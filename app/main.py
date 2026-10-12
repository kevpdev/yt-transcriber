import logging
import os
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import jobs as j
from .audio import AudioError, download_audio
from .fake import FakeTranscriber, fake_download
from .machine import read_machine, read_versions
from .runs import RunStore
from .transcribe import Transcriber, settings
from .urls import InvalidUrl, canonical_url, parse_video_id

STATIC = Path(__file__).parent / "static"
log = logging.getLogger(__name__)


class JobRequest(BaseModel):
    url: str = ""


def create_app(transcriber=None, download=download_audio, runs: RunStore | None = None) -> FastAPI:
    transcriber = transcriber or Transcriber()
    store = j.JobStore()
    runs = runs or RunStore(":memory:")
    env: dict = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if getattr(transcriber, "model", True) is None:
            transcriber.load()
        env["machine"], env["versions"] = read_machine(), read_versions()
        yield

    app = FastAPI(lifespan=lifespan)

    def work(job: j.Job, video_id: str, url: str) -> None:
        started_at = datetime.now(UTC).isoformat()
        t0 = time.monotonic()
        t_download = t_transcribe = None
        meta = None
        result = None
        try:
            store.set_stage(job, j.DOWNLOADING)
            with tempfile.TemporaryDirectory() as tmp:
                meta = download(url, Path(tmp))
                t_download = time.monotonic() - t0
                store.set_stage(job, j.TRANSCRIBING)
                result = transcriber.run(meta.path, lambda p: store.set_progress(job, p))
                t_transcribe = time.monotonic() - t0 - t_download
            store.finish(job, result.text)
        except AudioError as exc:
            store.fail(job, str(exc))
        except Exception as exc:  # noqa: BLE001 - the job fails, the app keeps running
            store.fail(job, f"Erreur inattendue pendant la transcription : {exc}")
        finally:
            try:
                runs.record(
                    id=job.id,
                    video_id=video_id,
                    url=url,
                    title=meta.title if meta else None,
                    channel=meta.channel if meta else None,
                    video_duration=meta.duration if meta else None,
                    state=job.stage,
                    error=job.error or None,
                    text=result.text if result and job.stage == j.DONE else None,
                    word_count=len(result.text.split()) if result and job.stage == j.DONE else None,
                    char_count=len(result.text) if result and job.stage == j.DONE else None,
                    language=result.language if result else None,
                    language_probability=result.language_probability if result else None,
                    started_at=started_at,
                    download_s=t_download,
                    transcribe_s=t_transcribe,
                    total_s=time.monotonic() - t0,
                    speed_ratio=meta.duration / t_transcribe
                    if meta and meta.duration and t_transcribe
                    else None,
                    settings=settings(),
                    machine=env.get("machine", {}),
                    versions=env.get("versions", {}),
                )
            except Exception:  # noqa: BLE001 - a storage failure never changes the job
                log.exception("Could not record run %s", job.id)

    @app.post("/jobs", status_code=202)
    def create_job(req: JobRequest):
        try:
            video_id = parse_video_id(req.url)
        except InvalidUrl as exc:
            return JSONResponse({"detail": str(exc)}, status_code=422)
        try:
            job = store.start()
        except j.JobBusy as exc:
            return JSONResponse({"detail": str(exc)}, status_code=409)
        threading.Thread(
            target=work, args=(job, video_id, canonical_url(video_id)), daemon=True
        ).start()
        return {"id": job.id}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str):
        job = store.get(job_id)
        if job is None:
            return JSONResponse({"detail": "Job inconnu."}, status_code=404)
        return job.view()

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    return app


def build_app() -> FastAPI:
    # started by `uvicorn --factory app.main:build_app`, tests import it without a GPU
    runs = RunStore(os.environ.get("YT_DB", "/data/runs.db"))
    if os.environ.get("YT_FAKE") == "1":
        return create_app(FakeTranscriber(), fake_download, runs)
    return create_app(runs=runs)
