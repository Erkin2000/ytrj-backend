import random

import pytest

from src.config import settings
from tests.conftest import data

pytestmark = pytest.mark.skipif(
    settings.SCORING_MODE != "auto_pass", reason="Нужен SCORING_MODE=auto_pass"
)


@pytest.fixture
def bank(banks):
    for item in banks:
        if item.get("is_active", True) and "SELF_EMPLOYED" in (
            item.get("allowed_subject_types") or []
        ):
            return item
    pytest.skip("Нет активного банка для SELF_EMPLOYED")


@pytest.fixture
def applicant(api):
    login, _ = api.sso_login(full_name="TEST Applicant")
    headers = login["headers"]
    r = api.client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "phone": "+998901234567",
            "passport_number": "AA" + "".join(random.choices("0123456789", k=7)),
            "inn": "".join(random.choices("0123456789", k=9)),
            "email": "test@example.com",
            "gender": "MALE",
            "date_of_birth": "1995-05-05",
        },
    )
    assert r.status_code == 200 and data(r)["profile_complete"], r.text
    return headers


@pytest.fixture
def submitted_application(api, applicant, bank, photo_upload):
    c = api.client
    r = c.post("/api/v1/applications", headers=applicant, json={"subject_type": "SELF_EMPLOYED"})
    assert r.status_code == 201, r.text
    app_id = data(r)["id"]
    api.application_ids.append(app_id)

    steps = [
        (
            "project",
            {
                "requested_amount": 50_000_000,
                "loan_term_months": 24,
                "total_cost": 60_000_000,
                "jobs_count": 3,
                "description": "TEST project description long enough",
            },
        ),
        (
            "location",
            {
                "lat": 41.31,
                "lng": 69.28,
                "region": "Toshkent",
                "district": "Yunusobod",
                "makhalla": "TEST",
                "confirmed": True,
            },
        ),
        ("bank", {"bank_id": bank["id"]}),
    ]
    for block, body in steps:
        r = c.put(f"/api/v1/applications/{app_id}/{block}", headers=applicant, json=body)
        assert r.status_code == 200, (block, r.text)

    for i in range(settings.MAX_APPLICATION_PHOTOS):
        r = c.post(
            f"/api/v1/applications/{app_id}/photos",
            headers=applicant,
            files=photo_upload(f"p{i}.png"),
        )
        assert r.status_code in (200, 201), r.text

    r = c.post(f"/api/v1/applications/{app_id}/submit", headers=applicant)
    assert r.status_code == 200, r.text
    return app_id


def status(api, app_id, headers):
    return data(api.client.get(f"/api/v1/applications/{app_id}", headers=headers))["status"]


def test_full_application_lifecycle(api, role_ids, bank, applicant, submitted_application):
    c, app_id = api.client, submitted_application

    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    bank_h, _ = api.staff(role_id=role_ids["BANK_EMPLOYEE"], bank_id=bank["id"])
    council_h, council_me = api.staff(role_id=role_ids["COUNCIL_MEMBER"])
    mute_h, mute_me = api.staff(
        role_id=role_ids["COUNCIL_MEMBER"],
        permissions=["council_review.read", "applications.read"],
    )

    assert status(api, app_id, applicant) == "SENT_TO_BANK"

    assert c.get("/api/v1/fund/applications", headers=applicant).status_code == 403
    bank_items = data(c.get("/api/v1/bank/applications?per_page=100", headers=bank_h))["items"]
    assert any(item["id"] == app_id for item in bank_items)

    assert c.post(f"/api/v1/bank/applications/{app_id}/accept", headers=bank_h).status_code == 200
    r = c.post(
        f"/api/v1/bank/applications/{app_id}/decision",
        headers=bank_h,
        json={"decision": "APPROVED"},
    )
    assert r.status_code == 200, r.text
    assert status(api, app_id, fund) == "BANK_APPROVED"

    send = f"/api/v1/fund/applications/{app_id}/send-to-council"
    assert (
        c.post(send, headers=fund, json={"council_member_ids": [mute_me["id"]]}).status_code == 404
    )
    r = c.post(send, headers=fund, json={"council_member_ids": [council_me["id"]]})
    assert r.status_code == 200, r.text
    assert c.get(f"/api/v1/applications/{app_id}", headers=mute_h).status_code in (403, 404)

    r = c.post(
        f"/api/v1/council/applications/{app_id}/decision",
        headers=council_h,
        json={"decision": "APPROVED"},
    )
    assert r.status_code == 200, r.text

    r = c.post(
        f"/api/v1/fund/applications/{app_id}/allocate",
        headers=fund,
        json={"amount": 50_000_000, "reference_number": "TEST-1"},
    )
    assert r.status_code == 200, r.text
    r = c.post(f"/api/v1/fund/applications/{app_id}/complete", headers=fund, json={})
    assert r.status_code == 200, r.text
    assert status(api, app_id, applicant) == "COMPLETED"

    for path, headers in [
        ("/api/v1/fund/applications/counters", fund),
        ("/api/v1/bank/applications/counters", bank_h),
        ("/api/v1/council/applications/counters", council_h),
        ("/api/v1/applications", applicant),
    ]:
        assert c.get(path, headers=headers).status_code == 200, path
