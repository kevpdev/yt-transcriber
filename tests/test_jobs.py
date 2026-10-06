import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import jobs as j
from app.audio import AudioError
from app.main import create_app

URL = "https://www.youtube.com/watch?v=gsxiFd8AZQU"


class FakeTranscriber:
    model = object()

    def __init__(self, gate=None):
        self.gate = gate

    def run(self, audio, on_progress):
        on_progress(0.5)
        if self.gate:
            self.gate.wait(5)
        return "bonjour le monde"


def fake_download(url, dest):
    return dest / "a.webm"


def wait_for(client, job_id, stages=(j.DONE, j.ERROR)):
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
    store.finish(first, "x")
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
    assert body["stage"] == j.DONE and body["text"] == "bonjour le monde" and body["progress"] == 1.0


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
