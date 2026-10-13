"""The published /openapi.json describes every response, and the real bodies match it."""

import threading

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app import contract as c
from app import jobs as j
from app.audio import AudioError
from app.fake import fake_capture
from app.main import create_app
from app.runs import RunStore
from tests.test_jobs import URL, FakeTranscriber, fake_download, wait_for

# Every operation and the codes it must declare. A new route fails the test until it is added.
EXPECTED = {
    ("post", "/jobs"): {"202", "409", "422"},
    ("get", "/jobs/{job_id}"): {"200", "404"},
    ("get", "/runs"): {"200", "422"},
    ("get", "/runs/latest"): {"200", "404"},
    ("get", "/runs/{run_id}"): {"200", "404"},
    ("get", "/runs/{run_id}/frames/{name}"): {"200", "404"},
    ("get", "/runs/{run_id}/markdown"): {"200", "404"},
    ("get", "/"): {"200"},
}


def missing_schemas(document: dict) -> list[str]:
    """Each response of each operation that publishes no body, or an empty schema."""
    missing = []
    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            for code, response in operation["responses"].items():
                content = response.get("content") or {}
                if not content or any(not media.get("schema") for media in content.values()):
                    missing.append(f"{method.upper()} {path} {code}")
    return missing


def spec() -> dict:
    return create_app(FakeTranscriber(), fake_download).openapi()


def test_every_response_of_every_route_has_a_schema():
    assert missing_schemas(spec()) == []


def test_a_route_without_a_response_model_is_caught():
    app = create_app(FakeTranscriber(), fake_download)

    @app.get("/undeclared")
    def undeclared():
        return {}

    assert missing_schemas(app.openapi()) == ["GET /undeclared 200"]


def test_every_route_declares_its_success_and_error_codes():
    published = spec()
    declared = {
        (method, path): {code for code, resp in op["responses"].items() if not generated(resp)}
        for path, ops in published["paths"].items()
        for method, op in ops.items()
    }
    assert declared == EXPECTED


def generated(response: dict) -> bool:
    """The 422 FastAPI adds to every route with a path parameter, which a string never fails."""
    schema = response.get("content", {}).get("application/json", {}).get("schema", {})
    return schema == {"$ref": "#/components/schemas/HTTPValidationError"}


def test_errors_are_the_french_detail_and_bodies_that_are_not_json_say_their_media_type():
    paths = spec()["paths"]

    def content(path: str, method: str, code: str) -> dict:
        return paths[path][method]["responses"][code]["content"]

    detail = {"application/json": {"schema": {"$ref": "#/components/schemas/Detail"}}}
    assert content("/jobs", "post", "409") == detail
    assert content("/runs/{run_id}", "get", "404") == detail
    assert set(content("/runs/{run_id}/markdown", "get", "200")) == {"text/markdown"}
    assert set(content("/runs/{run_id}/frames/{name}", "get", "200")) == {"image/webp"}
    assert [p["name"] for p in paths["/runs"]["get"]["parameters"]] == ["limit", "offset"]


def test_job_request_publishes_the_levels_it_accepts():
    level = spec()["components"]["schemas"]["JobRequest"]["properties"]["level"]
    assert level["enum"] == ["text", "frames", None]


def check(resp, status: int, model: type[BaseModel]) -> dict:
    assert resp.status_code == status, resp.text
    body = resp.json()
    model.model_validate(body)
    return body


def test_real_job_bodies_match_their_published_models():
    gate = threading.Event()
    client = TestClient(create_app(FakeTranscriber(gate), fake_download))
    job_id = check(client.post("/jobs", json={"url": URL}), 202, c.JobCreated)["id"]
    check(client.get(f"/jobs/{job_id}"), 200, c.JobView)
    check(client.post("/jobs", json={"url": URL}), 409, c.Detail)
    gate.set()
    wait_for(client, job_id)
    check(client.get(f"/jobs/{job_id}"), 200, c.JobView)
    check(client.get("/jobs/inconnu"), 404, c.Detail)
    check(client.post("/jobs", json={"url": "nope"}), 422, c.RequestError)
    check(client.post("/jobs", json={"url": URL, "level": "video"}), 422, c.RequestError)
    check(client.post("/jobs", json={"url": 5}), 422, c.RequestError)


def test_real_run_bodies_match_their_published_models(tmp_path):
    runs = RunStore(str(tmp_path / "runs.db"))
    client = TestClient(create_app(FakeTranscriber(), fake_download, runs, fake_capture))
    check(client.get("/runs/latest"), 404, c.Detail)
    run_id = client.post("/jobs", json={"url": URL, "level": "frames"}).json()["id"]
    assert wait_for(client, run_id)["stage"] == j.DONE

    def failing(url, dest):
        raise AudioError("Vidéo indisponible.")

    failed = TestClient(create_app(FakeTranscriber(), failing, runs))
    wait_for(failed, failed.post("/jobs", json={"url": URL}).json()["id"])

    listed = check(client.get("/runs"), 200, c.RunList)
    assert {r["state"] for r in listed["runs"]} == {j.DONE, j.ERROR}
    for run in listed["runs"]:
        check(client.get(f"/runs/{run['id']}"), 200, c.Run)
    run = check(client.get("/runs/latest"), 200, c.Run)
    assert len(run["frames"]) == 2 and run["segments"]
    check(client.get("/runs?limit=0"), 422, c.Detail)
    check(client.get("/runs/inconnu"), 404, c.Detail)
    check(client.get("/runs/inconnu/markdown"), 404, c.Detail)
    check(client.get(f"/runs/{run_id}/frames/9999.webp"), 404, c.Detail)
