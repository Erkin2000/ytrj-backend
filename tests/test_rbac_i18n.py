"""RBAC на трёх языках: переводы прав, модулей и ролей; создание роли с переводами."""

from sqlalchemy import text

from src.rbac.i18n import missing_translations
from tests.conftest import data, db_run

LANGS = ["ru", "uz", "en"]


def tr(name: str, description: str | None = None) -> list[dict]:
    return [
        {"language": lang, "name": f"{name} {lang}", "description": description} for lang in LANGS
    ]


def test_rbac_catalog_translated():
    assert missing_translations() == []


def test_permissions_and_matrix_have_three_languages(client, superadmin):
    items = data(client.get("/api/v1/permissions", headers=superadmin))
    assert items
    for item in items:
        assert [t["language"] for t in item["translations"]] == LANGS, item["code"]
        assert all(t["name"] for t in item["translations"])
    users_read = next(i for i in items if i["code"] == "users.read")
    assert users_read["translations"][2]["name"] == "View users"

    matrix = data(client.get("/api/v1/permissions/matrix", headers=superadmin))
    apps = next(g for g in matrix if g["module"] == "applications")
    assert [t["name"] for t in apps["translations"]] == ["Заявки", "Arizalar", "Applications"]


def test_roles_have_translations(client, superadmin):
    roles = data(client.get("/api/v1/roles?per_page=100", headers=superadmin))["items"]
    fund = next(r for r in roles if r["code"] == "FUND_OPERATOR")
    assert [t["language"] for t in fund["translations"]] == LANGS
    assert fund["translations"][1]["name"] == "Jamgʻarma operatori"
    assert "name" not in fund

    me = data(client.get("/api/v1/auth/me", headers=superadmin))
    assert [t["language"] for t in me["role"]["translations"]] == LANGS


def test_custom_role_crud_with_translations(client, superadmin):
    created: list[int] = []
    try:
        r = client.post(
            "/api/v1/roles",
            headers=superadmin,
            json={
                "code": "TEST_I18N_ROLE",
                "translations": tr("TEST Роль", "Описание"),
                "permissions": ["applications.read"],
            },
        )
        assert r.status_code == 201, r.text
        role = data(r)
        created.append(role["id"])
        assert [t["name"] for t in role["translations"]] == [f"TEST Роль {x}" for x in LANGS]

        # Не хватает языка — 422; описание не на всех языках — 422
        bad = tr("TEST Другая")[:2]
        body = {"code": "TEST_I18N_ROLE_2", "translations": bad}
        assert client.post("/api/v1/roles", headers=superadmin, json=body).status_code == 422
        partial = tr("TEST Другая")
        partial[0]["description"] = "только ru"
        body = {"code": "TEST_I18N_ROLE_2", "translations": partial}
        assert client.post("/api/v1/roles", headers=superadmin, json=body).status_code == 422

        # Такое же русское название — 409
        body = {"code": "TEST_I18N_ROLE_2", "translations": tr("TEST Роль", "Описание")}
        r = client.post("/api/v1/roles", headers=superadmin, json=body)
        assert r.status_code == 409 and r.json()["code"] == "role_name_already_exists"

        r = client.patch(
            f"/api/v1/roles/{role['id']}",
            headers=superadmin,
            json={"translations": tr("TEST Новая")},
        )
        assert r.status_code == 200, r.text
        updated = data(r)
        assert updated["translations"][0] == {
            "language": "ru",
            "name": "TEST Новая ru",
            "description": None,
        }
        assert updated["permissions"] == ["applications.read"]

        assert client.delete(f"/api/v1/roles/{role['id']}", headers=superadmin).status_code == 200
        created.clear()
    finally:
        if created:

            async def run(session):
                await session.execute(
                    text("DELETE FROM roles WHERE id = ANY(:ids)"), {"ids": created}
                )

            db_run(run)
