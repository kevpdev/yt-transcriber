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
    # fake ou real, posé par scripts/e2e.sh. Vide : le niveau n'est pas contrôlé.
    return os.environ.get("E2E_LEVEL", "")


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Chromium tourne en root dans le conteneur.
    return {**browser_type_launch_args, "args": ["--no-sandbox"]}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "permissions": ["clipboard-read", "clipboard-write"]}
