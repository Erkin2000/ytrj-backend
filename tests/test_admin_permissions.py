"""Админ-панель по permissions: признак сотрудника и направление в /auth/me, отдельное
окно Фонда (fund_review.*), у Фонда нет users/roles/council_review.read, роли и выдаваемые
права доступны форме пользователя (users.create / users.update)."""

import uuid

from sqlalchemy import text

from tests.conftest import data, db_run

ME = "/api/v1/auth/me"


def me(api, headers):
    return data(api.client.get(ME, headers=headers))


def test_auth_me_staff_and_direction(api, role_ids, applicant):
    profile = me(api, applicant)
    assert profile["is_staff"] is False and profile["direction"] is None

    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    profile = me(api, fund)
    assert profile["is_staff"] is True
    assert profile["direction"] == "FUND" and profile["is_direction_admin"] is False

    admin, _ = api.staff(role_id=role_ids["FUND_OPERATOR"], is_direction_admin=True)
    profile = me(api, admin)
    assert profile["is_direction_admin"] is True and profile["direction"] == "FUND"

    marketing, _ = api.staff(role_id=role_ids["MARKETING"])
    profile = me(api, marketing)
    assert profile["is_staff"] is True and profile["direction"] is None

    root = me(api, api.superadmin)
    assert root["is_staff"] is True and root["is_superuser"] is True
    assert "fund_review.read" in root["permissions"]  # у Super Admin — весь каталог


def test_fund_workspace_has_own_permission(api, role_ids, banks):
    c = api.client
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    bank_h, _ = api.staff(role_id=role_ids["BANK_EMPLOYEE"], bank_id=banks[0]["id"])
    council_h, _ = api.staff(eimzo=True, role_id=role_ids["COUNCIL_MEMBER"])

    perms = set(me(api, fund)["permissions"])
    assert {"fund_review.read", "fund_review.approve"} <= perms
    assert not perms & {"users.read", "roles.read", "council_review.read"}
    for headers in (bank_h, council_h):
        assert "fund_review.read" not in me(api, headers)["permissions"]

    assert c.get("/api/v1/fund/applications", headers=fund).status_code == 200
    assert c.get("/api/v1/fund/applications/counters", headers=fund).status_code == 200
    for headers in (bank_h, council_h):
        r = c.get("/api/v1/fund/applications", headers=headers)
        assert r.status_code == 403 and r.json()["code"] == "permission_denied"

    # Рядовому сотруднику Фонда не открываются «Пользователи», «Роли» и окно Совета.
    assert c.get("/api/v1/users", headers=fund).status_code == 403
    assert c.get("/api/v1/roles", headers=fund).status_code == 403
    assert c.get("/api/v1/council/bulletins", headers=fund).status_code == 403


def test_user_form_endpoints_with_users_update(api, role_ids, client, superadmin):
    """Роль с users.update (без users.create и roles.read): форма редактирования получает
    роли и выдаваемые права."""
    code = f"TEST_UPD_{uuid.uuid4().hex[:6].upper()}"
    r = client.post(
        "/api/v1/roles",
        headers=superadmin,
        json={
            "code": code,
            "translations": [
                {"language": lang, "name": f"TEST {code} {lang}"} for lang in ("ru", "uz", "en")
            ],
            "permissions": ["users.update", "fund_review.read"],
        },
    )
    assert r.status_code == 201, r.text
    role_id = data(r)["id"]
    try:
        editor, _ = api.staff(role_id=role_id)
        nobody, _ = api.staff(role_id=role_ids["MARKETING"])

        options = client.get("/api/v1/roles/options", headers=editor)
        assert options.status_code == 200
        codes = [o["code"] for o in data(options)]
        assert "FUND_OPERATOR" in codes and "APPLICANT" not in codes
        assert [t["language"] for t in data(options)[0]["translations"]] == ["ru", "uz", "en"]
        assert client.get("/api/v1/roles", headers=editor).status_code == 200

        r = client.get(
            f"/api/v1/users/grantable-permissions?role_id={role_ids['FUND_OPERATOR']}",
            headers=editor,
        )
        assert r.status_code == 200, r.text
        # Выдать можно только свои права в пределах роли: права Фонда ∩ права редактора.
        assert [p["code"] for p in data(r)["permissions"]] == ["fund_review.read"]

        assert client.get("/api/v1/roles/options", headers=nobody).status_code == 403
        r = client.get("/api/v1/users/grantable-permissions", headers=nobody)
        assert r.status_code == 403
    finally:

        async def run(session):
            await session.execute(text("DELETE FROM users WHERE role_id = :r"), {"r": role_id})
            await session.execute(text("DELETE FROM roles WHERE id = :r"), {"r": role_id})

        db_run(run)
