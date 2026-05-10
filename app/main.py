from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import dev, health, webhooks
from app.core.logging import configure_logging
from app.db.base import init_db
from app.workers.queue import worker_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    worker_queue.start()
    try:
        yield
    finally:
        worker_queue.stop()


app = FastAPI(title="Sentra", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(dev.router, prefix="/api/dev", tags=["dev"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
