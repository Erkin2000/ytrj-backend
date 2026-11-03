import json

from src.common.swagger.i18n import translate_openapi, untranslated
from src.common.swagger.responses import NULL_MARKER
from src.main import app

LOGIN_PATHS = ["/api/v1/auth/login", "/api/v1/auth/sso/callback", "/api/v1/auth/sso/mock-login"]


def _login_examples(spec, path):
    response = spec["paths"][path]["post"]["responses"]["200"]
    return response["content"]["application/json"]["examples"]


def test_login_endpoints_document_both_cases():
    spec = app.openapi()
    for path in LOGIN_PATHS:
        examples = _login_examples(spec, path)
        assert set(examples) == {"same_site", "other_subdomain"}, path

        same = examples["same_site"]["value"]["data"]
        assert set(same) == {"access_token", "refresh_token", "expires_in"}

        other = examples["other_subdomain"]["value"]["data"]
        assert set(other) == {"role", "redirect_url"}
        assert "ticket=" in other["redirect_url"]


def test_null_fields_survive_schema_generation():
    spec = app.openapi()
    assert NULL_MARKER not in json.dumps(spec)
    error = spec["paths"]["/api/v1/auth/ticket/exchange"]["post"]["responses"]["401"]
    assert error["content"]["application/json"]["example"]["errors"] is None


def test_auth_and_users_docs_fully_translated_to_uzbek():
    uz = translate_openapi(app.openapi())
    left = [
        path
        for path, _ in untranslated(uz)
        if ("/auth/" in path or "/redirect" in path or "/users" in path)
        and path.endswith((".summary", ".description"))
    ]
    assert left == []
    for path in LOGIN_PATHS:
        for example in _login_examples(uz, path).values():
            assert not any("А" <= ch <= "я" for ch in example["summary"]), example["summary"]
