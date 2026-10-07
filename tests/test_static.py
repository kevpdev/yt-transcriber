from fastapi.testclient import TestClient

from app.fake import FakeTranscriber, fake_download
from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(FakeTranscriber(), fake_download))


def test_theme_css_is_served_as_css():
    resp = make_client().get("/static/theme.css")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/css")


def test_app_js_is_served_as_javascript():
    resp = make_client().get("/static/app.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]


def test_unknown_static_file_gives_404_without_stack_trace():
    resp = make_client().get("/static/unknown.js")
    assert resp.status_code == 404
    assert "Traceback" not in resp.text


def test_index_route_still_serves_the_page():
    resp = make_client().get("/")
    assert resp.status_code == 200
    assert "/static/app.js" in resp.text
