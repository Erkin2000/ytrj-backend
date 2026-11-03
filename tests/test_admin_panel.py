import pytest
from sqlalchemy import select

from src.account.models.user_model import UserORM
from src.rbac.models.role_model import RoleORM
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, db_all


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
