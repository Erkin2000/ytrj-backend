import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from src.bulletin.enums import TASHKENT_TZ
from src.config import settings
from tests.conftest import data, db_run, png_bytes

BASE = "/api/v1/marketing/news"


def form(name: str = "TEST News", **extra) -> dict:
    body = {
        "title_ru": f"{name} ru",
        "title_uz": f"{name} uz",
        "title_en": f"{name} en",
        "text_ru": "Текст новости",
        "text_uz": "Yangilik matni",
        "text_en": "News text",
    }
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


def photo(name: str = "cover.png") -> dict:
    return {"photo": (name, png_bytes(), "image/png")}


@pytest.fixture
def marketing(api, role_ids):
    headers, me = api.staff(role_id=role_ids["MARKETING"], full_name="TEST Marketing")
    created: list[int] = []
    yield headers, me, created

    async def run(session):
        await session.execute(text("DELETE FROM news WHERE id = ANY(:ids)"), {"ids": created})

    if created:
        db_run(run)
        for news_id in created:
            shutil.rmtree(Path(settings.MEDIA_PATH) / "news" / str(news_id), ignore_errors=True)


def create(client, headers, created, files=None, **fields):
    r = client.post(BASE, headers=headers, data=form(**fields), files=files)
    if r.status_code == 201:
        created.append(data(r)["id"])
    return r


def public_ids(client) -> list[int]:
    return [n["id"] for n in data(client.get("/api/v1/news?per_page=100"))["items"]]


def test_publish_now_with_photo(client, marketing):
    headers, me, created = marketing
    r = create(client, headers, created, files=photo(), name="TEST Now")
    assert r.status_code == 201, r.text
    news = data(r)
    assert news["state"] == "PUBLISHED" and news["publish_at"]
    assert [t["language"] for t in news["translations"]] == ["ru", "uz", "en"]
    assert news["photo"]["url"] == f"{BASE}/{news['id']}/photo"
    assert news["created_by"]["id"] == me["id"]
    assert news["date"] == datetime.now(TASHKENT_TZ).date().isoformat()

    # Сайт: без токена, в ленте, фото открывается.
    assert news["id"] in public_ids(client)
    public = data(client.get(f"/api/v1/news/{news['id']}"))
    assert public["photo"]["url"] == f"/api/v1/news/{news['id']}/photo"
    assert "state" not in public and "created_by" not in public
    r = client.get(public["photo"]["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"

    # Замена и удаление фото.
    r = client.put(f"{BASE}/{news['id']}/photo", headers=headers, files=photo("new.png"))
    assert r.status_code == 200 and data(r)["photo"]["name"] == "new.png"
    r = client.delete(f"{BASE}/{news['id']}/photo", headers=headers)
    assert r.status_code == 200 and data(r)["photo"] is None
    assert client.get(f"/api/v1/news/{news['id']}/photo").status_code == 404

    # Не картинка — 400.
    bad = {"photo": ("doc.pdf", b"%PDF-1.4", "application/pdf")}
    r = client.put(f"{BASE}/{news['id']}/photo", headers=headers, files=bad)
    assert r.status_code == 400

    assert client.delete(f"{BASE}/{news['id']}", headers=headers).status_code == 200
    created.remove(news["id"])
    assert client.get(f"/api/v1/news/{news['id']}").status_code == 404


def test_scheduled_and_draft(client, marketing):
    headers, _, created = marketing
    future = (datetime.now(UTC) + timedelta(days=3)).isoformat()

    # Без фото, отложенная публикация.
    r = create(
        client,
        headers,
        created,
        name="TEST Later",
        status="SCHEDULED",
        publish_at=future,
        date="2026-12-01",
    )
    assert r.status_code == 201, r.text
    later = data(r)
    assert (
        later["state"] == "SCHEDULED" and later["photo"] is None and later["date"] == "2026-12-01"
    )
    assert later["id"] not in public_ids(client)
    assert client.get(f"/api/v1/news/{later['id']}").status_code == 404

    # Отложенная без даты или с датой в прошлом — ошибка.
    r = create(client, headers, created, status="SCHEDULED")
    assert r.status_code == 400 and r.json()["code"] == "news_schedule"
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    r = create(client, headers, created, status="SCHEDULED", publish_at=past)
    assert r.status_code == 400 and r.json()["code"] == "news_schedule"

    # Время наступило — новость видна на сайте без участия маркетинга.
    async def make_due(session):
        await session.execute(
            text("UPDATE news SET publish_at = now() - interval '1 minute' WHERE id = :id"),
            {"id": later["id"]},
        )

    db_run(make_due)
    assert later["id"] in public_ids(client)
    assert data(client.get(f"{BASE}/{later['id']}", headers=headers))["state"] == "PUBLISHED"

    # Черновик: не на сайте; публикация сейчас через PATCH.
    draft = data(create(client, headers, created, name="TEST Draft", status="DRAFT"))
    assert draft["state"] == "DRAFT" and draft["publish_at"] is None
    drafts = data(client.get(f"{BASE}?state=DRAFT&per_page=100", headers=headers))["items"]
    assert draft["id"] in [n["id"] for n in drafts]

    r = client.patch(f"{BASE}/{draft['id']}", headers=headers, json={"publish_at": future})
    assert r.status_code == 400 and r.json()["code"] == "news_schedule"
    r = client.patch(
        f"{BASE}/{draft['id']}", headers=headers, json={"status": "SCHEDULED", "publish_at": future}
    )
    assert r.status_code == 200 and data(r)["state"] == "SCHEDULED"
    r = client.patch(f"{BASE}/{draft['id']}", headers=headers, json={"status": "PUBLISHED"})
    assert r.status_code == 200 and data(r)["state"] == "PUBLISHED"
    assert draft["id"] in public_ids(client)

    # Перевод на три языка обязателен.
    r = client.patch(
        f"{BASE}/{draft['id']}",
        headers=headers,
        json={"translations": [{"language": "ru", "title": "Только ru", "text": "т"}]},
    )
    assert r.status_code == 422
    r = client.post(BASE, headers=headers, data={"title_ru": "Без перевода", "text_ru": "т"})
    assert r.status_code == 422

    # Снять с сайта.
    r = client.patch(f"{BASE}/{draft['id']}", headers=headers, json={"status": "DRAFT"})
    assert data(r)["state"] == "DRAFT" and draft["id"] not in public_ids(client)


def test_news_management_requires_permission(api, client, role_ids):
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    assert client.get(BASE, headers=fund).status_code == 403
    assert client.post(BASE, headers=fund, data=form()).status_code == 403
    assert client.get(BASE).status_code == 401
    assert client.get("/api/v1/news").status_code == 200
