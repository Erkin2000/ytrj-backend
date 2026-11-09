import json

from src.common.swagger.i18n import translate_openapi, untranslated
from src.common.swagger.responses import NULL_MARKER
from src.main import app

LOGIN_PATHS = ["/api/v1/auth/login", "/api/v1/auth/sso/callback", "/api/v1/auth/sso/mock-login"]


def test_login_endpoints_document_tokens():
    spec = app.openapi()
    for path in LOGIN_PATHS:
        response = spec["paths"][path]["post"]["responses"]["200"]
        example = response["content"]["application/json"]["example"]["data"]
        assert set(example) == {"access_token", "refresh_token", "expires_in"}, path
    assert "/api/v1/auth/ticket/exchange" not in spec["paths"]


def test_null_fields_survive_schema_generation():
    spec = app.openapi()
    assert NULL_MARKER not in json.dumps(spec)
    error = spec["paths"]["/api/v1/auth/login"]["post"]["responses"]["401"]
    assert error["content"]["application/json"]["example"]["errors"] is None


def test_docs_fully_translated_to_uzbek():
    uz = translate_openapi(app.openapi())
    assert untranslated(uz) == []


def test_product_and_application_form_endpoints_documented():
    paths = app.openapi()["paths"]
    for path in (
        "/api/v1/products",
        "/api/v1/fund/products/{product_id}/publish",
        "/api/v1/fund/products/{product_id}/stages/{stage_id}/fields",
        "/api/v1/applications/{application_id}/stages/{stage_id}",
        "/api/v1/applications/{application_id}/fields/{field_id}/files",
    ):
        assert path in paths, path
    for removed in ("project", "location", "founders", "photos", "documents"):
        assert f"/api/v1/applications/{{application_id}}/{removed}" not in paths, removed
