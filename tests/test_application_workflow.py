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


def history_statuses(api, app_id, headers):
    items = data(api.client.get(f"/api/v1/applications/{app_id}/history", headers=headers))
    items = items if isinstance(items, list) else items.get("items", [])
    return [item.get("to_status") or item.get("status") for item in items]


def test_full_application_lifecycle(api, role_ids, bank, applicant, submitted_application):
    c, app_id = api.client, submitted_application

    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    bank_h, _ = api.staff(role_id=role_ids["BANK_EMPLOYEE"], bank_id=bank["id"])
    council_h, council_me = api.staff(role_id=role_ids["COUNCIL_MEMBER"])
    mute_h, mute_me = api.staff(
        role_id=role_ids["COUNCIL_MEMBER"],
        permissions=["council_review.read", "applications.read"],
    )

    assert status(api, app_id, applicant) == "FUND_REVIEW"
    assert c.get("/api/v1/fund/applications", headers=applicant).status_code == 403

    def bank_sees():
        items = data(c.get("/api/v1/bank/applications?per_page=100", headers=bank_h))["items"]
        return any(item["id"] == app_id for item in items)

    assert not bank_sees()
    assert c.get(f"/api/v1/applications/{app_id}", headers=bank_h).status_code in (403, 404)

    send = f"/api/v1/fund/applications/{app_id}/send-to-council"
    assert (
        c.post(send, headers=fund, json={"council_member_ids": [mute_me["id"]]}).status_code == 404
    )
    r = c.post(send, headers=fund, json={"council_member_ids": [council_me["id"]]})
    assert r.status_code == 200, r.text
    assert status(api, app_id, fund) == "COUNCIL_REVIEW"
    assert c.get(f"/api/v1/applications/{app_id}", headers=mute_h).status_code in (403, 404)
    assert not bank_sees()

    r = c.post(
        f"/api/v1/council/applications/{app_id}/decision",
        headers=council_h,
        json={"decision": "APPROVED"},
    )
    assert r.status_code == 200, r.text
    assert status(api, app_id, applicant) == "SENT_TO_BANK"
    assert bank_sees()

    assert c.post(f"/api/v1/bank/applications/{app_id}/accept", headers=bank_h).status_code == 200
    r = c.post(
        f"/api/v1/bank/applications/{app_id}/decision",
        headers=bank_h,
        json={"decision": "APPROVED"},
    )
    assert r.status_code == 200, r.text
    assert status(api, app_id, applicant) == "COMPLETED"

    history = history_statuses(api, app_id, applicant)
    assert history[history.index("SCORING_IN_PROGRESS") :] == [
        "SCORING_IN_PROGRESS",
        "FUND_REVIEW",
        "COUNCIL_REVIEW",
        "COUNCIL_REVIEW",
        "COUNCIL_APPROVED",
        "SENT_TO_BANK",
        "BANK_REVIEW",
        "BANK_APPROVED",
        "COMPLETED",
    ], history

    progress = data(c.get(f"/api/v1/applications/{app_id}/progress", headers=applicant))
    steps = progress if isinstance(progress, list) else progress.get("steps", progress)
    assert [s["key"] for s in steps] == [
        "submitted",
        "scoring",
        "fund_review",
        "council_review",
        "sent_to_bank",
        "bank_review",
        "completed",
    ]
    assert all(s["state"] == "done" for s in steps)

    for path, headers in [
        ("/api/v1/fund/applications/counters", fund),
        ("/api/v1/bank/applications/counters", bank_h),
        ("/api/v1/council/applications/counters", council_h),
        ("/api/v1/applications", applicant),
    ]:
        assert c.get(path, headers=headers).status_code == 200, path


def test_fund_rejects_before_council(api, role_ids, applicant, submitted_application):
    c, app_id = api.client, submitted_application
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])

    reject = f"/api/v1/fund/applications/{app_id}/reject"
    assert c.post(reject, headers=fund, json={}).status_code == 422

    r = c.post(reject, headers=fund, json={"reason": "Не подходит под программу"})
    assert r.status_code == 200, r.text
    assert status(api, app_id, applicant) == "FUND_REJECTED"

    detail = data(c.get(f"/api/v1/applications/{app_id}", headers=applicant))
    assert detail["rejection_reason"] == "Не подходит под программу"

    r = c.post(f"/api/v1/fund/applications/{app_id}/send-to-council", headers=fund, json={})
    assert r.status_code == 400


def test_bank_rejects_after_council(api, role_ids, bank, applicant, submitted_application):
    c, app_id = api.client, submitted_application
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    bank_h, _ = api.staff(role_id=role_ids["BANK_EMPLOYEE"], bank_id=bank["id"])
    council_h, council_me = api.staff(role_id=role_ids["COUNCIL_MEMBER"])

    c.post(
        f"/api/v1/fund/applications/{app_id}/send-to-council",
        headers=fund,
        json={"council_member_ids": [council_me["id"]]},
    )
    c.post(
        f"/api/v1/council/applications/{app_id}/decision",
        headers=council_h,
        json={"decision": "APPROVED"},
    )
    c.post(f"/api/v1/bank/applications/{app_id}/accept", headers=bank_h)
    r = c.post(
        f"/api/v1/bank/applications/{app_id}/decision",
        headers=bank_h,
        json={"decision": "REJECTED", "reason": "Недостаточно залога"},
    )
    assert r.status_code == 200, r.text
    assert status(api, app_id, applicant) == "BANK_REJECTED"


def test_removed_allocation_endpoints(api, role_ids, submitted_application):
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    for action in ("allocate", "complete", "scoring/result", "send-to-bank"):
        r = api.client.post(
            f"/api/v1/fund/applications/{submitted_application}/{action}", headers=fund, json={}
        )
        assert r.status_code in (404, 405), action
