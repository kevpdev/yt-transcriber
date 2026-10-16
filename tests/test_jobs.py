import logging
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
        self.hotwords_seen: list[str] = []

    def run(self, audio, on_progress, hotwords=""):
        self.hotwords_seen.append(hotwords)
        on_progress(0.5)
        if self.gate:
            self.gate.wait(5)
        return Transcript(
            text="bonjour le monde",
            segments=[Segment(0.0, 1.5, "bonjour"), Segment(1.5, 3.0, "le monde")],
            language="fr",
            language_probability=0.99,
        )


def fake_download(url, dest, check=None, on_info=None):
    if on_info:
        on_info("T", "C", 12.0)
    return Download(
        path=dest / "a.webm", title="T", channel="C", duration=12.0, description="D\nline"
    )


def wait_for(client, job_id, stages=(j.DONE, j.ERROR)):
    body = {}
    for _ in range(100):
        body = client.get(f"/jobs/{job_id}").json()
        if body["stage"] in stages:
            return body
        time.sleep(0.02)
    raise AssertionError(body)


def test_store_accepts_a_second_job_while_the_first_is_unfinished():
    store = j.JobStore()
    first = store.start()
    second = store.start()
    assert second.id != first.id and second.stage == j.QUEUED


def test_store_evicts_only_finished_jobs():
    store = j.JobStore()
    waiting = store.start()
    running = store.start()
    store.set_stage(running, j.TRANSCRIBING)
    finished = [store.start() for _ in range(j._KEEP)]
    for job in finished:
        store.finish(job, "x", [])
    store.start()
    assert store.get(waiting.id) is waiting and store.get(running.id) is running
    assert store.get(finished[0].id) is None and store.get(finished[1].id) is None


def test_store_keeps_every_unfinished_job_past_the_limit():
    store = j.JobStore()
    unfinished = [store.start() for _ in range(j._KEEP + 5)]
    assert all(store.get(job.id) is job for job in unfinished)


def test_begin_restarts_the_clock_of_the_time_limit():
    job = j.JobStore().start(timeout=0.2)
    time.sleep(0.3)
    with pytest.raises(j.JobStopped, match="limite"):
        job.check()
    job.begin()
    job.check()


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


def test_run_carries_the_video_description_but_the_list_does_not():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    run_id = client.get("/runs/latest").json()["id"]
    assert client.get(f"/runs/{run_id}").json()["description"] == "D\nline"
    assert all("description" not in r for r in client.get("/runs").json()["runs"])


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


def test_second_job_waits_in_the_queue_and_runs_after_the_first():
    gates = [threading.Event(), threading.Event()]
    other = "https://www.youtube.com/watch?v=KnXm3PbNz5A"
    downloaded: list[str] = []

    class GatedTranscriber(FakeTranscriber):
        def run(self, audio, on_progress, hotwords=""):
            self.gate = gates[len(downloaded) - 1]
            return super().run(audio, on_progress, hotwords)

    def logging_download(url, dest, check=None, on_info=None):
        downloaded.append(url)
        return fake_download(url, dest, check, on_info)

    client = TestClient(create_app(GatedTranscriber(), logging_download))
    first = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, first, stages=(j.TRANSCRIBING,))
    resp = client.post("/jobs", json={"url": other})
    assert resp.status_code == 202
    second = resp.json()["id"]
    assert client.get(f"/jobs/{second}").json()["stage"] == j.QUEUED
    assert len(downloaded) == 1
    gates[0].set()
    assert wait_for(client, first)["stage"] == j.DONE
    assert wait_for(client, second, stages=(j.TRANSCRIBING,))["stage"] == j.TRANSCRIBING
    gates[1].set()
    assert wait_for(client, second)["stage"] == j.DONE
    assert [u.split("=")[1] for u in downloaded] == ["gsxiFd8AZQU", "KnXm3PbNz5A"]


def test_job_cancelled_in_the_queue_ends_in_error_without_a_download():
    gate = threading.Event()
    downloaded: list[str] = []

    def logging_download(url, dest, check=None, on_info=None):
        downloaded.append(url)
        return fake_download(url, dest, check, on_info)

    client = TestClient(create_app(FakeTranscriber(gate), logging_download))
    first = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, first, stages=(j.TRANSCRIBING,))
    second = client.post("/jobs", json={"url": URL}).json()["id"]
    resp = client.post(f"/jobs/{second}/cancel")
    assert resp.status_code == 202 and resp.json() == {"id": second}
    gate.set()
    assert wait_for(client, first)["stage"] == j.DONE
    body = wait_for(client, second)
    assert body["stage"] == j.ERROR and body["error"] == "Transcription annulée."
    assert len(downloaded) == 1
    assert client.get(f"/runs/{second}").json()["state"] == "error"


def test_waiting_in_the_queue_does_not_use_the_time_limit():
    release = threading.Event()
    calls = []

    def blocking_download(url, dest, check=None, on_info=None):
        calls.append(url)
        if len(calls) == 1:
            release.wait(5)
        return fake_download(url, dest, check, on_info)

    client = TestClient(create_app(FakeTranscriber(), blocking_download, timeout=0.5))
    first = client.post("/jobs", json={"url": URL}).json()["id"]
    second = client.post("/jobs", json={"url": URL}).json()["id"]
    time.sleep(0.7)
    release.set()
    first_body = wait_for(client, first)
    assert first_body["stage"] == j.ERROR and "limite" in first_body["error"]
    assert wait_for(client, second)["stage"] == j.DONE


def test_download_error_becomes_readable_job_error():
    def failing(url, dest, check=None, on_info=None):
        raise AudioError("Impossible de télécharger l'audio : Video unavailable")

    client = TestClient(create_app(FakeTranscriber(), failing))
    body = wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert body["stage"] == j.ERROR and "Video unavailable" in body["error"]


def test_download_error_logs_the_job_id_and_cause_but_keeps_the_french_message(caplog):
    def failing(url, dest, check=None, on_info=None):
        raise AudioError("Impossible de télécharger l'audio : Video unavailable")

    caplog.set_level(logging.INFO, logger="app")
    client = TestClient(create_app(FakeTranscriber(), failing))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    body = wait_for(client, job_id)
    assert body["error"] == "Impossible de télécharger l'audio : Video unavailable"
    failed = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(failed) == 1 and failed[0].exc_info is not None
    # The cause is written once, by the last line of the traceback, not in the header.
    assert job_id in failed[0].getMessage() and "Video unavailable" not in failed[0].getMessage()
    assert "AudioError: Impossible de télécharger l'audio : Video unavailable" in caplog.text
    assert f"Job {job_id} started" in caplog.text and f"Job {job_id} finished: error" in caplog.text


def test_unexpected_error_logs_the_job_id_and_traceback_but_not_in_the_api(caplog):
    class Crashing(FakeTranscriber):
        def run(self, audio, on_progress, hotwords=""):
            raise ZeroDivisionError("division by zero")

    caplog.set_level(logging.INFO, logger="app")
    client = TestClient(create_app(Crashing(), fake_download))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    body = wait_for(client, job_id)
    assert body["error"] == "Erreur inattendue pendant la transcription : division by zero"
    assert "Traceback" not in body["error"]
    failed = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(failed) == 1 and job_id in failed[0].getMessage()
    assert "Traceback (most recent call last)" in caplog.text
    assert "ZeroDivisionError: division by zero" in caplog.text
    assert f"Job {job_id} started" in caplog.text and f"Job {job_id} finished: error" in caplog.text


def test_job_publishes_the_video_info_while_downloading_and_keeps_it_when_done():
    gate = threading.Event()

    def waiting_download(url, dest, check=None, on_info=lambda *info: None):
        on_info("Titre", "Chaîne", 61.0)
        gate.wait(5)
        return Download(path=dest / "a.webm", title="Titre", channel="Chaîne", duration=61.0)

    client = TestClient(create_app(FakeTranscriber(), waiting_download))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    body: dict = {}
    for _ in range(100):
        body = client.get(f"/jobs/{job_id}").json()
        if body["title"]:
            break
        time.sleep(0.02)
    assert body["stage"] == j.DOWNLOADING
    assert (body["title"], body["channel"], body["duration"]) == ("Titre", "Chaîne", 61.0)
    gate.set()
    done = wait_for(client, job_id)
    assert (done["title"], done["channel"], done["duration"]) == ("Titre", "Chaîne", 61.0)


def test_info_stays_null_when_the_download_fails_before_knowing_the_video():
    def failing(url, dest, check=None, on_info=None):
        raise AudioError("Vidéo indisponible.")

    client = TestClient(create_app(FakeTranscriber(), failing))
    body = wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert body["stage"] == j.ERROR
    assert (body["title"], body["channel"], body["duration"]) == (None, None, None)


def test_job_hotwords_reach_the_transcriber_and_the_run_settings(monkeypatch):
    monkeypatch.setenv("HOTWORDS", "Env words")
    transcriber = FakeTranscriber()
    runs = RunStore(":memory:")
    client = TestClient(create_app(transcriber, fake_download, runs))
    sent = [{"hotwords": " Spring Boot "}, {}, {"hotwords": None}, {"hotwords": "   "}]
    for extra in sent:
        job_id = client.post("/jobs", json={"url": URL, **extra}).json()["id"]
        wait_for(client, job_id)
        used = transcriber.hotwords_seen[-1]
        assert client.get(f"/runs/{job_id}").json()["settings"]["hotwords"] == used
    assert transcriber.hotwords_seen == ["Spring Boot", "Env words", "Env words", "Env words"]


@pytest.mark.parametrize("bad", [42, ["a"], "x" * 501])
def test_invalid_hotwords_get_a_french_422(bad):
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    resp = client.post("/jobs", json={"url": URL, "hotwords": bad})
    assert resp.status_code == 422 and "hotwords" in resp.json()["detail"]
    assert client.post("/jobs", json={"url": URL}).status_code == 202


def test_get_hotwords_returns_the_default_read_at_call_time(monkeypatch):
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    monkeypatch.setenv("HOTWORDS", "Alpha, Beta")
    assert client.get("/hotwords").json() == {"default": "Alpha, Beta"}
    monkeypatch.delenv("HOTWORDS")
    assert client.get("/hotwords").json() == {"default": "Claude Code, Claude, Anthropic, MCP"}


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
    def capture(url, work_dir, out_dir, check=None):
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


@pytest.mark.parametrize("body", [{"url": URL}, {"url": URL, "level": None}])
def test_job_without_level_never_extracts_and_records_level_text(body, tmp_path, monkeypatch):
    stages = spy_stages(monkeypatch)
    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    job_id = client.post("/jobs", json=body).json()["id"]
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


def test_runs_list_carries_the_level_of_each_run():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert [r["level"] for r in client.get("/runs").json()["runs"]] == ["text"]


class SlowTranscriber(FakeTranscriber):
    """Reports progress until it is stopped, like the real one does for every segment."""

    def run(self, audio, on_progress, hotwords=""):
        for _ in range(500):
            time.sleep(0.01)
            on_progress(0.1)
        raise AssertionError("the job was never stopped")


def test_job_past_its_time_limit_ends_in_error_and_the_next_job_runs():
    client = TestClient(create_app(SlowTranscriber(), fake_download, timeout=0.2))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    body = wait_for(client, job_id)
    assert body["stage"] == j.ERROR and "limite" in body["error"]
    assert client.get(f"/runs/{job_id}").json()["state"] == "error"
    next_id = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, next_id, stages=(j.TRANSCRIBING,))
    client.post(f"/jobs/{next_id}/cancel")
    assert wait_for(client, next_id)["error"] == "Transcription annulée."


def test_cancel_during_transcription_ends_in_error_and_the_next_job_runs():
    client = TestClient(create_app(SlowTranscriber(), fake_download))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, job_id, stages=(j.TRANSCRIBING,))
    resp = client.post(f"/jobs/{job_id}/cancel")
    assert resp.status_code == 202 and resp.json() == {"id": job_id}
    body = wait_for(client, job_id)
    assert body["stage"] == j.ERROR and body["error"] == "Transcription annulée."
    assert client.get(f"/runs/{job_id}").json()["state"] == "error"
    next_id = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, next_id, stages=(j.TRANSCRIBING,))
    client.post(f"/jobs/{next_id}/cancel")
    assert wait_for(client, next_id)["error"] == "Transcription annulée."


def test_cancel_during_download_stops_the_job_before_transcription():
    started = threading.Event()

    def slow_download(url, dest, check, on_info):
        started.set()
        for _ in range(500):
            time.sleep(0.01)
            check()
        raise AssertionError("the job was never stopped")

    client = TestClient(create_app(FakeTranscriber(), slow_download))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    assert started.wait(5)
    assert client.post(f"/jobs/{job_id}/cancel").status_code == 202
    body = wait_for(client, job_id)
    assert body["stage"] == j.ERROR and body["error"] == "Transcription annulée."
    assert client.post("/jobs", json={"url": URL}).status_code == 202


def test_cancel_during_capture_ends_in_error_not_done_without_images(tmp_path):
    started = threading.Event()

    def slow_capture(url, work_dir, out_dir, check):
        out_dir.mkdir(parents=True)
        started.set()
        for _ in range(500):
            time.sleep(0.01)
            check()
        raise AssertionError("the job was never stopped")

    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, slow_capture))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    assert started.wait(5)
    client.post(f"/jobs/{job_id}/cancel")
    body = wait_for(client, job_id)
    assert body["stage"] == j.ERROR and body["error"] == "Transcription annulée."
    assert not (tmp_path / "frames" / job_id).exists()


def test_time_limit_during_capture_keeps_the_job_done_with_the_transcript_and_no_images(tmp_path):
    def slow_capture(url, work_dir, out_dir, check):
        out_dir.mkdir(parents=True)
        for _ in range(500):
            time.sleep(0.01)
            check()
        raise AssertionError("the job was never stopped")

    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, slow_capture, 0.3))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    body = wait_for(client, job_id)
    assert body["stage"] == j.DONE and body["text"] == "bonjour le monde"
    run = client.get(f"/runs/{job_id}").json()
    assert run["state"] == "done" and run["frames"] == []
    assert not (tmp_path / "frames" / job_id).exists()
    assert client.post("/jobs", json={"url": URL}).status_code == 202


def test_time_limit_past_when_the_capture_starts_keeps_the_job_done(tmp_path):
    gate = threading.Event()
    threading.Timer(0.5, gate.set).start()

    def never_capture(url, work_dir, out_dir, check):
        raise AssertionError("the capture started past the time limit")

    runs = RunStore(str(tmp_path / "runs.db"))
    app = create_app(FakeTranscriber(gate), fake_download, runs, never_capture, 0.2)
    client = TestClient(app)
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    body = wait_for(client, job_id)
    assert body["stage"] == j.DONE and body["text"] == "bonjour le monde"
    assert client.get(f"/runs/{job_id}").json()["frames"] == []


def test_cancel_unknown_job_is_404_and_finished_job_is_409():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    assert client.post("/jobs/nope/cancel").status_code == 404
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    resp = client.post(f"/jobs/{job_id}/cancel")
    assert resp.status_code == 409 and resp.json() == {"detail": "Ce job est déjà terminé."}


def test_store_cancel_reports_unknown_finished_and_requested():
    store = j.JobStore()
    assert store.cancel("nope") is None
    job = store.start()
    assert store.cancel(job.id) is True
    with pytest.raises(j.JobStopped, match="annulée"):
        job.check()
    store.fail(job, "x")
    assert store.cancel(job.id) is False
