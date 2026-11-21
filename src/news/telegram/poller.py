"""Фоновый опрос Telegram (long polling) в lifespan приложения.

Включается, если задан TELEGRAM_BOT_TOKEN и TELEGRAM_POLLING_ENABLED. Опрос должен
идти из одного процесса: при втором опрашивающем процессе Telegram отвечает 409,
и этот процесс ждёт и пробует снова. Подтверждённые обновления Telegram больше не
отдаёт; неподтверждённые после перезапуска приходят повторно — дубля не будет.
"""

import asyncio
import contextlib
import logging

from src.config import settings
from src.database import async_session_maker
from src.news.telegram.client import TelegramClient, TelegramError
from src.news.telegram.commands import handle_message
from src.news.telegram.service import TelegramNewsService
from src.utils.db_manager import DBManager

logger = logging.getLogger(__name__)


async def handle(client: TelegramClient, update: dict) -> None:
    if "message" in update:
        await handle_message(client, update)
        return
    async with DBManager(session_factory=async_session_maker) as db:
        await TelegramNewsService(db, client).handle_update(update)


async def run_poller() -> None:
    client = TelegramClient()
    offset: int | None = None
    try:
        while True:
            try:
                me = await client.get_me()
                await client.delete_webhook()
                logger.info("Telegram bot @%s: polling channel posts", me.get("username"))
                break
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001
                logger.warning("Telegram bot is not reachable, retry in 60 s: %s", error)
                await asyncio.sleep(60)

        while True:
            try:
                updates = await client.get_updates(offset)
            except asyncio.CancelledError:
                raise
            except TelegramError as error:
                delay = 30 if error.status in (401, 409) else 5
                logger.warning("Telegram getUpdates failed, retry in %s s: %s", delay, error)
                await asyncio.sleep(delay)
                continue
            except Exception as error:  # noqa: BLE001 — сеть: ждём и пробуем снова
                logger.warning("Telegram getUpdates error, retry in 5 s: %s", error)
                await asyncio.sleep(5)
                continue

            for update in updates or []:
                offset = int(update["update_id"]) + 1
                try:
                    await handle(client, update)
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001 — один плохой пост не останавливает бота
                    logger.exception("Telegram update %s is skipped", update.get("update_id"))
    finally:
        await client.close()


@contextlib.asynccontextmanager
async def telegram_poller():
    enabled = bool(settings.TELEGRAM_BOT_TOKEN) and settings.TELEGRAM_POLLING_ENABLED
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.info("Telegram bot is off: TELEGRAM_BOT_TOKEN is empty")
    elif not settings.TELEGRAM_POLLING_ENABLED:
        logger.info("Telegram bot is off: TELEGRAM_POLLING_ENABLED=false")
    if enabled and not settings.telegram_channels:
        logger.warning(
            "TELEGRAM_CHANNELS is empty: the bot ignores all posts and logs the channel id "
            "of every post it receives"
        )
    task = asyncio.create_task(run_poller()) if enabled else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
