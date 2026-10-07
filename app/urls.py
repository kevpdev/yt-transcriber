import os
import re
from urllib.parse import parse_qs, urlparse

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}


class InvalidUrl(ValueError):
    """URL rejected, the message is meant for the end user."""


def parse_video_id(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise InvalidUrl("Colle d'abord une URL YouTube.")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise InvalidUrl("Ce n'est pas une URL http(s) : colle l'adresse complète de la vidéo.")
    host = parsed.hostname.lower()
    candidate = None
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in _HOSTS:
        if parsed.path == "/watch":
            candidate = (parse_qs(parsed.query).get("v") or [""])[0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) == 2 and parts[0] in ("shorts", "live", "embed"):
                candidate = parts[1]
    else:
        raise InvalidUrl("Ce n'est pas une URL YouTube.")
    if not candidate or not _VIDEO_ID.match(candidate):
        raise InvalidUrl("Je ne trouve pas d'identifiant de vidéo YouTube dans cette URL.")
    return candidate


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
