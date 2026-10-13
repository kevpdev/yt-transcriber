import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


_LIVE = ("is_live", "is_upcoming")


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


def no_check() -> None:
    pass


def download_audio(url: str, dest_dir: Path, check: Callable[[], None] = no_check) -> Download:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    opts: Any = {
        "format": "bestaudio",
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "noprogress": True,
        # An exception raised by the hook leaves yt-dlp as it is, it stops the download.
        "progress_hooks": [lambda _: check()],
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("live_status") in _LIVE:
                raise AudioError(
                    "Les directs en cours ne sont pas pris en charge : attends la fin du direct."
                )
            info = ydl.process_ie_result(info, download=True)
            return Download(
                path=Path(ydl.prepare_filename(info)),
                title=info.get("title"),
                channel=info.get("channel") or info.get("uploader"),
                duration=info.get("duration"),
            )
    except DownloadError as exc:
        raise AudioError(readable_error(str(exc))) from exc
