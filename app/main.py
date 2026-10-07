import os
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import jobs as j
from .audio import AudioError, download_audio
from .fake import FakeTranscriber, fake_download
from .transcribe import Transcriber
from .urls import InvalidUrl, canonical_url, parse_video_id

STATIC = Path(__file__).parent / "static"


class JobRequest(BaseModel):
    url: str = ""


def create_app(transcriber=None, download=download_audio) -> FastAPI:
    transcriber = transcriber or Transcriber()
    store = j.JobStore()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if getattr(transcriber, "model", True) is None:
            transcriber.load()
        yield

    app = FastAPI(lifespan=lifespan)

    def work(job: j.Job, url: str) -> None:
        try:
            store.set_stage(job, j.DOWNLOADING)
            with tempfile.TemporaryDirectory() as tmp:
                audio = download(url, Path(tmp))
                store.set_stage(job, j.TRANSCRIBING)
                text = transcriber.run(audio, lambda p: store.set_progress(job, p))
            store.finish(job, text)
        except AudioError as exc:
            store.fail(job, str(exc))
        except Exception as exc:  # noqa: BLE001 - the job fails, the app keeps running
            store.fail(job, f"Erreur inattendue pendant la transcription : {exc}")

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
        threading.Thread(target=work, args=(job, canonical_url(video_id)), daemon=True).start()
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
    if os.environ.get("YT_FAKE") == "1":
        return create_app(FakeTranscriber(), fake_download)
    return create_app()
