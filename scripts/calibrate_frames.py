"""Calibration bench for the slide capture thresholds of app/frames.py (issue #53).

Runs inside the app image, which has PyAV, numpy and yt-dlp. The command line is in the
README, section "Capturer les slides à la main":

    <prefix> scripts/calibrate_frames.py <command> <video_id> [options]

Commands:
    sample  download the video once, decode it twice (the app sampling, then the libavfilter
            scene score of every frame), cache everything in calibration/<id>.npz, delete it
    sweep   replay app.frames.select_frames on the cache for a grid of thresholds, write a CSV
    scene   select on the cached scene scores for a range of thresholds, then the same dHash
            dedupe as the app, write a CSV
    sheet   draw a contact sheet: every N seconds (--every) or the frames kept by a set of
            thresholds (--params change,stable,hash or --scene threshold)

The sweep replays the real select_frames, not a copy: the thumbnails and hashes computed at
full resolution during `sample` are served back through app.frames._thumb and app.frames.dhash.
"""

import argparse
import csv
import itertools
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import av
import av.filter
import numpy as np

from app import frames

OUT = Path("calibration")
PREVIEW = (256, 144)  # width, height of the images kept for the contact sheets
DUP_BITS = 10  # two kept frames this close in dHash are counted as a probable duplicate


class Ref:
    """Stands for a sample image during the replay: an index into the cache."""

    def __init__(self, i: int) -> None:
        self.i = i


def _rgb_preview(rgb: np.ndarray) -> np.ndarray:
    w, h = PREVIEW
    rows = np.linspace(0, rgb.shape[0], h + 1).astype(int)
    cols = np.linspace(0, rgb.shape[1], w + 1).astype(int)
    out = np.empty((h, w, 3), np.uint8)
    for c in range(3):
        ch = rgb[:, :, c].astype(np.float32)
        sums = np.add.reduceat(np.add.reduceat(ch, rows[:-1], axis=0), cols[:-1], axis=1)
        out[:, :, c] = (sums / np.outer(np.diff(rows), np.diff(cols))).astype(np.uint8)
    return out


def _scene_scores(video: Path) -> tuple[np.ndarray, np.ndarray]:
    """libavfilter scene score of every decoded frame, with its time, through PyAV only."""
    times, scores = [], []
    with av.open(str(video)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        graph = av.filter.Graph()
        src = graph.add_buffer(template=stream)
        sel = graph.add("select", "gte(scene,0)")
        sink = graph.add("buffersink")
        src.link_to(sel)
        sel.link_to(sink)
        graph.configure()
        for frame in container.decode(stream):
            graph.push(frame)
            while True:
                try:
                    out = graph.pull()
                except (av.error.BlockingIOError, av.error.EOFError):
                    break
                assert isinstance(out, av.VideoFrame)
                times.append(float(out.time or 0.0))
                scores.append(float(out.metadata.get("lavfi.scene_score", "0")))
    return np.array(times), np.array(scores)


def sample(video_id: str) -> None:
    OUT.mkdir(exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.monotonic()
        video = frames.download_video(url, Path(tmp))
        download_s = time.monotonic() - t0
        size_mb = video.stat().st_size / 1e6
        with av.open(str(video)) as c:
            codec = c.streams.video[0].codec_context.name
            size = (c.streams.video[0].width, c.streams.video[0].height)

        t0 = time.monotonic()
        times, thumbs, hashes, previews = [], [], [], []
        for t, rgb in frames.sample_frames(video):
            times.append(t)
            thumbs.append(frames._thumb(rgb, *frames.THUMB).astype(np.float32))
            hashes.append(frames.dhash(rgb))
            previews.append(_rgb_preview(rgb))
        sample_s = time.monotonic() - t0

        t0 = time.monotonic()
        app_count = len(frames.select_frames(frames.sample_frames(video)))
        app_s = time.monotonic() - t0

        t0 = time.monotonic()
        scene_t, scene_s = _scene_scores(video)
        scene_decode_s = time.monotonic() - t0
        video.unlink()

    np.savez_compressed(
        OUT / f"{video_id}.npz",
        times=np.array(times),
        thumbs=np.stack(thumbs),
        hashes=np.array([str(h) for h in hashes]),
        previews=np.stack(previews),
        scene_t=scene_t,
        scene_s=scene_s,
        meta=np.array(
            [
                codec,
                f"{size[0]}x{size[1]}",
                f"{size_mb:.1f}",
                f"{download_s:.1f}",
                f"{sample_s:.1f}",
                f"{scene_decode_s:.1f}",
                f"{app_s:.1f}",
                str(app_count),
            ]
        ),
    )
    print(
        f"{video_id}: {codec} {size[0]}x{size[1]}, {size_mb:.1f} MB, download {download_s:.1f}s, "
        f"bench sampling {sample_s:.1f}s ({len(times)} samples), "
        f"app capture as shipped {app_s:.1f}s ({app_count} frames), "
        f"scene pass {scene_decode_s:.1f}s ({len(scene_s)} frames)"
    )


class Cache:
    def __init__(self, video_id: str) -> None:
        data = np.load(OUT / f"{video_id}.npz")
        self.times = data["times"]
        self.thumbs = data["thumbs"]
        self.hashes = [int(h) for h in data["hashes"]]
        self.previews = data["previews"]
        self.scene_t = data["scene_t"]
        self.scene_s = data["scene_s"]
        self.meta = list(data["meta"])

    def samples(self) -> Iterator[tuple[float, Ref]]:
        for i, t in enumerate(self.times):
            yield float(t), Ref(i)

    def index_at(self, t: float) -> int:
        return min(int(np.searchsorted(self.times, t)), len(self.times) - 1)


def replay(cache: Cache, change: float, stable: float, hash_bits: int) -> list[tuple[float, int]]:
    """(screen start, sample index) of what app.frames.select_frames keeps with these thresholds.

    The index is the sample at commit time, the image the app would write.
    """
    saved = (frames.CHANGE_THRESHOLD, frames.STABLE_S, frames.HASH_DISTANCE, frames.MAX_FRAMES)
    saved_fns = (frames._thumb, frames.dhash)
    frames.CHANGE_THRESHOLD, frames.STABLE_S = change, stable
    frames.HASH_DISTANCE, frames.MAX_FRAMES = hash_bits, 10_000
    frames._thumb = lambda ref, *_: cache.thumbs[ref.i]  # type: ignore[assignment]
    frames.dhash = lambda ref: cache.hashes[ref.i]  # type: ignore[assignment]
    try:
        kept = frames.select_frames(cache.samples())  # type: ignore[arg-type]
    finally:
        frames.CHANGE_THRESHOLD, frames.STABLE_S, frames.HASH_DISTANCE, frames.MAX_FRAMES = saved
        frames._thumb, frames.dhash = saved_fns
    return [(t, ref.i) for t, ref in kept]  # type: ignore[attr-defined]


def dup_pairs(cache: Cache, idx: list[int]) -> int:
    hs = [cache.hashes[i] for i in idx]
    return sum(frames._distance(a, b) <= DUP_BITS for a, b in itertools.combinations(hs, 2))


def scene_select(cache: Cache, threshold: float, hash_bits: int, settle: float) -> list[int]:
    """Cuts above the threshold, each shown by the sample `settle` seconds later, then dedupe."""
    cuts = cache.scene_t[cache.scene_s > threshold]
    candidates = [cache.index_at(0.0)] + [cache.index_at(float(t) + settle) for t in cuts]
    kept: list[int] = []
    for i in dict.fromkeys(candidates):
        if all(frames._distance(cache.hashes[i], cache.hashes[k]) > hash_bits for k in kept):
            kept.append(i)
    return kept


def sweep(video_id: str) -> None:
    cache = Cache(video_id)
    path = OUT / f"{video_id}-sweep.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["change", "stable_s", "hash_bits", "frames", "dup_pairs", "select_s"])
        for change, stable, bits in itertools.product(
            [3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0], [2.0, 3.0, 4.0, 5.0], [4, 6, 8, 10]
        ):
            t0 = time.monotonic()
            idx = [i for _, i in replay(cache, change, stable, bits)]
            w.writerow(
                [
                    change,
                    stable,
                    bits,
                    len(idx),
                    dup_pairs(cache, idx),
                    f"{time.monotonic() - t0:.3f}",
                ]
            )
    print(f"wrote {path}")


def scene(video_id: str) -> None:
    cache = Cache(video_id)
    path = OUT / f"{video_id}-scene.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scene", "hash_bits", "cuts", "frames", "dup_pairs"])
        for threshold, bits in itertools.product([0.1, 0.2, 0.3, 0.4, 0.5], [4, 6, 8, 10]):
            cuts = int((cache.scene_s > threshold).sum())
            idx = scene_select(cache, threshold, bits, settle=frames.STABLE_S)
            w.writerow([threshold, bits, cuts, len(idx), dup_pairs(cache, idx)])
    print(f"wrote {path}")


def _sheet(images: list[np.ndarray], labels: list[str], path: Path, cols: int = 8) -> None:
    w, h = PREVIEW
    band = 14
    rows = (len(images) + cols - 1) // cols
    canvas = np.full((rows * (h + band), cols * w, 3), 255, np.uint8)
    for n, (img, label) in enumerate(zip(images, labels, strict=True)):
        r, c = divmod(n, cols)
        y, x = r * (h + band), c * w
        canvas[y + band : y + band + h, x : x + w] = img
        _text(canvas, label, x + 2, y + 2)
    frame = av.VideoFrame.from_ndarray(canvas, format="rgb24")
    with av.open(str(path), "w", format="image2") as out:
        stream = out.add_stream("png", rate=1)
        stream.width, stream.height = canvas.shape[1], canvas.shape[0]
        stream.pix_fmt = "rgb24"
        for packet in stream.encode(frame):
            out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)


_DIGITS = {  # 3 x 5 bitmap font, enough for mm:ss labels and an index
    "0": "111101101101111",
    "1": "010110010010111",
    "2": "111001111100111",
    "3": "111001111001111",
    "4": "101101111001001",
    "5": "111100111001111",
    "6": "111100111101111",
    "7": "111001001001001",
    "8": "111101111101111",
    "9": "111101111001111",
    ":": "000010000010000",
    " ": "000000000000000",
    "#": "101111101111101",
}


def _text(canvas: np.ndarray, text: str, x: int, y: int, scale: int = 2) -> None:
    for k, ch in enumerate(text):
        bits = _DIGITS.get(ch, _DIGITS[" "])
        for b, bit in enumerate(bits):
            if bit == "1":
                r, c = divmod(b, 3)
                yy, xx = y + r * scale, x + (k * 4 + c) * scale
                canvas[yy : yy + scale, xx : xx + scale] = 0


def _mmss(t: float) -> str:
    return f"{int(t) // 60:02d}:{int(t) % 60:02d}"


def sheet(video_id: str, every: float | None, params: str | None, scene_t: float | None) -> None:
    cache = Cache(video_id)
    if every:
        idx = [cache.index_at(t) for t in np.arange(0.0, float(cache.times[-1]), every)]
        idx = list(dict.fromkeys(idx))
        labels = [_mmss(float(cache.times[i])) for i in idx]
        name = f"{video_id}-every{int(every)}s"
    elif params:
        change, stable, bits = params.split(",")
        kept = replay(cache, float(change), float(stable), int(bits))
        idx = [i for _, i in kept]
        labels = [f"{n} {_mmss(t)}" for n, (t, _) in enumerate(kept)]
        name = f"{video_id}-numpy-{change}-{stable}-{bits}"
    elif scene_t is not None:
        idx = scene_select(cache, scene_t, frames.HASH_DISTANCE, settle=frames.STABLE_S)
        labels = [f"{n} {_mmss(float(cache.times[i]))}" for n, i in enumerate(idx)]
        name = f"{video_id}-scene-{scene_t}"
    else:
        raise SystemExit("sheet needs --every, --params or --scene")
    # One PNG per 64 images keeps each sheet readable.
    for part in range(0, len(idx), 64):
        chunk = idx[part : part + 64]
        path = OUT / f"{name}-{part // 64}.png"
        _sheet([cache.previews[i] for i in chunk], labels[part : part + 64], path)
        print(f"wrote {path} ({len(chunk)} images)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["sample", "sweep", "scene", "sheet"])
    p.add_argument("video_id")
    p.add_argument("--every", type=float)
    p.add_argument("--params")
    p.add_argument("--scene", type=float)
    a = p.parse_args()
    if a.command == "sample":
        sample(a.video_id)
    elif a.command == "sweep":
        sweep(a.video_id)
    elif a.command == "scene":
        scene(a.video_id)
    else:
        sheet(a.video_id, a.every, a.params, a.scene)


if __name__ == "__main__":
    main()
