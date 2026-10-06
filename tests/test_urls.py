import pytest

from app.urls import InvalidUrl, canonical_url, parse_video_id

VID = "gsxiFd8AZQU"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?v={VID}&t=30s",
        f"https://m.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}",
        f"https://youtu.be/{VID}?si=abc",
        f"https://www.youtube.com/shorts/{VID}",
        f"  https://www.youtube.com/watch?v={VID}  ",
    ],
)
def test_accepts_youtube_urls(url):
    assert parse_video_id(url) == VID


@pytest.mark.parametrize(
    "url",
    ["", "   ", "abc", "https://example.com/watch?v=" + VID, "ftp://youtube.com/watch?v=" + VID,
     "https://www.youtube.com/watch", "https://www.youtube.com/watch?v=court", "https://www.youtube.com/"],
)
def test_rejects_other_input_with_a_message(url):
    with pytest.raises(InvalidUrl) as exc:
        parse_video_id(url)
    assert str(exc.value)


def test_canonical_url_drops_extra_params():
    assert canonical_url(VID) == f"https://www.youtube.com/watch?v={VID}"
