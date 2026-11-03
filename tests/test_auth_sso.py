from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from src.account.models.user_model import UserORM
from src.config import settings
from tests.conftest import bearer, data, db_all

ROLE_URLS = {
    "COUNCIL_MEMBER": "https://council.example.uz/",
    "APPLICANT": "https://cabinet.example.uz/home?lang=uz",
    "SUPER_ADMIN": "https://admin.example.uz/",
}


@pytest.fixture
def role_urls(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_HOME_URLS", ROLE_URLS)
    return ROLE_URLS


def ticket_of(url: str) -> str:
    return parse_qs(urlsplit(url).query)["ticket"][0]


LOGIN_PAGE = "https://front.uz/login?lang=uz"


@pytest.fixture
def portal(monkeypatch):
    """Подменяет обмен code у YIA Portal: profile задаёт тест (portal["profile"])."""
    from src.auth.schemas.auth_schema import SSOProfileDTO
    from src.auth.services.sso_service import YiaSSOService

    state = {"profile": None, "codes": []}

    async def fake_exchange(self, code):
        state["codes"].append(code)
        return SSOProfileDTO(**state["profile"])

    monkeypatch.setattr(YiaSSOService, "exchange_code", fake_exchange)
    return state


def test_redirect_from_backend_passes_portal_params(client, monkeypatch):
    monkeypatch.setattr(settings, "SSO_FRONTEND_REDIRECT_URL", LOGIN_PAGE)
    r = client.get("/api/v1/redirect/from-backend?code=abc&state=xyz", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == LOGIN_PAGE + "&code=abc&state=xyz"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_sso_callback_exchanges_code_and_returns_cabinet_url(api, role_ids, role_urls, portal):
    pinfl = api.fresh_pinfl()
    staff_id = data(api.create_user(pinfl=pinfl, role_id=role_ids["COUNCIL_MEMBER"]))["id"]
    portal["profile"] = {"sub": f"sub-{pinfl}", "full_name": "TEST Council", "pinfl": pinfl}

    state = data(api.client.get("/api/v1/auth/sso/authorize"))["state"]
    r = api.client.post("/api/v1/auth/sso/callback", json={"code": "CODE1", "state": state})

    assert r.status_code == 200, r.text
    login = data(r)
    assert portal["codes"] == ["CODE1"]
    assert login["role"] == "COUNCIL_MEMBER"
    assert login["redirect_url"].startswith("https://council.example.uz/?ticket=")
    me = data(api.client.get("/api/v1/auth/me", headers=bearer(login["access_token"])))
    assert me["id"] == staff_id


def test_sso_callback_rejects_forged_state_and_portal_error(client, portal):
    r = client.post("/api/v1/auth/sso/callback", json={"code": "C", "state": "forged"})
    assert r.status_code == 400
    assert r.json()["code"] == "sso_invalid_state"

    state = data(client.get("/api/v1/auth/sso/authorize"))["state"]
    r = client.post("/api/v1/auth/sso/callback", json={"state": state, "error": "access_denied"})
    assert r.status_code == 403
    assert r.json()["code"] == "sso_access_denied"
    assert portal["codes"] == []


def test_blocked_staff_cannot_sign_in(api, role_ids, portal):
    pinfl = api.fresh_pinfl()
    staff_id = data(api.create_user(pinfl=pinfl, role_id=role_ids["COUNCIL_MEMBER"]))["id"]
    api.client.post(
        f"/api/v1/users/{staff_id}/status", headers=api.superadmin, json={"status": "BLOCKED"}
    )
    portal["profile"] = {"sub": f"sub-{pinfl}", "full_name": "TEST", "pinfl": pinfl}

    state = data(api.client.get("/api/v1/auth/sso/authorize"))["state"]
    r = api.client.post("/api/v1/auth/sso/callback", json={"code": "C", "state": state})
    assert r.status_code == 403
    assert r.json()["code"] == "user_blocked"


def test_password_login_returns_cabinet_url_and_one_time_ticket(client, role_urls):
    from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME

    r = client.post(
        "/api/v1/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    login = data(r)
    assert login["role"] == "SUPER_ADMIN"
    assert login["redirect_url"].startswith("https://admin.example.uz/?ticket=")

    ticket = ticket_of(login["redirect_url"])
    first = client.post("/api/v1/auth/ticket/exchange", json={"ticket": ticket})
    assert first.status_code == 200
    assert data(first)["access_token"]

    again = client.post("/api/v1/auth/ticket/exchange", json={"ticket": ticket})
    assert again.status_code == 401
    assert again.json()["code"] == "invalid_login_ticket"


def test_unknown_ticket_rejected(client):
    r = client.post("/api/v1/auth/ticket/exchange", json={"ticket": "x" * 43})
    assert r.status_code == 401


def test_staff_created_by_pinfl_signs_in_via_sso(api, role_ids, role_urls):
    pinfl = api.fresh_pinfl()
    r = api.create_user(pinfl=pinfl, role_id=role_ids["COUNCIL_MEMBER"], full_name="TEST Council")
    assert r.status_code == 201, r.text
    staff_id = data(r)["id"]

    login, _ = api.sso_login(pinfl)
    assert login["role"] == "COUNCIL_MEMBER"
    assert login["redirect_url"].startswith("https://council.example.uz/?ticket=")

    tokens = api.client.post(
        "/api/v1/auth/ticket/exchange", json={"ticket": ticket_of(login["redirect_url"])}
    )
    me = data(api.client.get("/api/v1/auth/me", headers=bearer(data(tokens)["access_token"])))
    assert me["id"] == staff_id

    stored = db_all(select(UserORM.sso_sub).where(UserORM.id == staff_id))
    assert stored[0][0] == f"mock-{pinfl}"


def test_staff_without_password_cannot_use_password_login(api, role_ids):
    r = api.create_user(role_id=role_ids["COUNCIL_MEMBER"])
    assert r.status_code == 201
    login = api.client.post(
        "/api/v1/auth/login", json={"username": data(r)["username"], "password": "whatever123"}
    )
    assert login.status_code == 401


def test_pinfl_must_be_unique(api, role_ids):
    pinfl = api.fresh_pinfl()
    assert api.create_user(pinfl=pinfl, role_id=role_ids["COUNCIL_MEMBER"]).status_code == 201
    dup = api.create_user(pinfl=pinfl, role_id=role_ids["COUNCIL_MEMBER"])
    assert dup.status_code == 409
    assert dup.json()["code"] == "pinfl_already_exists"


def test_staff_needs_pinfl_or_password(api, role_ids):
    r = api.client.post(
        "/api/v1/users",
        headers=api.superadmin,
        json={"username": api.username(), "role_id": role_ids["COUNCIL_MEMBER"]},
    )
    assert r.status_code == 422


def test_pinfl_change_unlinks_sso(api, role_ids):
    pinfl = api.fresh_pinfl()
    staff_id = data(api.create_user(pinfl=pinfl, role_id=role_ids["COUNCIL_MEMBER"]))["id"]
    api.sso_login(pinfl)

    new_pinfl = api.fresh_pinfl()
    r = api.client.patch(
        f"/api/v1/users/{staff_id}", headers=api.superadmin, json={"pinfl": new_pinfl}
    )
    assert r.status_code == 200
    assert db_all(select(UserORM.pinfl, UserORM.sso_sub).where(UserORM.id == staff_id)) == [
        (new_pinfl, None)
    ]


def test_applicant_auto_created_and_cabinet_query_kept(api, role_urls):
    login, me = api.sso_login(full_name="TEST Applicant")
    assert me["role"]["code"] == "APPLICANT"
    assert login["redirect_url"].startswith("https://cabinet.example.uz/home?lang=uz&ticket=")


def test_role_without_url_goes_to_default(api, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_HOME_URLS", {})
    login, _ = api.sso_login()
    assert login["redirect_url"].startswith(settings.ROLE_HOME_URL_DEFAULT + "?ticket=")


def test_builtin_pages_render(client):
    assert client.get("/api/auth/one-id/login").status_code == 200
    assert client.get("/api/auth/one-id/callback").status_code == 200
