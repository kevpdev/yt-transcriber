import pytest

from app import fake


@pytest.fixture(autouse=True)
def no_fake_capture_delay(monkeypatch):
    """The 3 s pause of fake_capture only serves the browser tests."""
    monkeypatch.setattr(fake, "FAKE_CAPTURE_DELAY", 0)
