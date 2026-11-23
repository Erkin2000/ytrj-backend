"""Контент сайта: события, «О нас», члены Совета и руководство (маркетинг)."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import text

from src.config import settings
from tests.conftest import data, db_run, png_bytes


def title_text(name: str) -> list[dict]:
    return [
        {"language": "ru", "title": f"{name} ru", "text": "Текст"},
        {"language": "uz", "title": f"{name} uz", "text": "Matn"},
        {"language": "en", "title": f"{name} en", "text": "Text"},
    ]


def event_form(name: str, day: str, **extra) -> dict:
    body = {"date": day}
    for lang, text_ in (("ru", "Текст"), ("uz", "Matn"), ("en", "Text")):
        body[f"title_{lang}"] = f"{name} {lang}"
        body[f"text_{lang}"] = text_
    body.update({k: str(v).lower() if isinstance(v, bool) else v for k, v in extra.items()})
    return body


def person_form(name: str, **extra) -> dict:
    body = {
        "full_name_ru": f"{name} Ру",
        "full_name_uz": f"{name} Uz",
        "full_name_en": f"{name} En",
        "description_ru": "Член Совета",
        "description_uz": "Kengash aʼzosi",
        "description_en": "Council member",
    }
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


@pytest.fixture
def marketing(api, role_ids):
    headers, _ = api.staff(role_id=role_ids["MARKETING"], full_name="TEST Marketing")
    created = {
        "site_events": [],
        "site_about_sections": [],
        "site_people": [],
        "site_contacts": [],
        "site_testimonials": [],
    }
    yield headers, created

    async def run(session):
        for table, ids in created.items():
            if ids:
                await session.execute(
                    text(f"DELETE FROM {table} WHERE id = ANY(:ids)"), {"ids": ids}
                )

    db_run(run)
    for person_id in created["site_people"]:
        shutil.rmtree(Path(settings.MEDIA_PATH) / "site" / "people" / str(person_id), True)
    for event_id in created["site_events"]:
        shutil.rmtree(Path(settings.MEDIA_PATH) / "site" / "events" / str(event_id), True)
    for testimonial_id in created["site_testimonials"]:
        shutil.rmtree(
            Path(settings.MEDIA_PATH) / "site" / "testimonials" / str(testimonial_id), True
        )


def test_events_crud(client, marketing):
    headers, created = marketing
    r = client.post(
        "/api/v1/marketing/events", headers=headers, data=event_form("TEST Event", "2031-05-10")
    )
    assert r.status_code == 201, r.text
    event = data(r)
    created["site_events"].append(event["id"])
    assert event["date"] == "2031-05-10" and event["is_active"] is True
    assert event["photo"] is None

    hidden = data(
        client.post(
            "/api/v1/marketing/events",
            headers=headers,
            data=event_form("TEST Hidden", "2031-05-10", is_active=False),
        )
    )
    created["site_events"].append(hidden["id"])

    public = data(client.get("/api/v1/events?date_from=2031-05-10&date_to=2031-05-10"))["items"]
    ids = [e["id"] for e in public]
    assert event["id"] in ids and hidden["id"] not in ids
    assert "is_active" not in public[0]
    assert client.get(f"/api/v1/events/{hidden['id']}").status_code == 404
    assert data(client.get(f"/api/v1/events/{event['id']}"))["date"] == "2031-05-10"

    r = client.patch(
        f"/api/v1/marketing/events/{event['id']}", headers=headers, json={"date": "2031-06-01"}
    )
    assert r.status_code == 200 and data(r)["date"] == "2031-06-01"
    r = client.post(
        "/api/v1/marketing/events", headers=headers, data={"date": "2031-05-10", "title_ru": "Нет"}
    )
    assert r.status_code == 422

    assert (
        client.delete(f"/api/v1/marketing/events/{event['id']}", headers=headers).status_code == 200
    )
    r = client.get(f"/api/v1/marketing/events/{event['id']}", headers=headers)
    assert r.status_code == 404 and r.json()["code"] == "event_not_found"


def test_events_calendar_and_day_filter(client, marketing):
    headers, created = marketing

    def add(day: str, active: bool = True) -> int:
        body = event_form(f"TEST {day}", day, is_active=active)
        r = client.post("/api/v1/marketing/events", headers=headers, data=body)
        assert r.status_code == 201, r.text
        created["site_events"].append(data(r)["id"])
        return data(r)["id"]

    a = add("2031-03-05")
    b = add("2031-03-05")
    c = add("2031-03-20")
    hidden = add("2031-03-25", active=False)
    add("2031-04-02")

    # Точки календаря за март: только дни с активными событиями.
    days = data(client.get("/api/v1/events/calendar?date_from=2031-03-01&date_to=2031-03-31"))
    assert days == [{"date": "2031-03-05", "count": 2}, {"date": "2031-03-20", "count": 1}]
    # В админке видны и неактивные.
    admin_days = data(
        client.get(
            "/api/v1/marketing/events/calendar?date_from=2031-03-01&date_to=2031-03-31",
            headers=headers,
        )
    )
    assert {"date": "2031-03-25", "count": 1} in admin_days

    # Клик по дню: события этого дня.
    ids = [e["id"] for e in data(client.get("/api/v1/events?date=2031-03-05"))["items"]]
    assert sorted(ids) == sorted([a, b])
    assert c not in ids and hidden not in ids

    # Неверный диапазон.
    r = client.get("/api/v1/events/calendar?date_from=2031-03-10&date_to=2031-03-01")
    assert r.status_code == 400 and r.json()["code"] == "event_calendar_range"
    r = client.get("/api/v1/events/calendar?date_from=2031-01-01&date_to=2031-12-31")
    assert r.status_code == 400
    # По умолчанию — текущий месяц.
    assert client.get("/api/v1/events/calendar").status_code == 200


def test_event_photo(client, marketing):
    headers, created = marketing
    r = client.post(
        "/api/v1/marketing/events",
        headers=headers,
        data=event_form("TEST Photo", "2031-07-01"),
        files={"photo": ("e.png", png_bytes(), "image/png")},
    )
    assert r.status_code == 201, r.text
    event = data(r)
    created["site_events"].append(event["id"])
    eid = event["id"]
    assert event["photo"]["url"] == f"/api/v1/marketing/events/{eid}/photo"
    assert event["photo"]["name"] == "e.png"

    # Сайт: фото по публичной ссылке.
    card = data(client.get(f"/api/v1/events/{eid}"))
    assert card["photo"]["url"] == f"/api/v1/events/{eid}/photo"
    r = client.get(card["photo"]["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    listed = data(client.get("/api/v1/events?date=2031-07-01"))["items"]
    assert listed[0]["photo"]["url"] == card["photo"]["url"]

    # Замена, неверный файл, удаление.
    r = client.put(
        f"/api/v1/marketing/events/{eid}/photo",
        headers=headers,
        files={"photo": ("f.png", png_bytes(), "image/png")},
    )
    assert r.status_code == 200 and data(r)["photo"]["name"] == "f.png"
    r = client.put(
        f"/api/v1/marketing/events/{eid}/photo",
        headers=headers,
        files={"photo": ("x.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400
    assert client.get(f"/api/v1/marketing/events/{eid}/photo", headers=headers).status_code == 200
    r = client.delete(f"/api/v1/marketing/events/{eid}/photo", headers=headers)
    assert r.status_code == 200 and data(r)["photo"] is None
    r = client.get(f"/api/v1/events/{eid}/photo")
    assert r.status_code == 404 and r.json()["code"] == "event_photo_not_found"
    r = client.delete(f"/api/v1/marketing/events/{eid}/photo", headers=headers)
    assert r.status_code == 404

    # Неактивное событие: фото на сайте не отдаётся.
    client.put(
        f"/api/v1/marketing/events/{eid}/photo",
        headers=headers,
        files={"photo": ("g.png", png_bytes(), "image/png")},
    )
    client.patch(f"/api/v1/marketing/events/{eid}", headers=headers, json={"is_active": False})
    assert client.get(f"/api/v1/events/{eid}/photo").status_code == 404
    assert client.get(f"/api/v1/marketing/events/{eid}/photo", headers=headers).status_code == 200

    # Удаление события удаляет и каталог с фото.
    assert client.delete(f"/api/v1/marketing/events/{eid}", headers=headers).status_code == 200
    assert not (Path(settings.MEDIA_PATH) / "site" / "events" / str(eid)).exists()


def test_about_crud(client, marketing):
    headers, created = marketing
    r = client.post(
        "/api/v1/marketing/about",
        headers=headers,
        json={"translations": title_text("TEST About"), "sort_order": 900001},
    )
    assert r.status_code == 201, r.text
    section = data(r)
    created["site_about_sections"].append(section["id"])
    assert section["id"] in [s["id"] for s in data(client.get("/api/v1/about"))]

    r = client.patch(
        f"/api/v1/marketing/about/{section['id']}", headers=headers, json={"is_active": False}
    )
    assert r.status_code == 200
    assert section["id"] not in [s["id"] for s in data(client.get("/api/v1/about"))]
    assert section["id"] in [
        s["id"] for s in data(client.get("/api/v1/marketing/about", headers=headers))
    ]
    assert (
        client.delete(f"/api/v1/marketing/about/{section['id']}", headers=headers).status_code
        == 200
    )


@pytest.mark.parametrize(
    "marketing_path, public_path, other_path",
    [
        (
            "/api/v1/marketing/council-members",
            "/api/v1/council-members",
            "/api/v1/marketing/leadership",
        ),
        ("/api/v1/marketing/leadership", "/api/v1/leadership", "/api/v1/marketing/council-members"),
    ],
)
def test_people_crud(client, marketing, marketing_path, public_path, other_path):
    headers, created = marketing
    existing = len(data(client.get(marketing_path, headers=headers)))

    def add(name, files=None, **extra):
        r = client.post(
            marketing_path, headers=headers, data=person_form(name, **extra), files=files
        )
        assert r.status_code == 201, r.text
        created["site_people"].append(data(r)["id"])
        return data(r)

    first = add(
        "TEST A",
        files={"photo": ("a.png", png_bytes(), "image/png")},
        phone_number="+998901234567",
        email="a@example.com",
    )
    second = add("TEST B")
    assert first["queue_number"] == existing + 1 and second["queue_number"] == existing + 2
    assert first["photo"]["url"] == f"{marketing_path}/{first['id']}/photo"
    assert second["photo"] is None and second["phone_number"] is None
    assert first["email"] == "a@example.com"

    # Новая карточка на первое место: остальные сдвигаются.
    top = add("TEST Top", queue_number=1)
    order = [p["id"] for p in data(client.get(marketing_path, headers=headers))]
    assert order[0] == top["id"]
    assert order.index(first["id"]) == existing + 1 and order.index(second["id"]) == existing + 2
    numbers = [p["queue_number"] for p in data(client.get(marketing_path, headers=headers))]
    assert numbers == list(range(1, len(numbers) + 1))

    # Перестановка и сайт.
    r = client.patch(f"{marketing_path}/{top['id']}", headers=headers, json={"queue_number": 999})
    assert r.status_code == 200 and data(r)["queue_number"] == existing + 3
    public = data(client.get(public_path))
    card = next(p for p in public if p["id"] == first["id"])
    assert card["photo"]["url"] == f"{public_path}/{first['id']}/photo"
    assert "is_active" not in card
    r = client.get(card["photo"]["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"

    # Разделы не пересекаются.
    assert client.get(f"{other_path}/{first['id']}", headers=headers).status_code == 404

    # Контакты: неверный телефон — 422, null очищает.
    r = client.patch(
        f"{marketing_path}/{first['id']}", headers=headers, json={"phone_number": "123"}
    )
    assert r.status_code == 422
    r = client.patch(
        f"{marketing_path}/{first['id']}",
        headers=headers,
        json={"phone_number": None, "email": None},
    )
    assert data(r)["phone_number"] is None and data(r)["email"] is None

    # Фото: замена и удаление; скрытая карточка не видна на сайте.
    r = client.put(
        f"{marketing_path}/{second['id']}/photo",
        headers=headers,
        files={"photo": ("b.png", png_bytes(), "image/png")},
    )
    assert r.status_code == 200 and data(r)["photo"]["name"] == "b.png"
    r = client.delete(f"{marketing_path}/{second['id']}/photo", headers=headers)
    assert data(r)["photo"] is None
    client.patch(f"{marketing_path}/{second['id']}", headers=headers, json={"is_active": False})
    assert client.get(f"{public_path}/{second['id']}").status_code == 404

    # Удаление: номера без пропусков.
    assert client.delete(f"{marketing_path}/{top['id']}", headers=headers).status_code == 200
    numbers = [p["queue_number"] for p in data(client.get(marketing_path, headers=headers))]
    assert numbers == list(range(1, len(numbers) + 1))


def test_website_management_requires_permission(api, client, role_ids):
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    for path in (
        "/api/v1/marketing/events",
        "/api/v1/marketing/about",
        "/api/v1/marketing/council-members",
        "/api/v1/marketing/leadership",
    ):
        assert client.get(path, headers=fund).status_code == 403
        assert client.get(path).status_code == 401
    for path in (
        "/api/v1/events",
        "/api/v1/about",
        "/api/v1/council-members",
        "/api/v1/leadership",
    ):
        assert client.get(path).status_code == 200

    # Права раздельные: доступ к членам Совета не даёт доступа к руководству.
    only_council, _ = api.staff(
        role_id=role_ids["MARKETING"], permissions=["council_profiles.read"]
    )
    assert client.get("/api/v1/marketing/council-members", headers=only_council).status_code == 200
    assert client.get("/api/v1/marketing/leadership", headers=only_council).status_code == 403


def test_contacts_crud(client, marketing):
    headers, created = marketing
    base = "/api/v1/marketing/contacts"

    r = client.post(
        base,
        headers=headers,
        json={"phone": "+998712000000", "email": "Info@Example.COM", "sort_order": 900001},
    )
    assert r.status_code == 201, r.text
    first = data(r)
    created["site_contacts"].append(first["id"])
    assert first["email"] == "info@example.com" and first["is_active"] is True

    # Можно несколько; телефон или email может отсутствовать
    r = client.post(
        base, headers=headers, json={"email": "press@example.com", "sort_order": 900002}
    )
    assert r.status_code == 201, r.text
    second = data(r)
    created["site_contacts"].append(second["id"])
    assert second["phone"] is None

    # Пустой контакт и неверный формат — 422
    for body in ({}, {"phone": "12345"}, {"email": "not-an-email"}):
        assert client.post(base, headers=headers, json=body).status_code == 422, body

    # Сайт: без токена, только активные, по порядку
    public = data(client.get("/api/v1/contacts"))
    ids = [c["id"] for c in public]
    assert ids.index(first["id"]) < ids.index(second["id"])
    assert set(public[0]) == {"id", "phone", "email", "sort_order"}

    # Изменение: убрать email можно, но не оба значения сразу
    r = client.patch(f"{base}/{first['id']}", headers=headers, json={"email": None})
    assert r.status_code == 200 and data(r)["email"] is None and data(r)["phone"]
    r = client.patch(f"{base}/{first['id']}", headers=headers, json={"phone": None})
    assert r.status_code == 400 and r.json()["code"] == "site_contact_empty", r.text

    r = client.patch(f"{base}/{second['id']}", headers=headers, json={"is_active": False})
    assert r.status_code == 200
    assert second["id"] not in [c["id"] for c in data(client.get("/api/v1/contacts"))]
    assert second["id"] in [c["id"] for c in data(client.get(base, headers=headers))]

    assert client.delete(f"{base}/{second['id']}", headers=headers).status_code == 200
    assert client.get(f"{base}/{second['id']}", headers=headers).status_code == 404
    assert client.get(base).status_code == 401


def test_testimonials_crud(client, marketing):
    headers, created = marketing
    base = "/api/v1/marketing/testimonials"
    png = ("photo.png", png_bytes(), "image/png")

    r = client.post(
        base,
        headers=headers,
        data=person_form("TEST Отзыв", sort_order="900001"),
        files={"photo": png},
    )
    assert r.status_code == 201, r.text
    first = data(r)
    created["site_testimonials"].append(first["id"])
    assert [t["language"] for t in first["translations"]] == ["ru", "uz", "en"]
    assert first["photo"]["url"] == f"{base}/{first['id']}/photo"
    folder = Path(settings.MEDIA_PATH) / "site" / "testimonials" / str(first["id"])
    assert folder.exists()

    # Без фото — можно; без перевода — 422
    r = client.post(base, headers=headers, data=person_form("TEST Без фото", sort_order="900002"))
    assert r.status_code == 201, r.text
    second = data(r)
    created["site_testimonials"].append(second["id"])
    assert second["photo"] is None
    body = person_form("TEST Неполный")
    body.pop("description_en")
    assert client.post(base, headers=headers, data=body).status_code == 422

    # Сайт: без токена, только активные, по порядку, фото — по публичному адресу
    public = data(client.get("/api/v1/testimonials"))
    ids = [t["id"] for t in public]
    assert ids.index(first["id"]) < ids.index(second["id"])
    item = next(t for t in public if t["id"] == first["id"])
    assert "is_active" not in item and item["photo"]["url"].startswith("/api/v1/testimonials/")
    assert client.get(item["photo"]["url"]).status_code == 200

    # Изменение: переводы, скрытие
    r = client.patch(
        f"{base}/{first['id']}",
        headers=headers,
        json={
            "translations": [
                {"language": lang, "full_name": f"TEST Новое {lang}", "description": "Спасибо!"}
                for lang in ("en", "ru", "uz")
            ],
            "is_active": False,
        },
    )
    assert r.status_code == 200, r.text
    assert data(r)["translations"][0]["full_name"] == "TEST Новое ru"
    assert first["id"] not in [t["id"] for t in data(client.get("/api/v1/testimonials"))]
    assert client.get(f"/api/v1/testimonials/{first['id']}").status_code == 404
    assert client.get(f"/api/v1/testimonials/{first['id']}/photo").status_code == 404
    assert client.get(f"{base}/{first['id']}/photo", headers=headers).status_code == 200

    # Фото: загрузить второму, удалить у первого
    r = client.put(f"{base}/{second['id']}/photo", headers=headers, files={"photo": png})
    assert r.status_code == 200 and data(r)["photo"], r.text
    r = client.delete(f"{base}/{first['id']}/photo", headers=headers)
    assert r.status_code == 200 and data(r)["photo"] is None
    r = client.delete(f"{base}/{first['id']}/photo", headers=headers)
    assert r.status_code == 404 and r.json()["code"] == "testimonial_photo_not_found"

    # Удаление убирает и каталог с фото
    assert client.delete(f"{base}/{second['id']}", headers=headers).status_code == 200
    assert client.get(f"{base}/{second['id']}", headers=headers).status_code == 404
    assert not (Path(settings.MEDIA_PATH) / "site" / "testimonials" / str(second["id"])).exists()
    assert client.get(base).status_code == 401
