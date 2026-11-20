"""Пост Telegram-канала → новость. Клиент Telegram подменён: сеть не нужна."""

import asyncio
import random
import shutil
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
from src.news.telegram.service import TelegramNewsService, split_post
from src.utils.db_manager import DBManager
from tests.conftest import data, db_run, png_bytes

CHANNEL = {
    "id": -1009990000000 - random.randint(1, 999999),
    "type": "channel",
    "title": "TEST Yoshlar fondi",
    "username": "test_yoshlar_fondi",
}
STRANGER = {"id": -1008880000001, "type": "channel", "title": "Чужой канал", "username": "stranger"}


class FakeClient:
    def __init__(self):
        self.downloads: list[str] = []

    async def download_file(self, file_id: str) -> bytes:
        self.downloads.append(file_id)
        return png_bytes()


def post(message_id: int, chat=None, edited=False, **fields) -> dict:
    body = {"message_id": message_id, "chat": chat or CHANNEL, "date": 1795000000, **fields}
    return {"update_id": message_id, ("edited_channel_post" if edited else "channel_post"): body}


def photo(file_id: str) -> list[dict]:
    return [
        {"file_id": f"{file_id}-small", "width": 90, "height": 90, "file_size": 1000},
        {"file_id": file_id, "width": 1280, "height": 960, "file_size": 90000},
    ]


@pytest.fixture
def bot(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_CHANNELS", f"@{CHANNEL['username']}, -100123")
    engine = create_async_engine(settings.DB_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    client = FakeClient()

    def handle(update: dict):
        async def run():
            async with DBManager(session_factory=sessions) as db:
                news = await TelegramNewsService(db, client).handle_update(update)
                return news.id if news is not None else None

        return asyncio.run(run())

    yield handle, client

    async def cleanup(session):
        ids = [
            r[0]
            for r in await session.execute(
                text("SELECT id FROM news WHERE telegram_chat_id = ANY(:c)"),
                {"c": [CHANNEL["id"], STRANGER["id"]]},
            )
        ]
        await session.execute(text("DELETE FROM news WHERE id = ANY(:ids)"), {"ids": ids})
        for news_id in ids:
            shutil.rmtree(Path(settings.MEDIA_PATH) / "news" / str(news_id), ignore_errors=True)

    db_run(cleanup)
    asyncio.run(engine.dispose())


def test_split_post():
    assert split_post("Заголовок\n\nПервый абзац\nВторой") == ("Заголовок", "Первый абзац\nВторой")
    assert split_post("Одна строка") == ("Одна строка", "Одна строка")
    title, _ = split_post("слово " * 100)
    assert len(title) <= 201 and title.endswith("…")


def test_channel_post_becomes_published_news(client, superadmin, bot):
    handle, fake = bot
    news_id = handle(post(101, caption="Jamgʻarma yangiligi\nBatafsil matn", photo=photo("big")))
    assert news_id is not None
    assert fake.downloads == ["big"]  # самое крупное фото

    public = data(client.get(f"/api/v1/news/{news_id}"))
    titles = {t["language"]: t["title"] for t in public["translations"]}
    assert titles == {
        "ru": "Jamgʻarma yangiligi",
        "uz": "Jamgʻarma yangiligi",
        "en": "Jamgʻarma yangiligi",
    }
    assert public["translations"][0]["text"] == "Batafsil matn"
    assert public["photo"] and client.get(public["photo"]["url"]).status_code == 200

    detail = data(client.get(f"/api/v1/marketing/news/{news_id}", headers=superadmin))
    assert detail["source"] == "TELEGRAM" and detail["state"] == "PUBLISHED"
    assert detail["telegram_url"] == f"https://t.me/{CHANNEL['username']}/101"
    assert detail["created_by"] is None
    listed = data(
        client.get("/api/v1/marketing/news?source=TELEGRAM&per_page=100", headers=superadmin)
    )
    assert news_id in [n["id"] for n in listed["items"]]

    # Повтор того же поста — без дубля.
    assert handle(post(101, caption="Jamgʻarma yangiligi\nBatafsil matn")) is None

    # Правка в канале обновляет текст.
    assert handle(post(101, edited=True, text="Yangi sarlavha\nYangi matn")) == news_id
    assert (
        data(client.get(f"/api/v1/news/{news_id}"))["translations"][0]["title"] == "Yangi sarlavha"
    )

    # После правки в админке правки канала больше не применяются.
    client.patch(
        f"/api/v1/marketing/news/{news_id}", headers=superadmin, json={"date": "2026-11-21"}
    )
    assert handle(post(101, edited=True, text="Ещё правка")) is None
    assert (
        data(client.get(f"/api/v1/news/{news_id}"))["translations"][0]["title"] == "Yangi sarlavha"
    )


def test_album_text_only_and_skipped_posts(client, bot):
    handle, fake = bot
    # Альбом: подпись у второго сообщения, фото первого — без подписи.
    assert handle(post(201, media_group_id="alb1", photo=photo("a1"))) is None
    album_id = handle(post(202, media_group_id="alb1", caption="Albom", photo=photo("a2")))
    assert album_id is not None
    assert handle(post(203, media_group_id="alb1", photo=photo("a3"))) is None  # фото уже есть
    assert fake.downloads == ["a2"]

    # Текст без фото.
    text_id = handle(post(204, text="Faqat matn"))
    assert data(client.get(f"/api/v1/news/{text_id}"))["photo"] is None

    # Пропускаются: без текста, чужой канал, не канал.
    assert handle(post(205, photo=photo("p"))) is None
    assert handle(post(206, chat=STRANGER, text="Begona kanal")) is None
    group = {"id": -100555, "type": "supergroup", "title": "Guruh"}
    assert (
        handle({"update_id": 207, "message": {"message_id": 207, "chat": group, "text": "x"}})
        is None
    )
