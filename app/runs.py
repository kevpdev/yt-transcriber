"""One SQLite row per finished run, schema versioned by PRAGMA user_version."""

import json
import sqlite3
import threading
from pathlib import Path

SCHEMA_VERSION = 2

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
)
_JSON_COLUMNS = ("settings", "machine", "versions")


class RunStore:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
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
        script = ";\n".join(steps)
        self._db.executescript(
            f"BEGIN;\n{script};\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
        )

    def record(
        self, *, settings: dict, machine: dict, versions: dict, segments=(), **fields
    ) -> None:
        unknown = set(fields) - set(_COLUMNS)
        if unknown:
            raise TypeError(f"Unknown run columns: {sorted(unknown)}")
        values = [fields.get(c) for c in _COLUMNS]
        blobs = [json.dumps(v) for v in (settings, machine, versions)]
        names = ", ".join((*_COLUMNS, *_JSON_COLUMNS))
        marks = ", ".join(["?"] * (len(_COLUMNS) + len(_JSON_COLUMNS)))
        with self._lock, self._db:
            self._db.execute(f"INSERT INTO runs ({names}) VALUES ({marks})", [*values, *blobs])
            self._db.executemany(
                "INSERT INTO segments (run_id, position, start, end, text) VALUES (?, ?, ?, ?, ?)",
                [(fields.get("id"), i, s.start, s.end, s.text) for i, s in enumerate(segments)],
            )

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock:
            return self._db.execute(sql, params).fetchall()
