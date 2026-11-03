import pytest

from tests.conftest import data


@pytest.fixture
def fund_admin(api, role_ids):
    headers, me = api.staff(role_id=role_ids["FUND_OPERATOR"], is_direction_admin=True)
    detail = data(api.client.get(f"/api/v1/users/{me['id']}", headers=api.superadmin))
    return headers, me, sorted(detail["permissions"])


def test_direction_admin_requires_direction_role(api, role_ids):
    r = api.create_user(role_id=role_ids["SUPER_ADMIN"], is_direction_admin=True)
    assert r.status_code == 400
    assert r.json()["code"] == "direction_admin_role"


def test_default_permissions_are_full_role_ceiling(fund_admin):
    _, me, permissions = fund_admin
    assert me["is_direction_admin"] is True
    assert "applications.read" in permissions
    assert "users.create" not in permissions


def test_grantable_permissions_are_own_permissions(api, fund_admin):
    headers, _, permissions = fund_admin
    g = data(api.client.get("/api/v1/users/grantable-permissions", headers=headers))
    assert g["role_code"] == "FUND_OPERATOR"
    assert g["permissions"] == permissions


def test_creates_staff_in_own_direction_with_chosen_permissions(api, fund_admin):
    headers, _, _ = fund_admin
    pinfl = api.fresh_pinfl()
    r = api.create_user(headers, pinfl=pinfl, permissions=["applications.read"])
    assert r.status_code == 201, r.text
    staff = data(r)
    assert staff["role"]["code"] == "FUND_OPERATOR"
    assert staff["permissions"] == ["applications.read"]

    login, me = api.sso_login(pinfl)
    assert me["permissions"] == ["applications.read"]
    users = api.client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {login['access_token']}"}
    )
    assert users.status_code == 403


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"permissions": ["users.create"]}, "permissions_not_grantable"),
        ({"is_direction_admin": True}, "admin_management"),
    ],
)
def test_cannot_exceed_own_rights(api, fund_admin, body, code):
    headers, _, _ = fund_admin
    r = api.create_user(headers, **body)
    assert r.status_code == 403
    assert r.json()["code"] == code


def test_cannot_create_in_other_direction(api, fund_admin, role_ids):
    headers, _, _ = fund_admin
    r = api.create_user(headers, role_id=role_ids["COUNCIL_MEMBER"])
    assert r.status_code == 403
    assert r.json()["code"] == "user_out_of_scope"


def test_manages_own_staff_but_not_role_self_or_others(api, fund_admin, role_ids):
    headers, me, _ = fund_admin
    staff_id = data(api.create_user(headers, permissions=["applications.read"]))["id"]

    r = api.client.patch(
        f"/api/v1/users/{staff_id}",
        headers=headers,
        json={"permissions": ["applications.read", "scoring.read"]},
    )
    assert r.status_code == 200
    assert data(r)["permissions"] == ["applications.read", "scoring.read"]

    r = api.client.patch(
        f"/api/v1/users/{staff_id}", headers=headers, json={"role_id": role_ids["COUNCIL_MEMBER"]}
    )
    assert r.status_code == 403

    r = api.client.patch(f"/api/v1/users/{me['id']}", headers=headers, json={"full_name": "x"})
    assert r.status_code == 403

    council_id = data(api.create_user(role_id=role_ids["COUNCIL_MEMBER"]))["id"]
    r = api.client.post(
        f"/api/v1/users/{council_id}/status", headers=headers, json={"status": "BLOCKED"}
    )
    assert r.status_code == 403
    assert r.json()["code"] == "user_out_of_scope"

    r = api.client.post(
        f"/api/v1/users/{staff_id}/status", headers=headers, json={"status": "BLOCKED"}
    )
    assert r.status_code == 200
    assert data(r)["status"] == "BLOCKED"


def test_bank_admin_limited_to_own_bank(api, role_ids, banks):
    bank_a, bank_b = banks[0]["id"], banks[1]["id"]
    headers, _ = api.staff(
        role_id=role_ids["BANK_EMPLOYEE"], bank_id=bank_a, is_direction_admin=True
    )

    r = api.create_user(headers, permissions=["bank_review.read"])
    assert r.status_code == 201, r.text
    assert data(r)["bank"]["id"] == bank_a

    assert api.create_user(headers, bank_id=bank_b).status_code == 403

    items = data(api.client.get("/api/v1/users?per_page=100", headers=headers))["items"]
    assert items
    assert all(u["role"]["code"] == "BANK_EMPLOYEE" and u["bank"]["id"] == bank_a for u in items)

    other_bank_staff = data(api.create_user(role_id=role_ids["BANK_EMPLOYEE"], bank_id=bank_b))
    assert (
        api.client.get(f"/api/v1/users/{other_bank_staff['id']}", headers=headers).status_code
        == 404
    )


def test_flag_removal_revokes_user_management(api, fund_admin):
    headers, me, _ = fund_admin
    api.client.patch(
        f"/api/v1/users/{me['id']}",
        headers=api.superadmin,
        json={"is_direction_admin": False, "permissions": ["applications.read"]},
    )
    r = api.create_user(headers)
    assert r.status_code == 403
