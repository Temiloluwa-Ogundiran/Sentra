from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic, sleep

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import SessionLocal
from app.inference.pipeline import run_pipeline
from app.models.artifact import Artifact
from app.models.user import User
from app.models.verification_request import VerificationRequest
from app.services.messaging import send_processing_update, send_result, send_typing_indicator
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
        self.stop_event.clear()
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def enqueue(self, request_id: int) -> None:
        logger.info("enqueued verification request", extra={"extra_payload": {"request_id": request_id}})
        self.queue.put(request_id)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                request_id = self.queue.get(timeout=0.5)
            except Empty:
                continue

            self.process_request(request_id)
            self.queue.task_done()

    def process_request(self, request_id: int) -> None:
        with SessionLocal() as db:
            request = db.get(VerificationRequest, request_id)
            if request is None:
                logger.warning("request missing", extra={"extra_payload": {"request_id": request_id}})
                return

            artifact = db.query(Artifact).filter(Artifact.request_id == request_id).one()
            user = db.get(User, request.user_id)
            request.status = "processing"
            db.commit()
            logger.info(
                "started processing request",
                extra={
                    "extra_payload": {
                        "request_id": request_id,
                        "whatsapp_id": user.whatsapp_id if user else None,
                        "artifact_path": artifact.source_path,
                        "mime_type": artifact.mime_type,
                    }
                },
            )
            notifier_stop = Event()
            stage_state = {"stage": "received"}
            user_result_started = {"value": False}

            def stage_callback(stage: str) -> None:
                stage_state["stage"] = stage
                logger.info(
                    "pipeline stage transition",
                    extra={"extra_payload": {"request_id": request_id, "stage": stage}},
                )

            def typing_loop() -> None:
                if user is None:
                    return
                while not notifier_stop.is_set():
                    try:
                        asyncio.run(send_typing_indicator(user.whatsapp_id))
                    except Exception:
                        logger.exception(
                            "typing indicator failed",
                            extra={"extra_payload": {"request_id": request_id, "whatsapp_id": user.whatsapp_id}},
                        )
                    notifier_stop.wait(settings.typing_refresh_interval_seconds)

            def progress_heartbeat_loop() -> None:
                if user is None:
                    return
                last_sent_at = monotonic()
                while not notifier_stop.is_set():
                    sleep(1)
                    if notifier_stop.is_set():
                        break
                    if monotonic() - last_sent_at < settings.processing_progress_interval_seconds:
                        continue
                    try:
                        asyncio.run(send_processing_update(user.whatsapp_id, stage_state["stage"]))
                        last_sent_at = monotonic()
                    except Exception:
                        logger.exception(
                            "processing heartbeat update failed",
                            extra={"extra_payload": {"request_id": request_id, "stage": stage_state["stage"]}},
                        )

            typing_thread = Thread(target=typing_loop, daemon=True)
            heartbeat_thread = Thread(target=progress_heartbeat_loop, daemon=True)
            typing_thread.start()
            heartbeat_thread.start()
            try:
                result, debug = run_pipeline(
                    request_id=request_id,
                    file_path=__import__("pathlib").Path(artifact.source_path),
                    mime_type=artifact.mime_type,
                    expected_amount=str(request.expected_amount) if request.expected_amount else None,
                    stage_callback=stage_callback,
                )
                save_pipeline_result(db, request_id, result, debug)
                if user is not None:
                    try:
                        user_result_started["value"] = True
                        asyncio.run(send_result(user.whatsapp_id, result))
                    except Exception:
                        logger.exception(
                            "final result delivery failed",
                            extra={"extra_payload": {"request_id": request_id, "whatsapp_id": user.whatsapp_id}},
                        )
            except Exception as exc:
                logger.exception("request failed", extra={"extra_payload": {"request_id": request_id}})
                mark_failed(db, request_id, str(exc))
                if user is not None and not user_result_started["value"]:
                    try:
                        asyncio.run(send_processing_update(user.whatsapp_id, "failed"))
                    except Exception:
                        logger.exception(
                            "failed to send failure progress update",
                            extra={"extra_payload": {"request_id": request_id, "whatsapp_id": user.whatsapp_id}},
                        )
            finally:
                notifier_stop.set()
                typing_thread.join(timeout=1)
                heartbeat_thread.join(timeout=1)


worker_queue = WorkerQueue()
