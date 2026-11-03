import pytest

from src.common.urls import append_query, normalize_redirect_target
from src.config import Settings


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://yoshlarfondi.uz", "https://yoshlarfondi.uz/"),
        ("https://f.uz/login?x=1", "https://f.uz/login?x=1"),
        ("/api/auth/one-id/callback", "/api/auth/one-id/callback"),
        ("  https://f.uz/  ", "https://f.uz/"),
    ],
)
def test_normalize_accepts_http_urls_and_root_paths(value, expected):
    assert normalize_redirect_target(value, "X") == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "api/x",
        "//evil.com",
        "javascript:alert(1)",
        "ftp://f.uz/",
        "/api/v1/redirect/from-backend",
        "https://f.uz/api/v1/redirect/from-backend/",
    ],
)
def test_normalize_rejects_unsafe_or_looping_targets(value):
    with pytest.raises(ValueError):
        normalize_redirect_target(value, "X")


def test_append_query_keeps_own_query_and_fragment():
    url = append_query("https://front.uz/login?lang=uz#top", [("code", "a b"), ("state", "s+t")])
    assert url == "https://front.uz/login?lang=uz&code=a+b&state=s%2Bt#top"


def _settings(**overrides) -> Settings:
    base = {
        "DB_HOST": "h",
        "DB_USER": "u",
        "DB_PASS": "p",
        "DB_NAME": "n",
        "SSO_BASE_URL": "https://sso",
        "SSO_CLIENT_ID": "id",
        "SSO_CLIENT_SECRET": "secret",
        "SSO_REDIRECT_URI": "https://x/api/v1/redirect/from-backend",
        "JWT_SECRET_KEY": "test",
        "ADMIN_SESSION_SECRET": "test",
    }
    return Settings(_env_file=None, **{**base, **overrides})


def test_empty_frontend_redirect_falls_back_to_builtin_page():
    assert _settings(SSO_FRONTEND_REDIRECT_URL="").SSO_FRONTEND_REDIRECT_URL == (
        "/api/auth/one-id/callback"
    )


def test_admin_frontend_redirect_is_validated():
    s = _settings(SSO_FRONTEND_REDIRECT_URL_ADMIN="https://admin.uz")
    assert s.SSO_FRONTEND_REDIRECT_URL_ADMIN == "https://admin.uz/"

    with pytest.raises(ValueError):
        _settings(SSO_FRONTEND_REDIRECT_URL_ADMIN="javascript:alert(1)")
