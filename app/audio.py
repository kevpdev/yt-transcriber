import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class AudioError(Exception):
    """Download failed, the message is meant for the end user."""


def readable_error(raw: str, subject: str = "l'audio") -> str:
    text = _ANSI.sub("", raw).strip().splitlines()[-1] if raw.strip() else ""
    text = re.sub(r"^ERROR:\s*(\[[^\]]+\]\s*)?([\w-]{11}:\s*)?", "", text)
    return f"Impossible de télécharger {subject} : {text or 'erreur inconnue'}"


@dataclass
class Download:
    path: Path
    title: str | None = None
    channel: str | None = None
    duration: float | None = None


def download_audio(url: str, dest_dir: Path) -> Download:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    opts: Any = {
        "format": "bestaudio",
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "noprogress": True,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return Download(
                path=Path(ydl.prepare_filename(info)),
                title=info.get("title"),
                channel=info.get("channel") or info.get("uploader"),
                duration=info.get("duration"),
            )
    except DownloadError as exc:
        raise AudioError(readable_error(str(exc))) from exc
