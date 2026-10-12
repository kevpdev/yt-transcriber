"""Slide capture: video-only download, stable screen changes, perceptual dedupe, WebP files.

Everything goes through PyAV and numpy, there is no ffmpeg binary, see
aidd_docs/memory/internal/decisions/frames-pyav.md.
"""

import logging
import sys
import tempfile
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import av
import numpy as np

from .audio import AudioError, readable_error
from .runs import Frame

log = logging.getLogger(__name__)

# Provisional values, calibrated on the reference video by issue #53.
SAMPLE_EVERY_S = 1.0
THUMB = (64, 36)  # width, height of the grayscale thumbnail compared between samples
CHANGE_THRESHOLD = 6.0  # mean absolute difference on a 0 to 255 scale
STABLE_S = 3.0
HASH_DISTANCE = 6  # bits out of 64
MAX_FRAMES = 80

_VIDEO_FORMAT = (
    "bestvideo[height<=720][vcodec^=av01]"
    "/bestvideo[height<=720][vcodec^=vp09]"
    "/bestvideo[height<=720]"
)

Sample = tuple[float, np.ndarray]


def download_video(url: str, dest_dir: Path) -> Path:
    """Video stream only, 720p at most, AV1 then VP9. yt-dlp never merges, so no ffmpeg."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    opts: Any = {
        "format": _VIDEO_FORMAT,
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "noprogress": True,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            log.info("Downloaded video %s, codec %s", info.get("id"), info.get("vcodec"))
            return Path(ydl.prepare_filename(info))
    except DownloadError as exc:
        raise AudioError(readable_error(str(exc), "la vidéo")) from exc


def sample_frames(video: Path) -> Iterator[Sample]:
    """About one RGB image per SAMPLE_EVERY_S of video, with its time in seconds."""
    next_at = 0.0
    with av.open(str(video)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in container.decode(stream):
            if frame.time is None or frame.time < next_at:
                continue
            next_at = frame.time + SAMPLE_EVERY_S
            yield frame.time, frame.to_ndarray(format="rgb24")


def _thumb(rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    """Grayscale area average on a width x height grid."""
    gray = rgb.astype(np.float32).mean(axis=2)
    rows = np.linspace(0, gray.shape[0], height + 1).astype(int)
    cols = np.linspace(0, gray.shape[1], width + 1).astype(int)
    sums = np.add.reduceat(np.add.reduceat(gray, rows[:-1], axis=0), cols[:-1], axis=1)
    return sums / np.outer(np.diff(rows), np.diff(cols))


def dhash(rgb: np.ndarray) -> int:
    """64 bit difference hash: is each pixel brighter than its right neighbour, on a 9 x 8 grid."""
    small = _thumb(rgb, 9, 8)
    bits = (small[:, :-1] > small[:, 1:]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def _distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def select_frames(samples: Iterable[Sample]) -> list[Sample]:
    """One image per screen that stays for STABLE_S, timed at its start, without repeats.

    The image is the sample at commit time, once the screen has held, not the first one above
    the threshold, which can sit in the middle of a transition. Pure function of the samples,
    so it runs without PyAV or network.
    """
    kept: list[Sample] = []
    hashes: list[int] = []
    screen: tuple[float, np.ndarray] | None = None  # start time and thumbnail of the screen
    committed = False
    for t, rgb in samples:
        thumb = _thumb(rgb, *THUMB)
        if screen is None or np.abs(thumb - screen[1]).mean() > CHANGE_THRESHOLD:
            screen, committed = (t, thumb), False
        start = screen[0]
        if committed or t - start < STABLE_S:
            continue
        committed = True
        screen = (start, thumb)  # next change is measured against the stable image
        digest = dhash(rgb)
        if all(_distance(digest, h) > HASH_DISTANCE for h in hashes):
            hashes.append(digest)
            kept.append((start, rgb))
            if len(kept) >= MAX_FRAMES:
                break
    return kept


def write_webp(rgb: np.ndarray, path: Path) -> None:
    with av.open(str(path), "w", format="webp") as out:
        stream = out.add_stream("libwebp", rate=1)
        stream.width, stream.height = rgb.shape[1], rgb.shape[0]
        stream.pix_fmt = "yuv420p"
        for packet in stream.encode(av.VideoFrame.from_ndarray(rgb, format="rgb24")):
            out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)


def capture_frames(url: str, work_dir: Path, out_dir: Path) -> list[Frame]:
    """Slides of a video as `out_dir/<position>.webp`. The downloaded video never stays."""
    video: Path | None = None
    try:
        video = download_video(url, work_dir)
        selected = select_frames(sample_frames(video))
        out_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        for position, (t, rgb) in enumerate(selected):
            path = out_dir / f"{position:04d}.webp"
            write_webp(rgb, path)
            frames.append(Frame(position=position, time=t, path=path))
        return frames
    finally:
        if video is not None:
            video.unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    """`python -m app.frames <url> [out_dir]`: runs the same function as a job, by hand."""
    if not argv:
        print("usage: python -m app.frames <url> [out_dir]", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out_dir = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="frames-"))
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        frames = capture_frames(argv[0], Path(tmp), out_dir)
        left = [p.name for p in Path(tmp).iterdir()]
    for f in frames:
        print(f"{f.time:8.1f}  {f.path}")
    print(f"{len(frames)} frames in {time.monotonic() - t0:.1f}s, files left in work dir: {left}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
