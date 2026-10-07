import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import fake, main
from app import jobs as j
from app.fake import FAKE_TEXT, FakeTranscriber, fake_download
from app.main import build_app, create_app

URL = "https://www.youtube.com/watch?v=KnXm3PbNz5A"


@pytest.fixture(autouse=True)
def instant(monkeypatch):
    monkeypatch.setattr(fake, "FAKE_DURATION", 0.0)


def wait_for(client, job_id):
    body = {}
    for _ in range(100):
        body = client.get(f"/jobs/{job_id}").json()
        if body["stage"] in (j.DONE, j.ERROR):
            return body
        time.sleep(0.02)
    raise AssertionError(body)


def test_fake_pair_runs_a_job_to_done_with_fake_text():
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    body = wait_for(client, job_id)
    assert (body["stage"], body["text"], body["progress"]) == (j.DONE, FAKE_TEXT, 1.0)


def test_fake_progress_goes_through_the_stages():
    seen = []
    FakeTranscriber().run(fake_download(URL, Path("/tmp")), seen.append)
    assert seen[-1] == 1.0 and seen == sorted(seen)


def test_build_app_with_yt_fake_finishes_a_job(monkeypatch):
    monkeypatch.setenv("YT_FAKE", "1")
    client = TestClient(build_app())
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    assert wait_for(client, job_id)["text"] == FAKE_TEXT


@pytest.mark.parametrize("value", [None, "0", "true", ""])
def test_build_app_without_yt_fake_builds_the_real_transcriber(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("YT_FAKE", raising=False)
    else:
        monkeypatch.setenv("YT_FAKE", value)
    built = []

    class RealStub:
        model = object()

        def __init__(self):
            built.append(self)

    monkeypatch.setattr(main, "Transcriber", RealStub)
    build_app()
    assert len(built) == 1
