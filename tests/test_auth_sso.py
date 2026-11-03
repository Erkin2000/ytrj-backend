from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select, text

from src.account.models.user_model import UserORM
from src.config import settings
from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    bearer,
    data,
    db_all,
    db_scalar,
    tokens_of,
)

ROLE_URLS = {
    "COUNCIL_MEMBER": "https://council.example.uz/",
    "APPLICANT": "https://cabinet.example.uz/home?lang=uz",
    "SUPER_ADMIN": "https://admin.example.uz/",
}


FRONT_LOGIN = "https://front.example.uz/login"


@pytest.fixture
def role_urls(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_HOME_URLS", ROLE_URLS)
    monkeypatch.setattr(settings, "SSO_FRONTEND_REDIRECT_URL", FRONT_LOGIN)
    return ROLE_URLS


def ticket_of(url: str) -> str:
    return parse_qs(urlsplit(url).query)["ticket"][0]


LOGIN_PAGE = "https://front.uz/login?lang=uz"


@pytest.fixture
def portal(monkeypatch):
    """Подменяет обмен code у YIA Portal: profile задаёт тест (portal["profile"])."""
    from src.auth.schemas.auth_schema import SSOProfileDTO, SSOSite
    from src.auth.services.sso_service import YiaSSOService

    state = {"profile": None, "codes": [], "clients": []}

    async def fake_exchange(self, code, site=SSOSite.MAIN):
        state["codes"].append(code)
        state["clients"].append(self.client(site)[0])
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
    assert set(login) == {"role", "redirect_url"}
    tokens = tokens_of(api.client, login)
    me = data(api.client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"])))
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

    login, me = api.sso_login(pinfl)
    assert login["role"] == "COUNCIL_MEMBER"
    assert login["redirect_url"].startswith("https://council.example.uz/?ticket=")
    assert set(login) - {"headers"} == {"role", "redirect_url"}
    assert me["id"] == staff_id

    reused = api.client.post(
        "/api/v1/auth/ticket/exchange", json={"ticket": ticket_of(login["redirect_url"])}
    )
    assert reused.status_code == 401

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
    monkeypatch.setattr(settings, "SSO_FRONTEND_REDIRECT_URL", FRONT_LOGIN)
    login, _ = api.sso_login()
    assert login["redirect_url"].startswith(settings.ROLE_HOME_URL_DEFAULT + "?ticket=")


def test_builtin_pages_render(client):
    assert client.get("/api/auth/one-id/login").status_code == 200
    assert client.get("/api/auth/one-id/callback").status_code == 200


def _count(table, user_id):
    return db_scalar(text(f"SELECT count(*) FROM {table} WHERE user_id = :u"), {"u": user_id})


def test_same_site_cabinet_gets_tokens_without_ticket(api, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_HOME_URLS", {"APPLICANT": "https://yoshlarfondi.test/"})
    monkeypatch.setattr(settings, "SSO_FRONTEND_REDIRECT_URL", "https://yoshlarfondi.test/login")

    r = api.client.post(
        "/api/v1/auth/sso/mock-login", json={"pinfl": api.fresh_pinfl(), "full_name": "TEST"}
    )
    login = data(r)
    assert set(login) == {"access_token", "refresh_token", "expires_in"}

    me = data(api.client.get("/api/v1/auth/me", headers=bearer(login["access_token"])))
    api.remember_user(me["id"])
    assert _count("login_tickets", me["id"]) == 0
    assert _count("refresh_tokens", me["id"]) == 1


def test_other_subdomain_gets_only_ticket_and_one_session(api, role_urls):
    r = api.client.post(
        "/api/v1/auth/sso/mock-login", json={"pinfl": api.fresh_pinfl(), "full_name": "TEST"}
    )
    login = data(r)
    assert set(login) == {"role", "redirect_url"}
    assert "?" in login["redirect_url"] and "ticket=" in login["redirect_url"]

    tokens = tokens_of(api.client, login)
    me = data(api.client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"])))
    api.remember_user(me["id"])
    assert _count("refresh_tokens", me["id"]) == 1


def test_origin_header_decides_for_password_login(client, role_urls):
    body = {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}

    same = data(
        client.post("/api/v1/auth/login", json=body, headers={"Origin": "https://admin.example.uz"})
    )
    assert set(same) == {"access_token", "refresh_token", "expires_in"}

    other = data(client.post("/api/v1/auth/login", json=body))
    assert set(other) == {"role", "redirect_url"}
    assert other["redirect_url"].startswith("https://admin.example.uz/?ticket=")


ADMIN_FRONT = "https://admin.example.uz/login"


@pytest.fixture
def sites(monkeypatch):
    monkeypatch.setattr(settings, "SSO_CLIENT_ID", "main-client")
    monkeypatch.setattr(settings, "SSO_CLIENT_SECRET", "main-secret")
    monkeypatch.setattr(
        settings, "SSO_REDIRECT_URI", "https://yoshlarfondi.uz/api/v1/redirect/from-backend"
    )
    monkeypatch.setattr(settings, "SSO_CLIENT_ID_ADMIN", "admin-client")
    monkeypatch.setattr(settings, "SSO_CLIENT_SECRET_ADMIN", "admin-secret")
    monkeypatch.setattr(
        settings,
        "SSO_REDIRECT_URI_ADMIN",
        "https://admin.yoshlarfondi.uz/api/v1/redirect/from-backend",
    )
    monkeypatch.setattr(settings, "SSO_FRONTEND_REDIRECT_URL", FRONT_LOGIN)
    monkeypatch.setattr(settings, "SSO_FRONTEND_REDIRECT_URL_ADMIN", ADMIN_FRONT)


def _authorize(client, **params):
    r = client.get("/api/v1/auth/sso/authorize", params=params)
    assert r.status_code == 200, r.text
    auth = data(r)
    return auth, parse_qs(urlsplit(auth["authorize_url"]).query)


def test_authorize_uses_client_of_selected_site(client, sites):
    _, main = _authorize(client)
    assert main["client_id"] == ["main-client"]
    assert main["redirect_uri"] == ["https://yoshlarfondi.uz/api/v1/redirect/from-backend"]

    _, main_explicit = _authorize(client, site="yoshlarfondi")
    assert main_explicit["client_id"] == ["main-client"]

    _, admin = _authorize(client, site="admin")
    assert admin["client_id"] == ["admin-client"]
    assert admin["redirect_uri"] == ["https://admin.yoshlarfondi.uz/api/v1/redirect/from-backend"]


def test_authorize_rejects_unknown_site(client, sites):
    assert client.get("/api/v1/auth/sso/authorize", params={"site": "bank"}).status_code == 422


def test_admin_site_without_redirect_uri_is_not_configured(client, sites, monkeypatch):
    monkeypatch.setattr(settings, "SSO_REDIRECT_URI_ADMIN", "")
    r = client.get("/api/v1/auth/sso/authorize", params={"site": "admin"})
    assert r.status_code == 401
    assert r.json()["code"] == "sso_failed"


def test_admin_site_falls_back_to_main_client(client, sites, monkeypatch):
    monkeypatch.setattr(settings, "SSO_CLIENT_ID_ADMIN", "")
    monkeypatch.setattr(settings, "SSO_CLIENT_SECRET_ADMIN", "")
    _, admin = _authorize(client, site="admin")
    assert admin["client_id"] == ["main-client"]
    assert admin["redirect_uri"] == ["https://admin.yoshlarfondi.uz/api/v1/redirect/from-backend"]


def test_redirect_from_backend_returns_to_front_of_site(client, sites):
    admin_auth, _ = _authorize(client, site="admin")
    r = client.get(
        "/api/v1/redirect/from-backend",
        params={"code": "C", "state": admin_auth["state"]},
        follow_redirects=False,
    )
    assert r.headers["location"].startswith(ADMIN_FRONT + "?code=C&state=")

    main_auth, _ = _authorize(client)
    r = client.get(
        "/api/v1/redirect/from-backend",
        params={"code": "C", "state": main_auth["state"]},
        follow_redirects=False,
    )
    assert r.headers["location"].startswith(FRONT_LOGIN + "?code=C&state=")

    r = client.get(
        "/api/v1/redirect/from-backend",
        params={"code": "C", "state": "forged"},
        follow_redirects=False,
    )
    assert r.headers["location"] == FRONT_LOGIN + "?code=C&state=forged"


def test_callback_exchanges_code_with_client_of_site(api, role_ids, sites, portal):
    pinfl = api.fresh_pinfl()
    api.create_user(pinfl=pinfl, role_id=role_ids["COUNCIL_MEMBER"])
    portal["profile"] = {"sub": f"sub-{pinfl}", "full_name": "TEST", "pinfl": pinfl}

    for site, client_id in (("admin", "admin-client"), ("yoshlarfondi", "main-client")):
        auth, _ = _authorize(api.client, site=site)
        r = api.client.post("/api/v1/auth/sso/callback", json={"code": "C", "state": auth["state"]})
        assert r.status_code == 200, r.text
        assert portal["clients"][-1] == client_id


def test_redirect_site_param_selects_front_and_is_not_forwarded(client, sites):
    main_auth, _ = _authorize(client)
    r = client.get(
        "/api/v1/redirect/from-backend",
        params={"site": "admin", "code": "C", "state": main_auth["state"]},
        follow_redirects=False,
    )
    location = r.headers["location"]
    assert location.startswith(ADMIN_FRONT + "?code=C&state=")
    assert "site=" not in location

    admin_auth, _ = _authorize(client, site="admin")
    r = client.get(
        "/api/v1/redirect/from-backend",
        params={"site": "yoshlarfondi", "code": "C", "state": admin_auth["state"]},
        follow_redirects=False,
    )
    assert r.headers["location"].startswith(FRONT_LOGIN + "?code=C&state=")


def test_redirect_site_param_from_registered_redirect_uri(client, sites):
    r = client.get(
        "/api/v1/redirect/from-backend?site=admin&error=access_denied&state=forged",
        follow_redirects=False,
    )
    assert r.headers["location"] == ADMIN_FRONT + "?error=access_denied&state=forged"


def test_redirect_rejects_unknown_site(client, sites):
    r = client.get("/api/v1/redirect/from-backend", params={"site": "bank"}, follow_redirects=False)
    assert r.status_code == 422
