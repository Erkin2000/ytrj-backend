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
    created = {"site_events": [], "site_about_sections": [], "site_people": []}
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


def test_events_crud(client, marketing):
    headers, created = marketing
    body = {"translations": title_text("TEST Event"), "date": "2031-05-10"}
    r = client.post("/api/v1/marketing/events", headers=headers, json=body)
    assert r.status_code == 201, r.text
    event = data(r)
    created["site_events"].append(event["id"])
    assert event["date"] == "2031-05-10" and event["is_active"] is True

    hidden = data(
        client.post(
            "/api/v1/marketing/events",
            headers=headers,
            json={**body, "translations": title_text("TEST Hidden"), "is_active": False},
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
    r = client.post("/api/v1/marketing/events", headers=headers, json={**body, "translations": []})
    assert r.status_code == 422

    assert (
        client.delete(f"/api/v1/marketing/events/{event['id']}", headers=headers).status_code == 200
    )
    r = client.get(f"/api/v1/marketing/events/{event['id']}", headers=headers)
    assert r.status_code == 404 and r.json()["code"] == "event_not_found"


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
