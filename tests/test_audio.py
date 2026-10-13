from pathlib import Path

import pytest

from app import audio
from app.audio import AudioError, download_audio


class FakeYoutubeDL:
    """Stands in for yt-dlp: `info` comes from extract_info, the download is recorded."""

    info: dict = {}
    downloaded: list = []

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        assert download is False
        return dict(self.info)

    def process_ie_result(self, info, download):
        self.downloaded.append(info["id"])
        self.opts["progress_hooks"][0]({"status": "downloading"})
        return info

    def prepare_filename(self, info):
        return f"/tmp/{info['id']}.webm"


@pytest.fixture
def ydl(monkeypatch):
    FakeYoutubeDL.downloaded = []
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL


@pytest.mark.parametrize("status", ["is_live", "is_upcoming"])
def test_a_live_in_progress_is_refused_without_downloading(ydl, tmp_path: Path, status):
    ydl.info = {"id": "abc", "live_status": status}
    with pytest.raises(AudioError, match="directs en cours"):
        download_audio("u", tmp_path)
    assert ydl.downloaded == []


@pytest.mark.parametrize("status", ["not_live", "was_live", "post_live", None])
def test_a_finished_or_regular_video_is_downloaded(ydl, tmp_path: Path, status):
    ydl.info = {"id": "abc", "live_status": status, "title": "T", "duration": 12.0}
    result = download_audio("u", tmp_path)
    assert (result.path, result.title, result.duration) == (Path("/tmp/abc.webm"), "T", 12.0)
    assert ydl.downloaded == ["abc"]


def test_the_progress_hook_calls_check_and_its_exception_leaves_download_audio(ydl, tmp_path):
    ydl.info = {"id": "abc"}

    class Stop(Exception):
        pass

    def check():
        raise Stop

    with pytest.raises(Stop):
        download_audio("u", tmp_path, check)


def test_no_check_is_a_no_op():
    assert audio.no_check() is None
