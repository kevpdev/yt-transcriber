import sys
import types

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.runs import RunStore
from app.transcribe import Transcriber
from tests.test_jobs import URL, FakeTranscriber, fake_download, wait_for


@pytest.mark.parametrize(
    ("env", "expected"), [("int8", "int8"), ("", "float16"), (None, "float16")]
)
def test_run_settings_record_the_compute_type_from_the_environment(monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv("COMPUTE_TYPE", raising=False)
    else:
        monkeypatch.setenv("COMPUTE_TYPE", env)
    client = TestClient(create_app(FakeTranscriber(), fake_download, RunStore(":memory:")))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, job_id)
    assert client.get(f"/runs/{job_id}").json()["settings"]["compute_type"] == expected


def test_the_model_loads_with_the_compute_type_from_the_environment(monkeypatch):
    loaded = {}

    class FakeWhisperModel:
        def __init__(self, model, device, compute_type):
            loaded.update(model=model, device=device, compute_type=compute_type)

    # faster_whisper needs a CUDA GPU, the fake module stands in for it.
    fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    monkeypatch.setenv("COMPUTE_TYPE", "int8")
    Transcriber().load()
    assert loaded["compute_type"] == "int8"
