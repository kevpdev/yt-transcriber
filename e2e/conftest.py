import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def video_url():
    return os.environ.get("E2E_VIDEO_URL", "https://www.youtube.com/watch?v=KnXm3PbNz5A")


@pytest.fixture(scope="session")
def e2e_level():
    # fake or real, set by scripts/e2e.sh. Empty: the level is not checked.
    return os.environ.get("E2E_LEVEL", "")


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Chromium runs as root in the container.
    return {**browser_type_launch_args, "args": ["--no-sandbox"]}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "permissions": ["clipboard-read", "clipboard-write"]}
