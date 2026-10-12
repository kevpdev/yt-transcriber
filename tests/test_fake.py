import time

import pytest
from fastapi.testclient import TestClient

from app import fake, main
from app import jobs as j
from app.fake import FAKE_TEXT, FakeTranscriber, fake_download
from app.main import build_app, create_app

URL = "https://www.youtube.com/watch?v=KnXm3PbNz5A"


@pytest.fixture(autouse=True)
def instant(monkeypatch, tmp_path):
    monkeypatch.setattr(fake, "FAKE_DURATION", 0.0)
    monkeypatch.setenv("YT_DB", str(tmp_path / "runs.db"))


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
    assert " ".join(s["text"] for s in body["segments"]) == FAKE_TEXT


def test_fake_segments_join_to_the_fake_text_and_span_the_duration(monkeypatch):
    monkeypatch.setattr(fake, "FAKE_DURATION", 10.0)
    segments = fake.fake_segments()
    assert " ".join(s.text for s in segments) == FAKE_TEXT
    assert segments[0].start == 0.0 and segments[-1].end == fake.FAKE_DURATION
    assert all(a.end == b.start for a, b in zip(segments, segments[1:], strict=False))
    assert all(s.start < s.end for s in segments)


def test_fake_job_goes_through_downloading_transcribing_done_in_order(monkeypatch):
    seen = []
    set_stage, finish = j.JobStore.set_stage, j.JobStore.finish

    def spy_set_stage(self, job, stage, progress=0.0):
        seen.append(stage)
        set_stage(self, job, stage, progress)

    def spy_finish(self, job, text, segments):
        seen.append(j.DONE)
        finish(self, job, text, segments)

    monkeypatch.setattr(j.JobStore, "set_stage", spy_set_stage)
    monkeypatch.setattr(j.JobStore, "finish", spy_finish)
    monkeypatch.setattr(fake, "FAKE_DURATION", 0.1)
    client = TestClient(create_app(FakeTranscriber(), fake_download))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert seen == [j.DOWNLOADING, j.TRANSCRIBING, j.DONE]


def test_fake_progress_is_increasing_and_ends_at_one(tmp_path):
    seen = []
    FakeTranscriber().run(fake_download(URL, tmp_path).path, seen.append)
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
