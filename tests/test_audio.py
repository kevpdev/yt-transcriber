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


def test_the_description_of_the_video_comes_out_of_the_download(ydl, tmp_path: Path):
    ydl.info = {"id": "abc", "description": "Line one\nhttps://example.com"}
    assert download_audio("u", tmp_path).description == "Line one\nhttps://example.com"


def test_the_description_is_none_when_the_video_has_none(ydl, tmp_path: Path):
    ydl.info = {"id": "abc", "title": "T"}
    assert download_audio("u", tmp_path).description is None


def test_on_info_gets_title_channel_and_duration_before_the_download(ydl, tmp_path: Path):
    ydl.info = {"id": "abc", "title": "T", "uploader": "U", "duration": 12.0}
    seen = []
    download_audio("u", tmp_path, on_info=lambda *info: seen.append((info, list(ydl.downloaded))))
    assert seen == [(("T", "U", 12.0), [])]


def test_on_info_is_never_called_for_a_live_in_progress(ydl, tmp_path: Path):
    ydl.info = {"id": "abc", "live_status": "is_live", "title": "T"}
    seen = []
    with pytest.raises(AudioError):
        download_audio("u", tmp_path, on_info=lambda *info: seen.append(info))
    assert seen == []


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
