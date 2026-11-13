import pytest
from sqlalchemy import select

from src.account.models.user_model import UserORM
from src.product.models.product_model import ProductTranslationORM
from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_model import RoleORM
from src.rbac.models.role_permission_model import RolePermissionORM
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, data, db_all, tr


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


@pytest.fixture
def product_application(api, role_ids, banks, applicant, photo_upload):
    bank = next(
        (
            b
            for b in banks
            if b.get("is_active", True)
            and "SELF_EMPLOYED" in (b.get("allowed_subject_types") or [])
        ),
        None,
    )
    if bank is None:
        pytest.skip("Нет активного банка для SELF_EMPLOYED")
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    product = api.product(fund, [bank["id"]])
    r = api.client.post(
        "/api/v1/applications",
        headers=applicant,
        json={"product_id": product["id"], "subject_type": "SELF_EMPLOYED"},
    )
    assert r.status_code == 201, r.text
    app_id = data(r)["id"]
    api.application_ids.append(app_id)
    stage = product["stages"][0]
    number, photo, _ = stage["fields"]
    api.client.put(
        f"/api/v1/applications/{app_id}/stages/{stage['id']}",
        headers=applicant,
        json={"values": {str(number["id"]): "777"}},
    )
    r = api.client.post(
        f"/api/v1/applications/{app_id}/fields/{photo['id']}/files",
        headers=applicant,
        files=photo_upload(),
    )
    assert r.status_code == 201, r.text
    return product, app_id, data(r)["id"]


def test_admin_product_pages(admin_client, product_application):
    product, app_id, file_id = product_application
    for path in (
        "/admin/product-orm/list",
        "/admin/product-translation-orm/list",
        "/admin/product-category-orm/list",
        f"/admin/product-category-orm/details/{product['category']['id']}",
        f"/admin/product-orm/edit/{product['id']}",
    ):
        assert admin_client.get(path).status_code == 200, path

    page = admin_client.get(f"/admin/product-orm/details/{product['id']}").text
    assert "TEST Mahsulot" in page and "TEST Product" in page
    assert "Комментарий" in page

    page = admin_client.get(f"/admin/application-orm/details/{app_id}").text
    assert f"/application-field-file/{file_id}" in page
    assert "777" in page

    r = admin_client.get(f"/admin/application-field-file/{file_id}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert admin_client.get("/admin/application-field-file/999999999").status_code == 404


def test_admin_conditional_product_pages(api, admin_client, role_ids, banks, applicant):
    bank = next(
        (
            b
            for b in banks
            if b.get("is_active", True)
            and "SELF_EMPLOYED" in (b.get("allowed_subject_types") or [])
        ),
        None,
    )
    if bank is None:
        pytest.skip("Нет активного банка для SELF_EMPLOYED")
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    product = api.conditional_product(fund, [bank["id"]])
    stage1 = next(s for s in product["stages"] if s["number"] == 1)
    colour = next(f for f in stage1["fields"] if f["field_type"] == "SELECT")
    blue = next(o["id"] for o in colour["options"] if o["sort_order"] == 1)

    page = admin_client.get(f"/admin/product-orm/details/{product['id']}").text
    assert "Красный" in page and "Показывать, если" in page

    r = api.client.post(
        "/api/v1/applications",
        headers=applicant,
        json={"product_id": product["id"], "subject_type": "SELF_EMPLOYED"},
    )
    assert r.status_code == 201, r.text
    app_id = data(r)["id"]
    api.application_ids.append(app_id)
    r = api.client.put(
        f"/api/v1/applications/{app_id}/stages/{stage1['id']}",
        headers=applicant,
        json={"values": {str(colour["id"]): str(blue)}},
    )
    assert r.status_code == 200, r.text
    page = admin_client.get(f"/admin/application-orm/details/{app_id}").text
    assert "Синий" in page and "Фрукт" not in page and "Оттенок" in page


def test_admin_product_edit_validation(api, admin_client, product_application):
    product, _, _ = product_application
    url = f"/admin/product-orm/edit/{product['id']}"
    bank_ids = [str(b["id"]) for b in product["banks"]]
    category = str(product["category"]["id"])

    r = admin_client.post(
        url,
        data={
            "allowed_subject_types": ["SELF_EMPLOYED"],
            "accept_from": "2026-12-31",
            "accept_to": "2026-01-01",
            "banks": bank_ids,
            "category": category,
        },
        follow_redirects=False,
    )
    assert r.status_code == 400

    r = admin_client.post(
        url,
        data={
            "allowed_subject_types": ["SELF_EMPLOYED", "FOO"],
            "accept_from": "",
            "accept_to": "",
            "banks": bank_ids,
            "category": category,
        },
        follow_redirects=False,
    )
    assert r.status_code == 400

    r = admin_client.post(
        url,
        data={
            "allowed_subject_types": ["SELF_EMPLOYED", "MCHJ"],
            "accept_from": "2026-01-01",
            "accept_to": "",
            "banks": bank_ids,
            "category": category,
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    fund = api.client.post(
        "/api/v1/fund/product-categories",
        headers=api.superadmin,
        json={"translations": tr("TEST Н", "TEST N", "TEST I"), "is_active": False},
    )
    assert fund.status_code == 201, fund.text
    api.category_ids.append(data(fund)["id"])
    r = admin_client.post(
        url,
        data={
            "allowed_subject_types": ["SELF_EMPLOYED"],
            "accept_from": "",
            "accept_to": "",
            "banks": bank_ids,
            "category": str(data(fund)["id"]),
        },
        follow_redirects=False,
    )
    assert r.status_code == 400

    detail = data(api.client.get(f"/api/v1/fund/products/{product['id']}", headers=api.superadmin))
    assert detail["accept_from"] == "2026-01-01" and detail["accept_to"] is None
    assert detail["allowed_subject_types"] == ["SELF_EMPLOYED", "MCHJ"]


def test_admin_product_translation_edit(api, admin_client, product_application):
    product, _, _ = product_application
    rows = db_all(
        select(ProductTranslationORM.id, ProductTranslationORM.language).where(
            ProductTranslationORM.product_id == product["id"]
        )
    )
    en_id = next(row_id for row_id, language in rows if language == "en")
    url = f"/admin/product-translation-orm/edit/{en_id}"

    r = admin_client.post(url, data={"name": "x", "description": ""}, follow_redirects=False)
    assert r.status_code == 400
    r = admin_client.post(
        url, data={"name": "TEST Edited", "description": "only en"}, follow_redirects=False
    )
    assert r.status_code == 400
    r = admin_client.post(
        url, data={"name": "TEST Edited", "description": ""}, follow_redirects=False
    )
    assert r.status_code in (302, 303)

    detail = data(api.client.get(f"/api/v1/fund/products/{product['id']}", headers=api.superadmin))
    assert detail["translations"][2] == {
        "language": "en",
        "name": "TEST Edited",
        "description": None,
    }
