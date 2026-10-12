"""One SQLite row per finished run, schema versioned by PRAGMA user_version."""

import json
import logging
import sqlite3
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .transcribe import Segment

SCHEMA_VERSION = 4
log = logging.getLogger(__name__)


@dataclass
class Frame:
    """One captured slide: its position, its start in the video (seconds) and its file."""

    position: int
    time: float
    path: Path


_RUNS_SCHEMA = """
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    channel TEXT,
    video_duration REAL,
    state TEXT NOT NULL,
    error TEXT,
    text TEXT,
    word_count INTEGER,
    char_count INTEGER,
    language TEXT,
    language_probability REAL,
    started_at TEXT NOT NULL,
    download_s REAL,
    transcribe_s REAL,
    total_s REAL,
    speed_ratio REAL,
    settings TEXT,
    machine TEXT,
    versions TEXT
)
"""

_SEGMENTS_SCHEMA = """
CREATE TABLE segments (
    run_id TEXT NOT NULL REFERENCES runs(id),
    position INTEGER NOT NULL,
    start REAL NOT NULL,
    end REAL NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (run_id, position)
)
"""

_FRAMES_SCHEMA = """
CREATE TABLE frames (
    run_id TEXT NOT NULL REFERENCES runs(id),
    position INTEGER NOT NULL,
    time REAL NOT NULL,
    path TEXT NOT NULL,
    PRIMARY KEY (run_id, position)
)
"""

_LEVEL_SCHEMA = "ALTER TABLE runs ADD COLUMN level TEXT NOT NULL DEFAULT 'text'"

_COLUMNS = (
    "id",
    "video_id",
    "url",
    "title",
    "channel",
    "video_duration",
    "state",
    "error",
    "text",
    "word_count",
    "char_count",
    "language",
    "language_probability",
    "started_at",
    "download_s",
    "transcribe_s",
    "total_s",
    "speed_ratio",
    "level",
)
_JSON_COLUMNS = ("settings", "machine", "versions")
_SUMMARY_COLUMNS = (
    "id",
    "video_id",
    "url",
    "title",
    "channel",
    "video_duration",
    "state",
    "level",
    "language",
    "word_count",
    "started_at",
    "total_s",
)


def format_time(seconds: float) -> str:
    """Same format as formatTime in app/static/app.js."""
    total = int(seconds)
    h, rest = divmod(total, 3600)
    clock = f"{rest // 60:02d}:{rest % 60:02d}"
    return f"{h}:{clock}" if h > 0 else clock


def to_markdown(run: dict) -> str:
    """Title, blank line, then one `[mm:ss] text` line per segment."""
    lines = [f"[{format_time(s['start'])}] {s['text']}" for s in run["segments"]]
    return "\n".join([f"# {run['title'] or run['video_id']}", "", *lines]) + "\n"


class RunStore:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # Frame paths in the table are relative to the folder of the database file.
        self._root = None if path == ":memory:" else Path(path).parent
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        with self._lock:
            self._migrate()

    def _migrate(self) -> None:
        """Apply the missing steps in one transaction, never dropping existing data."""
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version >= SCHEMA_VERSION:
            return
        # executescript commits first, so the transaction is opened inside the script.
        steps = []
        if version < 1:
            steps.append(_RUNS_SCHEMA)
        if version < 2:
            steps.append(_SEGMENTS_SCHEMA)
        if version < 3:
            steps.append(_FRAMES_SCHEMA)
        if version < 4:
            steps.append(_LEVEL_SCHEMA)
        script = ";\n".join(steps)
        self._db.executescript(
            f"BEGIN;\n{script};\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
        )

    @property
    def frames_dir(self) -> Path | None:
        """Where the images of the runs go, next to the database file. None for `:memory:`."""
        return self._root / "frames" if self._root else None

    def _relative(self, path: Path) -> str:
        return path.relative_to(self._root).as_posix() if self._root else path.as_posix()

    def record(
        self,
        *,
        settings: dict,
        machine: dict,
        versions: dict,
        segments: Sequence[Segment] = (),
        frames: Sequence[Frame] = (),
        **fields,
    ) -> None:
        unknown = set(fields) - set(_COLUMNS)
        if unknown:
            raise TypeError(f"Unknown run columns: {sorted(unknown)}")
        fields.setdefault("level", "text")
        values = [fields.get(c) for c in _COLUMNS]
        blobs = [json.dumps(v) for v in (settings, machine, versions)]
        names = ", ".join((*_COLUMNS, *_JSON_COLUMNS))
        marks = ", ".join(["?"] * (len(_COLUMNS) + len(_JSON_COLUMNS)))
        # An image outside the database folder is dropped, never the run with its transcript.
        frame_rows = []
        for f in frames:
            try:
                frame_rows.append((fields.get("id"), f.position, f.time, self._relative(f.path)))
            except ValueError:
                log.warning("Dropped frame %s of run %s: outside the folder", f.path, fields["id"])
        with self._lock, self._db:
            self._db.execute(f"INSERT INTO runs ({names}) VALUES ({marks})", [*values, *blobs])
            self._db.executemany(
                "INSERT INTO segments (run_id, position, start, end, text) VALUES (?, ?, ?, ?, ?)",
                [(fields.get("id"), i, s.start, s.end, s.text) for i, s in enumerate(segments)],
            )
            self._db.executemany(
                "INSERT INTO frames (run_id, position, time, path) VALUES (?, ?, ?, ?)",
                frame_rows,
            )

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]

    def list_runs(self, limit: int, offset: int) -> list[dict]:
        cols = ", ".join(_SUMMARY_COLUMNS)
        with self._lock:
            rows = self._db.execute(
                f"SELECT {cols} FROM runs ORDER BY started_at DESC, rowid DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(zip(_SUMMARY_COLUMNS, row, strict=True)) for row in rows]

    def has_run(self, run_id: str) -> bool:
        with self._lock:
            row = self._db.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
        return row is not None

    def latest_id(self) -> str | None:
        with self._lock:
            row = self._db.execute(
                "SELECT id FROM runs WHERE state = 'done' "
                "ORDER BY started_at DESC, rowid DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else None

    def get_run(self, run_id: str) -> dict | None:
        names = (*_COLUMNS, *_JSON_COLUMNS)
        with self._lock:
            row = self._db.execute(
                f"SELECT {', '.join(names)} FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row is None:
                return None
            segs = self._db.execute(
                "SELECT start, end, text FROM segments WHERE run_id = ? ORDER BY position",
                (run_id,),
            ).fetchall()
            imgs = self._db.execute(
                "SELECT position, time, path FROM frames WHERE run_id = ? ORDER BY position",
                (run_id,),
            ).fetchall()
        run: dict = dict(zip(names, row, strict=True))
        for col in _JSON_COLUMNS:
            run[col] = json.loads(run[col]) if run[col] is not None else None
        run["segments"] = [{"start": a, "end": b, "text": t} for a, b, t in segs]
        run["frames"] = [{"position": p, "time": t, "path": f} for p, t, f in imgs]
        return run

    def frame_file(self, run_id: str, name: str) -> Path | None:
        """The file of an image of this run, found by its file name among the recorded rows.

        The table is the allow-list: a name that is not in it (`../runs.db`) matches nothing.
        None for `:memory:`, an unknown name, or a file missing from the disk.
        """
        if self._root is None:
            return None
        with self._lock:
            rows = self._db.execute(
                "SELECT path FROM frames WHERE run_id = ? ORDER BY position", (run_id,)
            ).fetchall()
        for (path,) in rows:
            if Path(path).name == name:
                file = self._root / path
                return file if file.is_file() else None
        return None

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock:
            return self._db.execute(sql, params).fetchall()
