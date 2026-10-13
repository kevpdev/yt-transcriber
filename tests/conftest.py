import logging

import pytest

from app import fake


@pytest.fixture(autouse=True)
def no_fake_capture_delay(monkeypatch):
    """The 3 s pause of fake_capture only serves the browser tests."""
    monkeypatch.setattr(fake, "FAKE_CAPTURE_DELAY", 0)


@pytest.fixture(autouse=True)
def restore_app_logger():
    """build_app adds a stdout handler to the `app` logger, the next test must not inherit it."""
    logger = logging.getLogger("app")
    handlers, level = logger.handlers[:], logger.level
    yield
    logger.handlers[:] = handlers
    logger.setLevel(level)
