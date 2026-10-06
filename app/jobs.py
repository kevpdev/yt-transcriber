import threading
import uuid
from dataclasses import dataclass

QUEUED, DOWNLOADING, TRANSCRIBING, DONE, ERROR = (
    "queued",
    "downloading",
    "transcribing",
    "done",
    "error",
)
_FINISHED = {DONE, ERROR}
_KEEP = 20


class JobBusy(Exception):
    """Un job est déjà en cours, il n'y a qu'un GPU."""


@dataclass
class Job:
    id: str
    stage: str = QUEUED
    progress: float = 0.0
    text: str = ""
    error: str = ""

    def view(self) -> dict:
        return {
            "id": self.id,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "text": self.text,
            "error": self.error,
        }


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._active: Job | None = None

    def start(self) -> Job:
        with self._lock:
            if self._active and self._active.stage not in _FINISHED:
                raise JobBusy("Une transcription est déjà en cours, attends qu'elle se termine.")
            job = Job(id=uuid.uuid4().hex)
            self._active = job
            self._jobs[job.id] = job
            while len(self._jobs) > _KEEP:
                self._jobs.pop(next(iter(self._jobs)))
            return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def set_stage(self, job: Job, stage: str, progress: float = 0.0) -> None:
        with self._lock:
            job.stage = stage
            job.progress = progress

    def set_progress(self, job: Job, progress: float) -> None:
        job.progress = progress

    def finish(self, job: Job, text: str) -> None:
        with self._lock:
            job.text = text
            job.progress = 1.0
            job.stage = DONE

    def fail(self, job: Job, message: str) -> None:
        with self._lock:
            job.error = message
            job.stage = ERROR
