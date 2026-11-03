import pytest
from sqlalchemy import select

from src.account.models.user_model import UserORM
from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_model import RoleORM
from src.rbac.models.role_permission_model import RolePermissionORM
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, data, db_all


@pytest.fixture
def admin_client(client, superadmin):
    r = client.post(
        "/admin/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    return client


@pytest.fixture
def role_pk():
    return dict(db_all(select(RoleORM.code, RoleORM.id)))


@pytest.mark.parametrize(
    "path",
    [
        "/admin/",
        "/admin/user-orm/list",
        "/admin/user-orm/create",
        "/admin/role-orm/list",
        "/admin/application-orm/list",
        "/admin/refresh-token-orm/list",
    ],
)
def test_pages_render(admin_client, path):
    assert admin_client.get(path).status_code == 200


def test_user_form_has_direction_fields(admin_client):
    page = admin_client.get("/admin/user-orm/create").text
    assert 'name="is_direction_admin"' in page
    assert 'name="permissions"' in page


def test_user_form_validation_and_save(api, admin_client, role_pk):
    def post(**fields):
        username = api.username()
        r = admin_client.post(
            "/admin/user-orm/create",
            data={"username": username, "status": "ACTIVE", **fields},
            follow_redirects=False,
        )
        return r, username

    pinfl = api.fresh_pinfl()
    fund = str(role_pk["FUND_OPERATOR"])

    r, _ = post(pinfl="123", role=fund)
    assert r.status_code == 400

    r, _ = post(pinfl=pinfl, role=str(role_pk["SUPER_ADMIN"]), is_direction_admin="y")
    assert r.status_code == 400

    r, username = post(pinfl=pinfl, role=fund, is_direction_admin="y")
    assert r.status_code in (302, 303)
    rows = db_all(
        select(UserORM.id, UserORM.is_direction_admin, UserORM.pinfl).where(
            UserORM.username == username
        )
    )
    assert rows, "пользователь не сохранён"
    api.remember_user(rows[0][0])
    assert rows[0][1:] == (True, pinfl)

    assert admin_client.get(f"/admin/user-orm/details/{rows[0][0]}").status_code == 200
    assert admin_client.get(f"/admin/user-orm/edit/{rows[0][0]}").status_code == 200

    r, _ = post(pinfl=pinfl, role=fund)
    assert r.status_code == 400  # ПИНФЛ занят


def _role_codes(role_id):
    return sorted(
        code
        for (code,) in db_all(
            select(PermissionORM.code)
            .join(RolePermissionORM, RolePermissionORM.permission_id == PermissionORM.id)
            .where(RolePermissionORM.role_id == role_id)
        )
    )


def _personal_codes(api, headers):
    return sorted(data(api.client.get("/api/v1/auth/me", headers=headers))["permissions"])


def test_applicant_promoted_in_admin_gets_role_permissions(api, admin_client, role_pk):
    login, me = api.sso_login(full_name="TEST Applicant")
    assert me["role"]["code"] == "APPLICANT"

    r = admin_client.post(
        f"/admin/user-orm/edit/{me['id']}",
        data={
            "username": me["username"],
            "status": "ACTIVE",
            "role": str(role_pk["FUND_OPERATOR"]),
            "pinfl": me["pinfl"],
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), r.text[:300]

    fund_codes = _role_codes(role_pk["FUND_OPERATOR"])
    assert _personal_codes(api, login["headers"]) == fund_codes
    assert api.client.get("/api/v1/fund/applications", headers=login["headers"]).status_code == 200


def test_admin_create_without_permissions_gets_role_permissions(api, admin_client, role_pk):
    pinfl = api.fresh_pinfl()
    r = admin_client.post(
        "/admin/user-orm/create",
        data={
            "username": api.username(),
            "status": "ACTIVE",
            "role": str(role_pk["FUND_OPERATOR"]),
            "pinfl": pinfl,
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), r.text[:300]
    login, _ = api.sso_login(pinfl)
    assert _personal_codes(api, login["headers"]) == _role_codes(role_pk["FUND_OPERATOR"])


def test_admin_keeps_manually_selected_permissions(api, admin_client, role_pk):
    read_id = db_all(select(PermissionORM.id).where(PermissionORM.code == "applications.read"))[0][
        0
    ]
    pinfl = api.fresh_pinfl()
    r = admin_client.post(
        "/admin/user-orm/create",
        data={
            "username": api.username(),
            "status": "ACTIVE",
            "role": str(role_pk["FUND_OPERATOR"]),
            "pinfl": pinfl,
            "permissions": str(read_id),
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), r.text[:300]
    login, _ = api.sso_login(pinfl)
    assert _personal_codes(api, login["headers"]) == ["applications.read"]
