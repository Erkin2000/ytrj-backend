from pathlib import Path

import pytest
from sqlalchemy import text

from src.config import settings
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, data, db_scalar

pytestmark = pytest.mark.skipif(
    settings.SCORING_MODE != "auto_pass", reason="Нужен SCORING_MODE=auto_pass"
)

RELATED_TABLES = [
    "application_status_history",
    "application_scoring_attempts",
    "application_council_assignments",
    "application_field_values",
    "application_field_files",
    "application_photos",
    "application_documents",
    "application_founders",
    "demand_documents",
    "resource_allocations",
]


@pytest.fixture
def bank(banks):
    for item in banks:
        if item.get("is_active", True) and "SELF_EMPLOYED" in (
            item.get("allowed_subject_types") or []
        ):
            return item
    pytest.skip("Нет активного банка для SELF_EMPLOYED")


@pytest.fixture
def full_application(api, role_ids, bank, applicant, photo_upload):
    c = api.client
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    _, council_me = api.staff(role_id=role_ids["COUNCIL_MEMBER"])
    product = api.product(fund, [bank["id"]])
    stage = product["stages"][0]
    number, photo, _ = stage["fields"]

    r = c.post(
        "/api/v1/applications",
        headers=applicant,
        json={"product_id": product["id"], "subject_type": "SELF_EMPLOYED", "bank_id": bank["id"]},
    )
    assert r.status_code == 201, r.text
    app_id = data(r)["id"]
    api.application_ids.append(app_id)
    c.put(
        f"/api/v1/applications/{app_id}/stages/{stage['id']}",
        headers=applicant,
        json={"values": {str(number["id"]): "1000"}},
    )
    r = c.post(
        f"/api/v1/applications/{app_id}/fields/{photo['id']}/files",
        headers=applicant,
        files=photo_upload(),
    )
    assert r.status_code == 201, r.text
    assert c.post(f"/api/v1/applications/{app_id}/submit", headers=applicant).status_code == 200
    r = c.post(
        f"/api/v1/fund/applications/{app_id}/send-to-council",
        headers=fund,
        json={"council_member_ids": [council_me["id"]]},
    )
    assert r.status_code == 200, r.text
    return app_id, fund


def traces(app_id: int) -> dict:
    counts = {
        table: db_scalar(
            text(f"SELECT count(*) FROM {table} WHERE application_id = :id"), {"id": app_id}
        )
        for table in RELATED_TABLES
    }
    counts["applications"] = db_scalar(
        text("SELECT count(*) FROM applications WHERE id = :id"), {"id": app_id}
    )
    counts["media"] = (Path(settings.MEDIA_PATH) / "applications" / str(app_id)).exists()
    return counts


def test_superadmin_purges_application(api, applicant, full_application):
    c = api.client
    app_id, fund = full_application
    before = traces(app_id)
    assert before["applications"] == 1 and before["media"]
    assert before["application_status_history"] and before["application_scoring_attempts"]
    assert before["application_council_assignments"] and before["application_field_files"]

    url = f"/api/v1/admin/applications/{app_id}"
    assert c.delete(url, headers=fund).status_code == 403
    assert c.delete(url, headers=applicant).status_code == 403
    assert c.delete(url).status_code == 401

    r = c.delete(url, headers=api.superadmin)
    assert r.status_code == 200, r.text
    assert not any(traces(app_id).values()), traces(app_id)
    assert c.get(f"/api/v1/applications/{app_id}", headers=applicant).status_code == 404
    assert c.delete(url, headers=api.superadmin).status_code == 404


def test_admin_panel_purges_application(api, admin_client, full_application):
    app_id, _ = full_application
    assert traces(app_id)["media"]
    page = admin_client.get(f"/admin/application-orm/details/{app_id}").text
    assert "modal-delete" in page

    r = admin_client.delete(f"/admin/application-orm/delete?pks={app_id}")
    assert r.status_code == 200, r.text
    assert not any(traces(app_id).values()), traces(app_id)


@pytest.fixture
def admin_client(client, superadmin):
    r = client.post(
        "/admin/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    return client
