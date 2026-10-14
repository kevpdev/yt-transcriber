import logging
import os
import queue
import re
import shutil
import sys
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import contract as c
from . import jobs as j
from .audio import AudioError, download_audio
from .fake import FakeTranscriber, fake_capture, fake_download
from .frames import capture_frames
from .machine import read_machine, read_versions
from .runs import Frame, RunStore, to_markdown
from .transcribe import Transcriber, hotwords, settings
from .urls import InvalidUrl, canonical_url, parse_video_id

STATIC = Path(__file__).parent / "static"
log = logging.getLogger(__name__)


LEVELS = ("text", "frames")
MAX_HOTWORDS = 500


def with_frame_urls(run: dict) -> dict:
    """Add the relative `url` that serves each image, next to its `path`."""
    for frame in run["frames"]:
        frame["url"] = f"/runs/{run['id']}/frames/{Path(frame['path']).name}"
    return run


class JobRequest(BaseModel):
    url: str = Field("", description="A YouTube video URL.")
    # Any type: a null or a number gets the French 422 below, not the pydantic one.
    # The enum is published in the schema only, it is checked by `create_job`.
    level: Any = Field(
        None,
        description="`frames` also captures the slides. Missing or null means `text`.",
        json_schema_extra={"enum": [*LEVELS, None], "default": "text"},
    )
    # Any type, checked by `create_job` like `level`, published as a nullable string.
    hotwords: Any = Field(
        None,
        description=f"Words Whisper must spell right, at most {MAX_HOTWORDS} characters. "
        "Missing, null or blank means the `HOTWORDS` default, see `GET /hotwords`.",
        json_schema_extra={"type": ["string", "null"], "maxLength": MAX_HOTWORDS, "default": None},
    )


def create_app(
    transcriber=None,
    download=download_audio,
    runs: RunStore | None = None,
    capture=capture_frames,
    timeout: float = j.JOB_TIMEOUT_S,
) -> FastAPI:
    transcriber = transcriber or Transcriber()
    store = j.JobStore()
    runs = runs or RunStore(":memory:")
    env: dict = {}
    pending: queue.Queue[tuple[j.Job, str, str]] = queue.Queue()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if getattr(transcriber, "model", True) is None:
            transcriber.load()
        env["machine"], env["versions"] = read_machine(), read_versions()
        yield

    app = FastAPI(lifespan=lifespan)

    def capture_images(job: j.Job, url: str, work_dir: Path, out_dir: Path) -> list[Frame]:
        # Losing a transcript for a failed image or a late capture costs more than having no
        # images. Only an explicit cancel ends the job in error.
        try:
            job.check()
            return capture(url, work_dir, out_dir, job.check)
        except j.JobStopped as exc:
            shutil.rmtree(out_dir, ignore_errors=True)
            if exc.cancelled:
                raise
            # The time limit hit during the capture: keep the transcript, drop the images.
            log.warning("Capture of run %s stopped by the time limit: %s", job.id, exc)
            return []
        except Exception:  # noqa: BLE001 - the job stays done, without images
            log.exception("Could not capture frames for run %s", job.id)
            shutil.rmtree(out_dir, ignore_errors=True)
            return []

    def progress(job: j.Job, value: float) -> None:
        # Every progress report is a checkpoint, the transcriber calls it for each segment.
        job.check()
        store.set_progress(job, value)

    def work(job: j.Job, video_id: str, url: str) -> None:
        started_at = datetime.now(UTC).isoformat()
        t0 = time.monotonic()
        t_download = t_transcribe = None
        meta = None
        result = None
        images: list[Frame] = []
        error = None
        log.info("Job %s started: %s, level %s", job.id, url, "frames" if job.frames else "text")
        try:
            # A job cancelled while it waited in the queue stops here, before any download.
            job.check()
            store.set_stage(job, j.DOWNLOADING)
            with tempfile.TemporaryDirectory() as tmp:
                meta = download(
                    url,
                    Path(tmp),
                    job.check,
                    lambda title, channel, duration: store.set_info(job, title, channel, duration),
                )
                t_download = time.monotonic() - t0
                job.check()
                store.set_stage(job, j.TRANSCRIBING)
                result = transcriber.run(meta.path, lambda p: progress(job, p), job.hotwords)
                t_transcribe = time.monotonic() - t0 - t_download
                if job.frames:
                    store.set_stage(job, j.EXTRACTING)
                    if runs.frames_dir:
                        images = capture_images(job, url, Path(tmp), runs.frames_dir / job.id)
        except j.JobStopped as exc:
            log.info("Job %s stopped: %s", job.id, exc)
            error = str(exc)
        except AudioError as exc:
            # The cause is the last line of the traceback, the header does not repeat it.
            log.exception("Job %s failed to download", job.id)
            error = str(exc)
        except Exception as exc:  # noqa: BLE001 - the job fails, the app keeps running
            log.exception("Job %s failed with an unexpected error", job.id)
            error = f"Erreur inattendue pendant la transcription : {exc}"
        done = error is None and result is not None
        # The row is written before the job is published as finished, so a reader that sees
        # done or error finds the run in the database.
        try:
            runs.record(
                id=job.id,
                video_id=video_id,
                url=url,
                title=meta.title if meta else None,
                channel=meta.channel if meta else None,
                video_duration=meta.duration if meta else None,
                level="frames" if job.frames else "text",
                state=j.DONE if done else j.ERROR,
                error=error,
                text=result.text if done and result else None,
                word_count=len(result.text.split()) if done and result else None,
                char_count=len(result.text) if done and result else None,
                language=result.language if result else None,
                language_probability=result.language_probability if result else None,
                started_at=started_at,
                download_s=t_download,
                transcribe_s=t_transcribe,
                total_s=time.monotonic() - t0,
                speed_ratio=meta.duration / t_transcribe
                if meta and meta.duration and t_transcribe
                else None,
                settings=settings(job.hotwords),
                machine=env.get("machine", {}),
                versions=env.get("versions", {}),
                segments=result.segments if done and result else (),
                frames=images if done else (),
            )
        except Exception:  # noqa: BLE001 - a storage failure never changes the job
            log.exception("Could not record run %s", job.id)
            if runs.frames_dir:
                shutil.rmtree(runs.frames_dir / job.id, ignore_errors=True)
        # Logged before the job is published, so a reader that sees it finished finds the line.
        log.info(
            "Job %s finished: %s in %.1f s",
            job.id,
            j.DONE if done else j.ERROR,
            time.monotonic() - t0,
        )
        if done and result:
            store.finish(job, result.text, result.segments)
        else:
            store.fail(job, error or "Erreur inattendue pendant la transcription.")

    def consume() -> None:
        # The single consumer: one GPU, so one job at a time, in the order of arrival.
        while True:
            job, video_id, url = pending.get()
            job.begin()
            try:
                work(job, video_id, url)
            except Exception:  # noqa: BLE001 - `work` catches everything, this keeps the loop alive
                log.exception("Job %s crashed the worker", job.id)

    threading.Thread(target=consume, daemon=True).start()

    @app.post(
        "/jobs",
        status_code=202,
        responses={
            202: {"model": c.JobCreated, "description": "Job queued, poll it with its id."},
            422: c.error("Invalid YouTube URL, level or hotwords.", c.RequestError),
        },
    )
    def create_job(req: JobRequest):
        try:
            video_id = parse_video_id(req.url)
        except InvalidUrl as exc:
            return JSONResponse({"detail": str(exc)}, status_code=422)
        level = "text" if req.level is None else req.level
        if level not in LEVELS:
            return JSONResponse(
                {"detail": f"Le niveau doit être {' ou '.join(LEVELS)}."}, status_code=422
            )
        words = req.hotwords
        if words is not None and (not isinstance(words, str) or len(words) > MAX_HOTWORDS):
            return JSONResponse(
                {
                    "detail": "Les hotwords doivent être un texte "
                    f"de {MAX_HOTWORDS} caractères au plus."
                },
                status_code=422,
            )
        words = (words or "").strip() or hotwords()
        job = store.start(frames=level == "frames", timeout=timeout, hotwords=words)
        pending.put((job, video_id, canonical_url(video_id)))
        return {"id": job.id}

    @app.post(
        "/jobs/{job_id}/cancel",
        status_code=202,
        responses={
            202: {"model": c.JobCancel, "description": "Stop requested, poll the job."},
            404: c.error("Unknown job."),
            409: c.error("The job is already finished."),
        },
    )
    def cancel_job(job_id: str):
        requested = store.cancel(job_id)
        if requested is None:
            return JSONResponse({"detail": "Job inconnu."}, status_code=404)
        if not requested:
            return JSONResponse({"detail": "Ce job est déjà terminé."}, status_code=409)
        return {"id": job_id}

    @app.get(
        "/jobs/{job_id}",
        responses={200: {"model": c.JobView}, 404: c.error("Unknown job.")},
    )
    def get_job(job_id: str):
        job = store.get(job_id)
        if job is None:
            return JSONResponse({"detail": "Job inconnu."}, status_code=404)
        return job.view()

    @app.get("/hotwords", responses={200: {"model": c.Hotwords}})
    def get_hotwords():
        return {"default": hotwords()}

    def int_param(request: Request, name: str, default: int, low: int, high: int | None) -> int:
        raw = request.query_params.get(name)
        if raw is None:
            return default
        value = int(raw) if re.fullmatch(r"-?[0-9]+", raw) else None
        if value is None or value < low or (high is not None and value > high):
            bounds = f"entre {low} et {high}" if high is not None else f"supérieur ou égal à {low}"
            raise HTTPException(
                status_code=422,
                detail=f"Le paramètre {name} doit être un entier {bounds}.",
            )
        return value

    @app.get(
        "/runs",
        responses={200: {"model": c.RunList}, 422: c.error("Invalid limit or offset.")},
        # Read by `int_param` and only declared here: a Query(int) would answer in English.
        openapi_extra={"parameters": c.PAGINATION},
    )
    def list_runs(request: Request):
        limit = int_param(request, "limit", 20, 1, 100)
        offset = int_param(request, "offset", 0, 0, None)
        return {
            "runs": runs.list_runs(limit, offset),
            "total": runs.count(),
            "limit": limit,
            "offset": offset,
        }

    @app.get(
        "/runs/latest",
        responses={200: {"model": c.Run}, 404: c.error("No run is done.")},
    )
    def get_latest_run():
        run_id = runs.latest_id()
        run = runs.get_run(run_id) if run_id else None
        if run is None:
            return JSONResponse({"detail": "Aucun run réussi."}, status_code=404)
        return with_frame_urls(run)

    @app.get(
        "/runs/{run_id}",
        responses={200: {"model": c.Run}, 404: c.error("Unknown run.")},
    )
    def get_run(run_id: str):
        run = runs.get_run(run_id)
        if run is None:
            return JSONResponse({"detail": "Run inconnu."}, status_code=404)
        return with_frame_urls(run)

    @app.get(
        "/runs/{run_id}/frames/{name}",
        response_class=Response,
        responses={
            200: c.content("image/webp", c.BINARY, "The image of one captured slide."),
            404: c.error("Unknown run, or a name that is not an image of the run."),
        },
    )
    def get_run_frame(run_id: str, name: str):
        if not runs.has_run(run_id):
            return JSONResponse({"detail": "Run inconnu."}, status_code=404)
        file = runs.frame_file(run_id, name)
        if file is None:
            return JSONResponse({"detail": "Image inconnue."}, status_code=404)
        return FileResponse(file, media_type="image/webp")

    @app.get(
        "/runs/{run_id}/markdown",
        response_class=Response,
        responses={
            200: c.content(
                "text/markdown",
                c.TEXT,
                "UTF-8. `# <title, or the video_id without one>`, a blank line, then one "
                "`[mm:ss] text` line per segment, `[h:mm:ss]` from one hour.",
            ),
            404: c.error("Unknown run."),
        },
    )
    def get_run_markdown(run_id: str):
        run = runs.get_run(run_id)
        if run is None:
            return JSONResponse({"detail": "Run inconnu."}, status_code=404)
        return Response(to_markdown(run), media_type="text/markdown; charset=utf-8")

    @app.get(
        "/",
        response_class=HTMLResponse,
        responses={200: c.content("text/html", c.TEXT, "The page.")},
    )
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    return app


def setup_logging() -> None:
    """Send the INFO logs of the `app` package to stdout, read by `docker compose logs`.

    Uvicorn configures only its own loggers: without this, an INFO line is lost and an
    ERROR line goes out bare, through the `lastResort` handler of `logging`.
    """
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)


def build_app() -> FastAPI:
    # started by `uvicorn --factory app.main:build_app`, tests import it without a GPU
    setup_logging()
    runs = RunStore(os.environ.get("YT_DB", "/data/runs.db"))
    if os.environ.get("YT_FAKE") == "1":
        return create_app(FakeTranscriber(), fake_download, runs, fake_capture)
    return create_app(runs=runs)
