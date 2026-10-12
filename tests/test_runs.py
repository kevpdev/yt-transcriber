import sqlite3
import time

from fastapi.testclient import TestClient

from app import jobs as j
from app import machine
from app.audio import AudioError
from app.main import create_app
from app.runs import RunStore
from app.transcribe import settings
from tests.test_jobs import URL, FakeTranscriber, fake_download, wait_for


def wait_for_rows(runs, count):
    for _ in range(100):
        rows = runs.query("SELECT COUNT(*) FROM runs")
        if rows[0][0] >= count:
            return
        time.sleep(0.02)
    raise AssertionError("run not recorded")


def test_successful_run_is_recorded_with_its_telemetry():
    runs = RunStore(":memory:")
    with TestClient(create_app(FakeTranscriber(), fake_download, runs)) as client:
        job_id = client.post("/jobs", json={"url": URL}).json()["id"]
        assert wait_for(client, job_id)["stage"] == j.DONE
        wait_for_rows(runs, 1)
    row = runs.query(
        "SELECT id, state, text, word_count, language, title, channel, video_duration, "
        "download_s, total_s, json_extract(settings, '$.model'), "
        "char_count, speed_ratio, "
        "json_type(machine, '$.docker'), "
        "json_extract(versions, '$.yt_dlp') FROM runs"
    )[0]
    assert row[:8] == (job_id, "done", "bonjour le monde", 3, "fr", "T", "C", 12.0)
    assert row[8] >= 0 and row[9] >= row[8]
    assert row[10] == settings()["model"]
    assert row[13] in ("null", "text")
    assert row[14] is not None
    assert row[11] == len("bonjour le monde") and row[12] > 0


def test_failed_run_is_recorded_with_its_error_and_no_transcript():
    def failing(url, dest):
        raise AudioError("Impossible de télécharger l'audio : Video unavailable")

    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), failing, runs))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    wait_for_rows(runs, 1)
    assert runs.query("SELECT state, error, text, language, transcribe_s FROM runs") == [
        ("error", "Impossible de télécharger l'audio : Video unavailable", None, None, None)
    ]


def test_two_jobs_give_two_rows():
    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    wait_for_rows(runs, 1)
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    wait_for_rows(runs, 2)
    assert runs.query("SELECT state FROM runs") == [("done",), ("done",)]


def test_record_failure_leaves_the_job_done(monkeypatch, caplog):
    runs = RunStore(":memory:")

    def refuse(**_):
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(runs, "record", refuse)
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs))
    body = wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert body["stage"] == j.DONE and body["text"] == "bonjour le monde"
    for _ in range(100):
        if "Could not record run" in caplog.text:
            break
        time.sleep(0.02)
    assert "Could not record run" in caplog.text


def test_schema_is_created_once_in_a_file_database(tmp_path):
    path = str(tmp_path / "sub" / "runs.db")
    first = RunStore(path)
    first.record(
        id="a",
        video_id="v",
        url="u",
        state="done",
        started_at="now",
        settings={},
        machine={},
        versions={},
    )
    second = RunStore(path)
    assert second.query("PRAGMA user_version") == [(1,)]
    assert second.query("SELECT COUNT(*) FROM runs") == [(1,)]


def test_fresh_database_is_empty_at_version_one():
    runs = RunStore(":memory:")
    assert runs.query("PRAGMA user_version") == [(1,)]
    assert runs.query("SELECT COUNT(*) FROM runs") == [(0,)]


def test_machine_reads_return_none_without_nvidia_smi(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("HOST_DOCKER_VERSION", raising=False)
    info = machine.read_machine()
    assert info["gpu"] is None and info["cuda"] is None and info["docker"] is None


def test_machine_reads_nvidia_smi_and_docker_env(monkeypatch):
    def fake_smi(*args):
        if args:
            return "RTX 5060 Ti, 16311, 580.178.04\n"
        return "| NVIDIA-SMI 580.178.04   Driver Version: 580.178.04   CUDA Version: 13.0 |"

    monkeypatch.setattr(machine, "_nvidia_smi", fake_smi)
    monkeypatch.setenv("HOST_DOCKER_VERSION", "27.3.1")
    info = machine.read_machine()
    assert (info["gpu"], info["gpu_memory_mb"], info["gpu_driver"], info["cuda"]) == (
        "RTX 5060 Ti",
        16311,
        "580.178.04",
        "13.0",
    )
    assert info["docker"] == "27.3.1"


def test_versions_are_none_for_a_missing_package(monkeypatch):
    monkeypatch.setattr(machine, "_PACKAGES", {"nope": "definitely-not-installed-pkg"})
    assert machine.read_versions() == {"nope": None}
