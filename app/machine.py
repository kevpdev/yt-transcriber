"""Machine and library versions, read once. Every read returns None on failure, never raises."""

import contextlib
import os
import platform
import re
import subprocess
from importlib import metadata
from pathlib import Path

_PACKAGES = {
    "faster_whisper": "faster-whisper",
    "ctranslate2": "ctranslate2",
    "av": "av",
    "yt_dlp": "yt-dlp",
}


def _text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _cpu() -> tuple[str | None, int | None]:
    raw = _text("/proc/cpuinfo")
    if raw is None:
        return None, None
    model = re.search(r"^model name\s*:\s*(.+)$", raw, re.M)
    cores = len(re.findall(r"^processor\s*:", raw, re.M)) or None
    return (model.group(1).strip() if model else None), cores


def _ram_mb() -> int | None:
    raw = _text("/proc/meminfo")
    match = re.search(r"^MemTotal:\s*(\d+)\s*kB", raw or "", re.M)
    return int(match.group(1)) // 1024 if match else None


def _os_release() -> str | None:
    match = re.search(r'^PRETTY_NAME="?([^"\n]+)"?', _text("/etc/os-release") or "", re.M)
    return match.group(1) if match else None


def _nvidia_smi(*args: str) -> str | None:
    try:
        done = subprocess.run(
            ["nvidia-smi", *args], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _gpu() -> dict:
    gpu: dict = {"gpu": None, "gpu_memory_mb": None, "gpu_driver": None, "cuda": None}
    raw = _nvidia_smi(
        "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"
    )
    if raw and raw.strip():
        parts = [p.strip() for p in raw.strip().splitlines()[0].split(",")]
        if len(parts) == 3:
            gpu["gpu"] = parts[0]
            gpu["gpu_driver"] = parts[2]
            with contextlib.suppress(ValueError):
                gpu["gpu_memory_mb"] = int(parts[1])
    header = _nvidia_smi()
    match = re.search(r"CUDA Version:\s*([\d.]+)", header or "")
    gpu["cuda"] = match.group(1) if match else None
    return gpu


def read_machine() -> dict:
    cpu, cores = _cpu()
    try:
        host = platform.platform()
    except Exception:  # noqa: BLE001 - a machine read never raises
        host = None
    return {
        "cpu": cpu,
        "cpu_cores": cores,
        "ram_mb": _ram_mb(),
        **_gpu(),
        "os": host,
        "container_os": _os_release(),
        "docker": os.environ.get("HOST_DOCKER_VERSION") or None,
    }


def read_versions() -> dict:
    versions: dict = {}
    for key, dist in _PACKAGES.items():
        try:
            versions[key] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            versions[key] = None
    return versions
