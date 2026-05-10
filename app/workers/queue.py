from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
from threading import Event, Thread

from app.core.logging import get_logger
from app.db.base import SessionLocal
from app.inference.pipeline import run_pipeline
from app.models.artifact import Artifact
from app.models.user import User
from app.models.verification_request import VerificationRequest
from app.services.messaging import send_result
from app.services.requests import mark_failed, save_pipeline_result
import asyncio

logger = get_logger(__name__)


class WorkerQueue:
    def __init__(self) -> None:
        self.queue: Queue[int] = Queue()
        self.stop_event = Event()
        self.thread: Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def enqueue(self, request_id: int) -> None:
        self.queue.put(request_id)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                request_id = self.queue.get(timeout=0.5)
            except Empty:
                continue

            with SessionLocal() as db:
                request = db.query(VerificationRequest).get(request_id)
                artifact = db.query(Artifact).filter(Artifact.request_id == request_id).one()
                user = db.query(User).get(request.user_id)
                request.status = "processing"
                db.commit()
                try:
                    result, debug = run_pipeline(
                        request_id=request_id,
                        file_path=__import__("pathlib").Path(artifact.source_path),
                        mime_type=artifact.mime_type,
                        expected_amount=str(request.expected_amount) if request.expected_amount else None,
                    )
                    save_pipeline_result(db, request_id, result, debug)
                    asyncio.run(send_result(user.whatsapp_id if user else "dev-user", result))
                except Exception as exc:
                    logger.exception("request failed", extra={"extra_payload": {"request_id": request_id}})
                    mark_failed(db, request_id, str(exc))
            self.queue.task_done()


worker_queue = WorkerQueue()
