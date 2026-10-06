import re
from pathlib import Path

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class AudioError(Exception):
    """Téléchargement impossible, le message est destiné à l'utilisateur."""


def _readable(raw: str) -> str:
    text = _ANSI.sub("", raw).strip().splitlines()[-1] if raw.strip() else ""
    text = re.sub(r"^ERROR:\s*(\[[^\]]+\]\s*)?([\w-]{11}:\s*)?", "", text)
    return f"Impossible de télécharger l'audio : {text or 'erreur inconnue'}"


def download_audio(url: str, dest_dir: Path) -> Path:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    opts = {
        "format": "bestaudio",
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "noprogress": True,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return Path(ydl.prepare_filename(info))
    except DownloadError as exc:
        raise AudioError(_readable(str(exc))) from exc
