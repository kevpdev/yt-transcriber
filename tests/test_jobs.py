import sqlite3
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import jobs as j
from app.audio import AudioError, Download
from app.fake import fake_capture
from app.main import create_app
from app.runs import RunStore
from app.transcribe import Segment, Transcript

URL = "https://www.youtube.com/watch?v=gsxiFd8AZQU"


class FakeTranscriber:
    model = object()

    def __init__(self, gate=None):
        self.gate = gate

    def run(self, audio, on_progress):
        on_progress(0.5)
        if self.gate:
            self.gate.wait(5)
        return Transcript(
            text="bonjour le monde",
            segments=[Segment(0.0, 1.5, "bonjour"), Segment(1.5, 3.0, "le monde")],
            language="fr",
            language_probability=0.99,
        )


def fake_download(url, dest):
    return Download(path=dest / "a.webm", title="T", channel="C", duration=12.0)


def wait_for(client, job_id, stages=(j.DONE, j.ERROR)):
    body = {}
    for _ in range(100):
        body = client.get(f"/jobs/{job_id}").json()
        if body["stage"] in stages:
            return body
        time.sleep(0.02)
    raise AssertionError(body)


def test_store_refuses_second_job_until_first_finishes():
    store = j.JobStore()
    first = store.start()
    with pytest.raises(j.JobBusy):
        store.start()
    store.finish(first, "x", [])
    assert store.start().id != first.id


def test_store_frees_the_lock_after_error():
    store = j.JobStore()
    first = store.start()
    store.fail(first, "boom")
    store.start()


def test_happy_path_returns_raw_text():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    resp = client.post("/jobs", json={"url": URL})
    assert resp.status_code == 202
    body = wait_for(client, resp.json()["id"])
    assert (
        body["stage"] == j.DONE and body["text"] == "bonjour le monde" and body["progress"] == 1.0
    )


def test_done_job_exposes_timed_segments_and_keeps_text():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    body = wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert body["text"] == "bonjour le monde"
    assert body["segments"] == [
        {"start": 0.0, "end": 1.5, "text": "bonjour"},
        {"start": 1.5, "end": 3.0, "text": "le monde"},
    ]


def test_running_job_has_no_segments_yet():
    gate = threading.Event()
    client = TestClient(create_app(FakeTranscriber(gate), fake_download))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    body = wait_for(client, job_id, stages=(j.TRANSCRIBING,))
    assert body["segments"] == []
    gate.set()
    wait_for(client, job_id)


def test_invalid_url_gives_422_and_app_keeps_running():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    resp = client.post("/jobs", json={"url": "abc"})
    assert resp.status_code == 422 and resp.json()["detail"]
    assert client.post("/jobs", json={"url": URL}).status_code == 202


def test_second_job_while_running_gives_409_then_frees():
    gate = threading.Event()
    client = TestClient(create_app(FakeTranscriber(gate), fake_download))
    first = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, first, stages=(j.TRANSCRIBING,))
    resp = client.post("/jobs", json={"url": URL})
    assert resp.status_code == 409 and resp.json()["detail"]
    gate.set()
    wait_for(client, first)
    assert client.post("/jobs", json={"url": URL}).status_code == 202


def test_download_error_becomes_readable_job_error():
    def failing(url, dest):
        raise AudioError("Impossible de télécharger l'audio : Video unavailable")

    client = TestClient(create_app(FakeTranscriber(), failing))
    body = wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert body["stage"] == j.ERROR and "Video unavailable" in body["error"]


def test_unknown_job_is_404():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    assert client.get("/jobs/nope").status_code == 404


def test_job_with_frames_records_one_row_per_file_on_disk(tmp_path):
    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    frames = client.get(f"/runs/{job_id}").json()["frames"]
    assert [f["position"] for f in frames] == [0, 1]
    assert [f["path"] for f in frames] == [f"frames/{job_id}/000{i}.webp" for i in (0, 1)]
    assert all((tmp_path / f["path"]).is_file() for f in frames)


def test_job_without_frames_never_calls_the_capture(tmp_path):
    def capture(*_):
        raise AssertionError("capture must not run")

    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, capture))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    assert client.get(f"/runs/{job_id}").json()["frames"] == []
    assert not (tmp_path / "frames").exists()


def test_failed_capture_leaves_the_job_done_without_images(tmp_path, caplog):
    def capture(url, work_dir, out_dir):
        out_dir.mkdir(parents=True)
        (out_dir / "0000.webp").touch()
        raise RuntimeError("decode failed")

    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, capture))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    body = wait_for(client, job_id)
    assert body["stage"] == j.DONE and body["text"] == "bonjour le monde"
    run = client.get(f"/runs/{job_id}").json()
    assert run["state"] == "done" and run["frames"] == []
    assert not (tmp_path / "frames" / job_id).exists()
    assert "Could not capture frames" in caplog.text


def test_record_failure_after_capture_removes_the_images(tmp_path, monkeypatch, caplog):
    def refuse(**_):
        raise sqlite3.OperationalError("disk full")

    runs = RunStore(str(tmp_path / "runs.db"))
    monkeypatch.setattr(runs, "record", refuse)
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    assert "Could not record run" in caplog.text
    assert not (tmp_path / "frames" / job_id).exists()


def spy_stages(monkeypatch):
    stages = []
    set_stage = j.JobStore.set_stage

    def spy(self, job, stage, progress=0.0):
        stages.append(stage)
        set_stage(self, job, stage, progress)

    monkeypatch.setattr(j.JobStore, "set_stage", spy)
    return stages


def test_job_without_level_never_extracts_and_records_level_text(tmp_path, monkeypatch):
    stages = spy_stages(monkeypatch)
    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    assert j.EXTRACTING not in stages
    run = client.get(f"/runs/{job_id}").json()
    assert run["level"] == "text" and run["frames"] == []


def test_job_with_frames_level_passes_through_extracting_and_records_it(tmp_path, monkeypatch):
    stages = spy_stages(monkeypatch)
    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    assert stages == [j.DOWNLOADING, j.TRANSCRIBING, j.EXTRACTING]
    run = client.get(f"/runs/{job_id}").json()
    assert run["level"] == "frames" and len(run["frames"]) == 2


def test_unknown_level_gives_422_in_french_and_takes_no_job():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    resp = client.post("/jobs", json={"url": URL, "level": "video"})
    assert resp.status_code == 422
    assert resp.json() == {"detail": "Le niveau doit être text ou frames."}
    assert client.post("/jobs", json={"url": URL}).status_code == 202


@pytest.mark.parametrize("level", [1, ["frames"], ""])
def test_non_string_or_empty_level_gives_the_french_422(level):
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    resp = client.post("/jobs", json={"url": URL, "level": level})
    assert resp.status_code == 422
    assert resp.json() == {"detail": "Le niveau doit être text ou frames."}


def test_null_level_means_text():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    assert client.post("/jobs", json={"url": URL, "level": None}).status_code == 202


def test_runs_list_carries_the_level_of_each_run():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert [r["level"] for r in client.get("/runs").json()["runs"]] == ["text"]
