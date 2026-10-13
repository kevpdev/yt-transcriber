import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import jobs as j
from app import machine
from app.audio import AudioError
from app.fake import fake_capture
from app.main import create_app
from app.runs import _FRAMES_SCHEMA, _RUNS_SCHEMA, _SEGMENTS_SCHEMA, Frame, RunStore, to_markdown
from app.transcribe import Segment, settings
from tests.test_jobs import URL, FakeTranscriber, fake_download, wait_for


def count_rows(runs):
    return runs.query("SELECT COUNT(*) FROM runs")[0][0]


def test_successful_run_is_recorded_with_its_telemetry():
    runs = RunStore(":memory:")
    with TestClient(create_app(FakeTranscriber(), fake_download, runs)) as client:
        job_id = client.post("/jobs", json={"url": URL}).json()["id"]
        assert wait_for(client, job_id)["stage"] == j.DONE
        assert count_rows(runs) == 1
    row = runs.query(
        "SELECT id, state, text, word_count, language, title, channel, video_duration, "
        "download_s, total_s, json_extract(settings, '$.model'), "
        "char_count, speed_ratio, "
        "json_type(machine, '$.docker'), "
        "json_extract(versions, '$.yt_dlp'), typeof(machine) FROM runs"
    )[0]
    assert row[:8] == (job_id, "done", "bonjour le monde", 3, "fr", "T", "C", 12.0)
    assert row[8] >= 0 and row[9] >= row[8]
    assert row[10] == settings()["model"]
    assert row[13] in ("null", "text")
    assert row[14] is not None
    assert row[11] == len("bonjour le monde") and row[12] > 0
    assert row[15] == "text"


def test_done_run_stores_its_segments_in_order():
    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, job_id)
    assert runs.query(
        "SELECT run_id, position, start, end, text FROM segments ORDER BY position"
    ) == [(job_id, 0, 0.0, 1.5, "bonjour"), (job_id, 1, 1.5, 3.0, "le monde")]


def test_failed_run_stores_no_segments():
    def failing(url, dest, check=None):
        raise AudioError("Video unavailable")

    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), failing, runs))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert runs.query("SELECT COUNT(*) FROM segments") == [(0,)]


def test_version_one_database_migrates_without_losing_runs(tmp_path):
    path = str(tmp_path / "runs.db")
    old = sqlite3.connect(path)
    old.execute(_RUNS_SCHEMA)
    old.execute(
        "INSERT INTO runs (id, video_id, url, state, started_at) "
        "VALUES ('old', 'v', 'u', 'done', 'now')"
    )
    old.execute("PRAGMA user_version = 1")
    old.commit()
    old.close()
    runs = RunStore(path)
    assert runs.query("PRAGMA user_version") == [(4,)]
    assert runs.query("SELECT id FROM runs") == [("old",)]
    assert runs.query("SELECT COUNT(*) FROM segments") == [(0,)]


def test_version_two_database_migrates_to_four_keeping_runs_and_segments(tmp_path):
    path = str(tmp_path / "runs.db")
    old = sqlite3.connect(path)
    old.execute(_RUNS_SCHEMA)
    old.execute(_SEGMENTS_SCHEMA)
    old.execute(
        "INSERT INTO runs (id, video_id, url, state, started_at) "
        "VALUES ('old', 'v', 'u', 'done', 'now')"
    )
    old.execute("INSERT INTO segments VALUES ('old', 0, 0.0, 1.0, 'salut')")
    old.execute("PRAGMA user_version = 2")
    old.commit()
    old.close()
    runs = RunStore(path)
    assert runs.query("PRAGMA user_version") == [(4,)]
    assert runs.query("SELECT id FROM runs") == [("old",)]
    assert runs.query("SELECT text FROM segments") == [("salut",)]
    assert runs.query("SELECT COUNT(*) FROM frames") == [(0,)]


def test_frames_are_recorded_with_paths_relative_to_the_database_folder(tmp_path):
    runs = RunStore(str(tmp_path / "runs.db"))
    assert runs.frames_dir == tmp_path / "frames"
    images = [
        Frame(position=i, time=t, path=tmp_path / "frames" / "a" / f"{i:04d}.webp")
        for i, t in enumerate((0.0, 12.5))
    ]
    runs.record(
        id="a",
        video_id="v",
        url="u",
        state="done",
        started_at="now",
        settings={},
        machine={},
        versions={},
        frames=images,
    )
    run = runs.get_run("a")
    assert run is not None
    assert run["frames"] == [
        {"position": 0, "time": 0.0, "path": "frames/a/0000.webp"},
        {"position": 1, "time": 12.5, "path": "frames/a/0001.webp"},
    ]


def test_frame_outside_the_database_folder_is_dropped_and_the_run_kept(tmp_path, caplog):
    runs = RunStore(str(tmp_path / "runs.db"))
    images = [
        Frame(position=0, time=0.0, path=tmp_path / "frames" / "a" / "0000.webp"),
        Frame(position=1, time=5.0, path=tmp_path.parent / "elsewhere.webp"),
    ]
    runs.record(
        id="a",
        video_id="v",
        url="u",
        state="done",
        started_at="now",
        settings={},
        machine={},
        versions={},
        frames=images,
    )
    run = runs.get_run("a")
    assert run is not None
    assert run["frames"] == [{"position": 0, "time": 0.0, "path": "frames/a/0000.webp"}]
    assert "Dropped frame" in caplog.text


def test_run_without_images_has_an_empty_frames_list():
    runs = RunStore(":memory:")
    assert runs.frames_dir is None
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs))
    job_id = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, job_id)
    assert client.get(f"/runs/{job_id}").json()["frames"] == []


def test_two_runs_migration_leaves_the_version_at_four(tmp_path):
    path = str(tmp_path / "runs.db")
    RunStore(path)
    assert RunStore(path).query("PRAGMA user_version") == [(4,)]


def test_failed_run_is_recorded_with_its_error_and_no_transcript():
    def failing(url, dest, check=None):
        raise AudioError("Impossible de télécharger l'audio : Video unavailable")

    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), failing, runs))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert count_rows(runs) == 1
    assert runs.query("SELECT state, error, text, language, transcribe_s FROM runs") == [
        ("error", "Impossible de télécharger l'audio : Video unavailable", None, None, None)
    ]


def test_two_jobs_give_two_rows():
    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert count_rows(runs) == 1
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert count_rows(runs) == 2
    assert runs.query("SELECT state FROM runs") == [("done",), ("done",)]


def test_record_failure_leaves_the_job_done(monkeypatch, caplog):
    runs = RunStore(":memory:")

    def refuse(**_):
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(runs, "record", refuse)
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs))
    body = wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    assert body["stage"] == j.DONE and body["text"] == "bonjour le monde"
    assert "Could not record run" in caplog.text


def test_record_rejects_an_unknown_column():
    runs = RunStore(":memory:")
    with pytest.raises(TypeError, match="titel"):
        runs.record(settings={}, machine={}, versions={}, titel="x")


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
    assert second.query("PRAGMA user_version") == [(4,)]
    assert second.query("SELECT COUNT(*) FROM runs") == [(1,)]


def test_fresh_database_is_empty_at_version_four():
    runs = RunStore(":memory:")
    assert runs.query("PRAGMA user_version") == [(4,)]
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


def two_runs():
    client = TestClient(create_app(FakeTranscriber(), fake_download, RunStore(":memory:")))
    ids = []
    for _ in range(2):
        job_id = client.post("/jobs", json={"url": URL}).json()["id"]
        wait_for(client, job_id)
        ids.append(job_id)
    return client, ids


def test_latest_run_is_the_second_and_list_is_newest_first():
    client, (first, second) = two_runs()
    assert client.get("/runs/latest").json()["id"] == second
    body = client.get("/runs").json()
    assert [r["id"] for r in body["runs"]] == [second, first]
    assert (body["total"], body["limit"], body["offset"]) == (2, 20, 0)
    assert "text" not in body["runs"][0] and "segments" not in body["runs"][0]


def failing_download(url, dest, check=None):
    raise AudioError("Impossible de télécharger l'audio : Video unavailable")


def test_latest_run_skips_a_failed_run_but_list_keeps_it():
    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs))
    ok = client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(client, ok)
    bad_client = TestClient(create_app(FakeTranscriber(), failing_download, runs))
    bad = bad_client.post("/jobs", json={"url": URL}).json()["id"]
    wait_for(bad_client, bad)
    assert client.get("/runs/latest").json()["id"] == ok
    assert [r["id"] for r in client.get("/runs").json()["runs"]] == [bad, ok]


def test_latest_run_is_404_when_only_a_failed_run_exists():
    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), failing_download, runs))
    wait_for(client, client.post("/jobs", json={"url": URL}).json()["id"])
    response = client.get("/runs/latest")
    assert response.status_code == 404
    assert response.json() == {"detail": "Aucun run réussi."}


def test_run_detail_has_metadata_telemetry_and_ordered_segments():
    client, (first, _) = two_runs()
    run = client.get(f"/runs/{first}").json()
    assert (run["title"], run["channel"], run["state"], run["language"]) == ("T", "C", "done", "fr")
    assert run["text"] == "bonjour le monde"
    assert run["settings"]["model"] == settings()["model"]
    assert run["total_s"] >= 0
    assert isinstance(run["machine"], dict) and isinstance(run["versions"], dict)
    assert isinstance(run["transcribe_s"], int | float) and run["transcribe_s"] >= 0
    assert run["segments"] == [
        {"start": 0.0, "end": 1.5, "text": "bonjour"},
        {"start": 1.5, "end": 3.0, "text": "le monde"},
    ]


def test_unknown_run_is_404_for_detail_and_markdown():
    client = TestClient(create_app(FakeTranscriber(), fake_download, RunStore(":memory:")))
    for path in ("/runs/nope", "/runs/nope/markdown"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json() == {"detail": "Run inconnu."}


def test_latest_run_on_empty_database_is_404():
    client = TestClient(create_app(FakeTranscriber(), fake_download, RunStore(":memory:")))
    response = client.get("/runs/latest")
    assert response.status_code == 404
    assert response.json() == {"detail": "Aucun run réussi."}


def test_markdown_view_has_a_title_and_one_timed_line_per_segment():
    client, (first, _) = two_runs()
    response = client.get(f"/runs/{first}/markdown")
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert response.text == "# T\n\n[00:00] bonjour\n[00:01] le monde\n"


def test_markdown_uses_hours_after_one_hour_and_falls_back_to_the_video_id():
    runs = RunStore(":memory:")
    runs.record(
        id="r1",
        video_id="vid",
        url="u",
        state="done",
        started_at="2026-01-01T00:00:00",
        settings={},
        machine={},
        versions={},
        segments=[Segment(59.9, 60.0, "a"), Segment(3700.0, 3701.0, "b")],
    )
    run = runs.get_run("r1")
    assert run is not None
    assert to_markdown(run) == "# vid\n\n[00:59] a\n[1:01:40] b\n"


def test_runs_list_paginates_with_limit_and_offset():
    client, (first, _) = two_runs()
    body = client.get("/runs", params={"limit": 1, "offset": 1}).json()
    assert [r["id"] for r in body["runs"]] == [first]
    assert (body["total"], body["limit"], body["offset"]) == (2, 1, 1)


@pytest.mark.parametrize(
    "query",
    ["limit=0", "limit=101", "offset=-1", "limit=abc", "offset=1.5", "limit=1_0", "offset=+5"],
)
def test_runs_list_rejects_invalid_pagination_with_422(query):
    client = TestClient(create_app(FakeTranscriber(), fake_download, RunStore(":memory:")))
    response = client.get(f"/runs?{query}")
    assert response.status_code == 422
    assert "entier" in response.json()["detail"]


def test_version_three_database_migrates_to_four_with_level_text(tmp_path):
    path = str(tmp_path / "runs.db")
    old = sqlite3.connect(path)
    old.execute(_RUNS_SCHEMA)
    old.execute(_SEGMENTS_SCHEMA)
    old.execute(_FRAMES_SCHEMA)
    old.execute(
        "INSERT INTO runs (id, video_id, url, state, started_at) "
        "VALUES ('old', 'v', 'u', 'done', 'now')"
    )
    old.execute("PRAGMA user_version = 3")
    old.commit()
    old.close()
    runs = RunStore(path)
    assert runs.query("PRAGMA user_version") == [(4,)]
    assert runs.query("SELECT id, level FROM runs") == [("old", "text")]


def frames_client(tmp_path):
    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    return client, job_id


def test_run_frames_list_time_and_url_and_each_url_serves_the_file(tmp_path):
    client, run_id = frames_client(tmp_path)
    for run in (client.get(f"/runs/{run_id}").json(), client.get("/runs/latest").json()):
        assert [f["time"] for f in run["frames"]] == [0.0, 5.0]
        assert [f["url"] for f in run["frames"]] == [
            f"/runs/{run_id}/frames/000{i}.webp" for i in (0, 1)
        ]
        for frame in run["frames"]:
            resp = client.get(frame["url"])
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "image/webp"
            assert resp.content == (tmp_path / frame["path"]).read_bytes()


def test_unknown_frame_name_gives_404_in_french(tmp_path):
    client, run_id = frames_client(tmp_path)
    resp = client.get(f"/runs/{run_id}/frames/9999.webp")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Image inconnue."}


@pytest.mark.parametrize("name", ["..%2Fruns.db", "..%2F..%2Fruns.db", "%2E%2E%2Fruns.db"])
def test_traversal_name_serves_nothing(tmp_path, name):
    client, run_id = frames_client(tmp_path)
    assert (tmp_path / "runs.db").is_file()
    resp = client.get(f"/runs/{run_id}/frames/{name}")
    assert resp.status_code == 404
    assert b"SQLite" not in resp.content


def test_frame_of_unknown_run_gives_404_in_french(tmp_path):
    client, _ = frames_client(tmp_path)
    resp = client.get("/runs/inconnu/frames/0000.webp")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Run inconnu."}


def test_deleted_frame_file_gives_404(tmp_path):
    client, run_id = frames_client(tmp_path)
    (tmp_path / "frames" / run_id / "0000.webp").unlink()
    resp = client.get(f"/runs/{run_id}/frames/0000.webp")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Image inconnue."}


def test_memory_store_serves_no_frame_of_a_known_run():
    runs = RunStore(":memory:")
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    job_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    assert wait_for(client, job_id)["stage"] == j.DONE
    assert runs.frame_file(job_id, "0000.webp") is None
    resp = client.get(f"/runs/{job_id}/frames/0000.webp")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Image inconnue."}


@pytest.mark.parametrize(
    "name", ["../runs.db", "../../runs.db", "runs.db", "frames/{id}/0000.webp"]
)
def test_frame_file_refuses_any_name_not_listed_for_the_run(tmp_path, name):
    client, run_id = frames_client(tmp_path)
    runs = RunStore(str(tmp_path / "runs.db"))
    assert runs.frame_file(run_id, name.format(id=run_id)) is None
    assert runs.frame_file(run_id, "0000.webp") == tmp_path / "frames" / run_id / "0000.webp"
