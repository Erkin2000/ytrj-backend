"""Фоновая отправка отложенных бюллетеней (PENDING → PUBLISHED в `send_at`).

Запускается в lifespan приложения (BULLETIN_SCHEDULER_ENABLED). Строки берутся
с FOR UPDATE SKIP LOCKED, поэтому несколько процессов uvicorn не отправят один
бюллетень дважды. Списки бюллетеней дополнительно вызывают publish_due, так что
даже без фоновой задачи бюллетень отправится при первом обращении после `send_at`.
"""

import asyncio
import contextlib
import logging

from src.bulletin.services.bulletin_service import BulletinService
from src.config import settings
from src.database import async_session_maker
from src.utils.db_manager import DBManager

logger = logging.getLogger(__name__)


async def publish_due_once() -> int:
    async with DBManager(session_factory=async_session_maker) as db:
        return await BulletinService(db).publish_due()


async def run_scheduler() -> None:
    interval = max(settings.BULLETIN_SCHEDULER_INTERVAL_SECONDS, 5)
    while True:
        try:
            await publish_due_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — задача не должна умирать из-за одного сбоя
            logger.exception("Scheduled bulletin publication failed")
        await asyncio.sleep(interval)


@contextlib.asynccontextmanager
async def bulletin_scheduler():
    task = asyncio.create_task(run_scheduler()) if settings.BULLETIN_SCHEDULER_ENABLED else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
