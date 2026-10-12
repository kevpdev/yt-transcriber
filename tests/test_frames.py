from pathlib import Path

import av
import numpy as np
import pytest

from app import frames
from app.audio import AudioError
from app.frames import (
    capture_frames,
    dhash,
    download_video,
    select_frames,
    write_webp,
)

H, W = 72, 128


def solid(value: int) -> np.ndarray:
    return np.full((H, W, 3), value, dtype=np.uint8)


def pattern(seed: int) -> np.ndarray:
    """Noise that differs a lot from any other seed, in both brightness and hash."""
    return np.random.default_rng(seed).integers(0, 256, (H, W, 3), dtype=np.uint8)


def run(*screens: tuple[np.ndarray, int], start: float = 0.0):
    """Samples one per second, each screen shown for the given number of seconds."""
    t = start
    for rgb, seconds in screens:
        for _ in range(seconds):
            yield t, rgb
            t += 1.0


def test_three_stable_slides_give_three_frames_at_their_start():
    a, b, c = pattern(1), pattern(2), pattern(3)
    kept = select_frames(run((a, 5), (b, 5), (c, 5)))
    assert [t for t, _ in kept] == [0.0, 5.0, 10.0]


def test_returning_to_a_seen_slide_keeps_it_once():
    a, b = pattern(1), pattern(2)
    kept = select_frames(run((a, 5), (b, 5), (a, 5)))
    assert [t for t, _ in kept] == [0.0, 5.0]


def test_short_change_is_not_kept():
    kept = select_frames(run((pattern(1), 6), (pattern(2), 1), (pattern(3), 6)))
    assert [t for t, _ in kept] == [0.0, 7.0]


def test_screen_not_stable_at_the_end_is_not_kept():
    kept = select_frames(run((pattern(1), 5), (pattern(2), 2)))
    assert [t for t, _ in kept] == [0.0]


def test_noise_below_the_threshold_does_not_start_a_new_slide():
    base = solid(120)
    noisy = np.clip(base.astype(int) + 2, 0, 255).astype(np.uint8)
    kept = select_frames(run((base, 3), (noisy, 3)))
    assert len(kept) == 1


def test_frames_never_exceed_the_cap(monkeypatch):
    monkeypatch.setattr(frames, "MAX_FRAMES", 3)
    kept = select_frames(run(*[(pattern(i), 4) for i in range(10)]))
    assert len(kept) == 3


def test_dhash_is_stable_and_tells_patterns_apart():
    assert dhash(pattern(1)) == dhash(pattern(1))
    assert (dhash(pattern(1)) ^ dhash(pattern(2))).bit_count() > frames.HASH_DISTANCE


def test_webp_round_trip_keeps_the_size(tmp_path: Path):
    path = tmp_path / "0000.webp"
    write_webp(pattern(1), path)
    with av.open(str(path)) as container:
        image = next(container.decode(video=0)).to_ndarray(format="rgb24")
    assert image.shape == (H, W, 3)


def test_unavailable_video_gives_a_readable_audio_error(monkeypatch, tmp_path: Path):
    from yt_dlp.utils import DownloadError

    class Broken:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download):
            raise DownloadError("ERROR: [youtube] abcdefghijk: Video unavailable")

    monkeypatch.setattr("yt_dlp.YoutubeDL", Broken)
    with pytest.raises(AudioError) as err:
        download_video("https://www.youtube.com/watch?v=abcdefghijk", tmp_path)
    assert str(err.value) == "Impossible de télécharger la vidéo : Video unavailable"


def test_capture_writes_frames_and_removes_the_video(monkeypatch, tmp_path: Path):
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()

    def fake_download(url, dest):
        path = dest / "v.webm"
        path.touch()
        return path

    samples = list(run((pattern(1), 5), (pattern(2), 5)))
    monkeypatch.setattr(frames, "download_video", fake_download)
    monkeypatch.setattr(frames, "sample_frames", lambda video: iter(samples))
    result = capture_frames("u", work, out)
    assert [(f.position, f.time) for f in result] == [(0, 0.0), (1, 5.0)]
    assert sorted(p.name for p in out.iterdir()) == ["0000.webp", "0001.webp"]
    assert list(work.iterdir()) == []


def test_capture_removes_the_video_when_selection_raises(monkeypatch, tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()

    def fake_download(url, dest):
        path = dest / "v.webm"
        path.touch()
        return path

    def boom(video):
        raise RuntimeError("decode failed")

    monkeypatch.setattr(frames, "download_video", fake_download)
    monkeypatch.setattr(frames, "sample_frames", boom)
    with pytest.raises(RuntimeError):
        capture_frames("u", work, tmp_path / "out")
    assert list(work.iterdir()) == []


def test_sample_frames_decodes_a_video_about_once_per_second(tmp_path: Path):
    video = tmp_path / "v.mkv"
    with av.open(str(video), "w") as out:
        stream = out.add_stream("mpeg4", rate=4)
        stream.width, stream.height = W, H
        stream.pix_fmt = "yuv420p"
        for i in range(12):
            frame = av.VideoFrame.from_ndarray(solid(40 if i < 6 else 200), format="rgb24")
            frame.pts = i
            for packet in stream.encode(frame):
                out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)
    times = [t for t, _ in frames.sample_frames(video)]
    assert times == [0.0, 1.0, 2.0]
