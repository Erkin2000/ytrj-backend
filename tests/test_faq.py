from sqlalchemy import text

from tests.conftest import data, db_run


def faq_body(question: str = "TEST Savol", active: bool = True, order: int = 0) -> dict:
    return {
        "translations": [
            {"language": "uz", "question": f"{question} uz", "answer": "Javob"},
            {"language": "ru", "question": f"{question} ru", "answer": "Ответ"},
            {"language": "en", "question": f"{question} en", "answer": "Answer"},
        ],
        "is_active": active,
        "sort_order": order,
    }


def drop_faqs(ids: list[int]) -> None:
    async def run(session):
        await session.execute(text("DELETE FROM faqs WHERE id = ANY(:ids)"), {"ids": ids})

    if ids:
        db_run(run)


def test_marketing_signs_in_via_one_id_and_manages_faq(api, client, role_ids):
    assert "MARKETING" in role_ids
    headers, me = api.staff(role_id=role_ids["MARKETING"], full_name="TEST Marketing")
    assert me["role"]["code"] == "MARKETING"
    profile = data(client.get("/api/v1/auth/me", headers=headers))
    assert {"faq.create", "faq.read", "faq.update", "faq.delete"} <= set(profile["permissions"])

    created: list[int] = []
    try:
        r = client.post("/api/v1/marketing/faq", headers=headers, json=faq_body(order=900001))
        assert r.status_code == 201, r.text
        faq = data(r)
        created.append(faq["id"])
        assert [t["language"] for t in faq["translations"]] == ["ru", "uz", "en"]
        assert faq["created_by"]["id"] == me["id"] and faq["is_active"] is True

        hidden = data(
            client.post(
                "/api/v1/marketing/faq", headers=headers, json=faq_body("TEST Hidden", False)
            )
        )
        created.append(hidden["id"])

        # Сайт: без токена, только активные, по порядку.
        public = data(client.get("/api/v1/faq"))
        public_ids = [f["id"] for f in public]
        assert faq["id"] in public_ids and hidden["id"] not in public_ids
        assert "is_active" not in public[0] and "created_by" not in public[0]

        # Маркетинг видит все.
        all_ids = [f["id"] for f in data(client.get("/api/v1/marketing/faq", headers=headers))]
        assert {faq["id"], hidden["id"]} <= set(all_ids)

        r = client.patch(
            f"/api/v1/marketing/faq/{hidden['id']}",
            headers=headers,
            json={"is_active": True, "translations": faq_body("TEST Shown")["translations"]},
        )
        assert r.status_code == 200, r.text
        shown = data(r)
        assert shown["is_active"] is True
        assert {t["language"]: t["question"] for t in shown["translations"]}[
            "ru"
        ] == "TEST Shown ru"
        assert hidden["id"] in [f["id"] for f in data(client.get("/api/v1/faq"))]

        # Перевод на все три языка обязателен; лишние поля запрещены.
        partial = faq_body()
        partial["translations"] = partial["translations"][:2]
        assert (
            client.post("/api/v1/marketing/faq", headers=headers, json=partial).status_code == 422
        )
        assert (
            client.patch(
                f"/api/v1/marketing/faq/{faq['id']}", headers=headers, json={"foo": 1}
            ).status_code
            == 422
        )

        assert (
            client.delete(f"/api/v1/marketing/faq/{faq['id']}", headers=headers).status_code == 200
        )
        created.remove(faq["id"])
        r = client.get(f"/api/v1/marketing/faq/{faq['id']}", headers=headers)
        assert r.status_code == 404 and r.json()["code"] == "faq_not_found"
    finally:
        drop_faqs(created)


def test_faq_management_requires_permission(api, client, role_ids):
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    assert client.get("/api/v1/marketing/faq", headers=fund).status_code == 403
    assert client.post("/api/v1/marketing/faq", headers=fund, json=faq_body()).status_code == 403
    assert client.get("/api/v1/marketing/faq").status_code == 401

    # Права выдаются поштучно: маркетолог только с правом просмотра не создаёт вопросы.
    viewer, _ = api.staff(role_id=role_ids["MARKETING"], permissions=["faq.read"])
    assert client.get("/api/v1/marketing/faq", headers=viewer).status_code == 200
    assert client.post("/api/v1/marketing/faq", headers=viewer, json=faq_body()).status_code == 403
