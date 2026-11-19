"""Бюллетени Совета: вход члена Совета ключом E-IMZO, отправка, подпись ЭЦП,
решение связанной заявки, календарь и проверка по QR."""

import io
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from src.config import settings
from tests import test_application_workflow as workflow
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, data, db_run
from tests.test_application_workflow import status

pytestmark = pytest.mark.skipif(not settings.EIMZO_MOCK, reason="Нужен EIMZO_MOCK=true")

# Заявка на рассмотрении Фонда — фикстуры сценария заявки.
bank = workflow.bank
product = workflow.product
submitted_application = workflow.submitted_application

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def pdf_upload(name="byulleten.pdf"):
    return {"file": (name, io.BytesIO(PDF), "application/pdf")}


@pytest.fixture
def fund(api, role_ids):
    headers, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    return headers


@pytest.fixture
def council(api, role_ids):
    """Два члена Совета с правом решения: (headers, me)."""
    return [
        api.staff(eimzo=True, role_id=role_ids["COUNCIL_MEMBER"], full_name=f"TEST Council {i}")
        for i in (1, 2)
    ]


def my_ids(items):
    return {item["id"] for item in items}


def council_list(api, headers, tab="all"):
    r = api.client.get(f"/api/v1/council/bulletins?tab={tab}&per_page=100", headers=headers)
    assert r.status_code == 200, r.text
    return data(r)["items"]


# ---------- вход ----------


def test_council_member_signs_in_only_with_eimzo(api, role_ids):
    c = api.client
    pinfl = api.fresh_pinfl()
    r = api.create_user(pinfl=pinfl, password="Council12345", role_id=role_ids["COUNCIL_MEMBER"])
    assert r.status_code == 201, r.text
    username = data(r)["username"]

    r = c.post("/api/v1/auth/sso/mock-login", json={"pinfl": pinfl, "full_name": "TEST"})
    assert r.status_code == 403 and r.json()["code"] == "council_login_via_eimzo", r.text
    r = c.post("/api/v1/auth/login", json={"username": username, "password": "Council12345"})
    assert r.status_code == 403 and r.json()["code"] == "council_login_via_eimzo", r.text

    headers, me = api.eimzo_login(pinfl)
    assert me["role"]["code"] == "COUNCIL_MEMBER" and me["pinfl"] == pinfl

    config = data(c.get("/api/v1/auth/eimzo/config"))
    assert config["mock"] is True and config["bridge_url"]


def test_eimzo_login_refused_for_others(api, role_ids):
    c = api.client
    fund_pinfl = api.fresh_pinfl()
    api.create_user(pinfl=fund_pinfl, role_id=role_ids["FUND_OPERATOR"])

    for pinfl in (fund_pinfl, api.fresh_pinfl()):
        r = c.post("/api/v1/auth/eimzo/login", json={"code": f"mock-{pinfl}"})
        assert r.status_code == 403 and r.json()["code"] == "eimzo_login_not_allowed", r.text

    r = c.post("/api/v1/auth/eimzo/login", json={"code": "garbage"})
    assert r.status_code == 400 and r.json()["code"] == "eimzo_invalid_code"

    blocked = api.fresh_pinfl()
    user_id = data(api.create_user(pinfl=blocked, role_id=role_ids["COUNCIL_MEMBER"]))["id"]
    c.post(f"/api/v1/users/{user_id}/status", headers=api.superadmin, json={"status": "BLOCKED"})
    r = c.post("/api/v1/auth/eimzo/login", json={"code": f"mock-{blocked}"})
    assert r.status_code == 403 and r.json()["code"] == "user_blocked"


# ---------- бюллетень без заявки ----------


def test_bulletin_signing_flow(api, fund, council):
    c = api.client
    (a_h, a_me), (b_h, b_me) = council

    bulletin = api.bulletin(fund, name="TEST Kengash №1", file=pdf_upload())
    bid = bulletin["id"]
    assert bulletin["status"] == "PUBLISHED" and bulletin["number"].startswith("BYU-")
    assert (
        bulletin["file"]["content_type"] == "application/pdf"
        and len(bulletin["file"]["sha256"]) == 64
    )
    recipients = {s["member"]["id"] for s in bulletin["signature_list"] if s["member"]}
    assert {a_me["id"], b_me["id"]} <= recipients
    assert bulletin["signatures"]["signed"] == 0

    # Фонд видит, член Совета — нет.
    assert c.get("/api/v1/fund/bulletins", headers=a_h).status_code == 403
    assert bid in my_ids(data(c.get("/api/v1/fund/bulletins?per_page=100", headers=fund))["items"])

    assert bid in my_ids(council_list(api, a_h, "new"))
    counters = data(c.get("/api/v1/council/bulletins/counters", headers=a_h))
    assert counters["new"] >= 1 and counters["to_sign"] >= 1

    sign = f"/api/v1/council/bulletins/{bid}/sign"
    body = {"decision": "AGREE", "code": f"mock-{a_me['pinfl']}"}
    r = c.post(sign, headers=a_h, json=body)
    assert r.status_code == 400 and r.json()["code"] == "bulletin_not_viewed"

    opened = data(c.get(f"/api/v1/council/bulletins/{bid}", headers=a_h))
    assert opened["my"]["status"] == "VIEWED"
    assert opened["my"]["sign_blockers"] == ["bulletin_file_not_viewed"]
    assert "signature_list" not in opened and "signatures" not in opened
    assert bid not in my_ids(council_list(api, a_h, "new"))
    assert bid in my_ids(council_list(api, a_h, "to_sign"))

    r = c.post(sign, headers=a_h, json=body)
    assert r.status_code == 400 and r.json()["code"] == "bulletin_file_not_viewed"

    r = c.get(f"/api/v1/council/bulletins/{bid}/file", headers=a_h)
    assert r.status_code == 200 and r.content == PDF

    r = c.post(sign, headers=a_h, json={**body, "code": f"mock-{b_me['pinfl']}"})
    assert r.status_code == 403 and r.json()["code"] == "eimzo_signer_mismatch"

    r = c.post(sign, headers=a_h, json={**body, "comment": "Roziman"})
    assert r.status_code == 200, r.text
    signed = data(r)
    assert signed["my_status"] == "SIGNED" and signed["my_decision"] == "AGREE"
    assert signed["my"]["certificate"]["pinfl"] == a_me["pinfl"]
    assert signed["status"] == "PARTIALLY_SIGNED"

    r = c.post(sign, headers=a_h, json=body)
    assert r.status_code == 400 and r.json()["code"] == "bulletin_already_signed"
    assert bid in my_ids(council_list(api, a_h, "signed"))

    # Второй член Совета не видит решение первого.
    other = data(c.get(f"/api/v1/council/bulletins/{bid}", headers=b_h))
    assert other["my_status"] == "VIEWED" and other["my"]["decision"] is None

    detail = data(c.get(f"/api/v1/fund/bulletins/{bid}", headers=fund))
    rows = {s["member"]["id"]: s for s in detail["signature_list"] if s["member"]}
    assert rows[a_me["id"]]["status"] == "SIGNED" and rows[a_me["id"]]["decision"] == "AGREE"
    assert rows[a_me["id"]]["certificate"]["serial_number"]
    assert len(rows[a_me["id"]]["document_hash"]) == 64
    assert rows[b_me["id"]]["status"] == "VIEWED" and rows[b_me["id"]]["signed_at"] is None
    assert detail["signatures"]["signed"] == 1 and detail["signatures"]["agree"] == 1

    # После отправки меняется только срок.
    url = f"/api/v1/fund/bulletins/{bid}"
    r = c.patch(url, headers=fund, json={"name": "TEST другое"})
    assert r.status_code == 400 and r.json()["code"] == "bulletin_not_editable"
    r = c.patch(url, headers=fund, json={"deadline_at": api.iso(timedelta(days=10))})
    assert r.status_code == 200, r.text
    r = c.put(f"{url}/file", headers=fund, files=pdf_upload())
    assert r.status_code == 400 and r.json()["code"] == "bulletin_not_editable"
    assert c.delete(url, headers=fund).json()["code"] == "bulletin_status"

    # QR и страница проверки.
    r = c.get(f"{url}/qr", headers=fund)
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in r.content
    public_id = detail["public_id"]
    assert detail["verify_url"].endswith(f"/{public_id}")

    check = data(c.get(f"/api/v1/public/bulletins/{public_id}"))
    assert check["validity"] == "VALID" and check["name"] == "TEST Kengash №1"
    assert check["file"]["sha256"] == bulletin["file"]["sha256"] and check["file"]["url"] is None
    signers = {s["full_name"]: s["signed"] for s in check["signers"]}
    assert signers[a_me["full_name"]] is True and signers[b_me["full_name"]] is False
    decisions = {s["full_name"]: s["decision"] for s in check["signers"]}
    assert decisions[a_me["full_name"]] == "AGREE" and decisions[b_me["full_name"]] is None
    assert (check["agree_count"], check["against_count"], check["not_signed_count"]) == (1, 0, 1)

    page = c.get(f"/bulletins/verify/{public_id}")
    assert page.status_code == 200 and "TEST Kengash №1" in page.text
    assert "Hujjat haqiqiy" in page.text
    assert "Документ действителен" in c.get(f"/bulletins/verify/{public_id}?lang=ru").text

    # Аннулирование: подписи остаются, QR — «Аннулирован», подписать больше нельзя.
    r = c.post(f"{url}/cancel", headers=fund, json={"reason": "TEST ошибка в тексте"})
    assert r.status_code == 200 and data(r)["status"] == "CANCELLED"
    assert data(c.get(f"/api/v1/public/bulletins/{public_id}"))["validity"] == "CANCELLED"
    c.get(f"/api/v1/council/bulletins/{bid}/file", headers=b_h)
    r = c.post(sign, headers=b_h, json={"decision": "AGAINST", "code": f"mock-{b_me['pinfl']}"})
    assert r.status_code == 400 and r.json()["code"] == "bulletin_not_open_for_signing"
    assert c.post(f"{url}/cancel", headers=fund, json={"reason": "TEST again"}).status_code == 400


def test_verify_unknown_document(client):
    r = client.get("/api/v1/public/bulletins/unknown-id")
    assert r.status_code == 404 and r.json()["code"] == "bulletin_not_found"
    page = client.get("/bulletins/verify/unknown-id")
    assert page.status_code == 404 and "Hujjatni tasdiqlab boʻlmaydi" in page.text


# ---------- отложенная отправка ----------


def test_pending_bulletin_is_sent_on_schedule(api, fund, council):
    c = api.client
    a_h, _ = council[0]

    r = api.create_bulletin(fund, status="PENDING")
    assert r.status_code == 400 and r.json()["code"] == "bulletin_schedule"
    r = api.create_bulletin(
        fund,
        status="PENDING",
        send_at=api.iso(timedelta(days=2)),
        deadline_at=api.iso(timedelta(days=1)),
    )
    assert r.status_code == 400 and r.json()["errors"][0]["field"] == "deadline_at"

    bulletin = api.bulletin(
        fund, status="PENDING", send_at=api.iso(timedelta(hours=1)), file=pdf_upload()
    )
    bid = bulletin["id"]
    assert bulletin["status"] == "PENDING" and bulletin["signature_list"] == []
    assert bulletin["qr_url"] and bulletin["verify_url"]
    assert c.get(f"/api/v1/council/bulletins/{bid}", headers=a_h).status_code == 404
    assert bid not in my_ids(council_list(api, a_h))

    url = f"/api/v1/fund/bulletins/{bid}"
    r = c.patch(url, headers=fund, json={"name": "TEST отложенный"})
    assert r.status_code == 200 and data(r)["name"] == "TEST отложенный"
    r = c.patch(url, headers=fund, json={"send_at": api.iso(timedelta(hours=-1))})
    assert r.status_code == 400 and r.json()["errors"][0]["field"] == "send_at"
    r = c.put(
        f"{url}/file", headers=fund, files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")}
    )
    assert r.status_code == 400 and r.json()["code"] == "invalid_document"
    r = c.delete(f"{url}/file", headers=fund)
    assert r.status_code == 200 and data(r)["file"] is None

    # Дата отправки наступила — бюллетень уходит при первом обращении (или фоновой задачей).
    db_run(
        lambda s: s.execute(
            text("UPDATE bulletins SET send_at = now() - interval '1 minute' WHERE id = :id"),
            {"id": bid},
        )
    )
    assert bid in my_ids(council_list(api, a_h, "new"))
    detail = data(c.get(url, headers=fund))
    assert detail["status"] == "PUBLISHED" and detail["published_at"]
    assert detail["signatures"]["total"] >= 2


def test_pending_bulletin_publish_now_and_delete(api, fund, council):
    c = api.client
    a_h, a_me = council[0]

    first = api.bulletin(fund, status="PENDING", send_at=api.iso(timedelta(days=1)))
    r = c.post(f"/api/v1/fund/bulletins/{first['id']}/publish", headers=fund)
    assert r.status_code == 200 and data(r)["status"] == "PUBLISHED"
    assert c.post(f"/api/v1/fund/bulletins/{first['id']}/publish", headers=fund).status_code == 400
    # Без файла подписать можно сразу после просмотра.
    assert api.sign(a_h, first["id"], a_me["pinfl"], "AGAINST").status_code == 200

    second = api.bulletin(fund, status="PENDING", send_at=api.iso(timedelta(days=1)))
    url = f"/api/v1/fund/bulletins/{second['id']}"
    assert c.delete(url, headers=fund).status_code == 200
    assert c.get(url, headers=fund).status_code == 404


def test_calendar(api, fund, council):
    c = api.client
    a_h, _ = council[0]
    bulletin = api.bulletin(fund, deadline_at=api.iso(timedelta(days=3)))

    def events(path, headers, **params):
        r = c.get(path, headers=headers, params=params)
        assert r.status_code == 200, r.text
        return [(e["type"], e["bulletin_id"]) for day in data(r) for e in day["events"]]

    start = date.today() - timedelta(days=1)
    end = start + timedelta(days=10)
    params = {"date_from": start.isoformat(), "date_to": end.isoformat()}
    mine = events("/api/v1/council/bulletins/calendar", a_h, **params)
    assert ("SEND", bulletin["id"]) in mine and ("DEADLINE", bulletin["id"]) in mine
    fund_events = events("/api/v1/fund/bulletins/calendar", fund, **params)
    assert ("DEADLINE", bulletin["id"]) in fund_events

    r = c.get(
        "/api/v1/council/bulletins/calendar",
        headers=a_h,
        params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
    )
    assert r.status_code == 400


# ---------- бюллетень по заявке ----------


def test_against_vote_rejects_application(api, role_ids, applicant, submitted_application, council):
    c, app_id = api.client, submitted_application
    fund_h, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    a_h, a_me = council[0]

    bulletin = api.bulletin(fund_h, application_id=app_id)
    assert status(api, app_id, applicant) == "COUNCIL_REVIEW"
    assert (
        data(c.get(f"/api/v1/council/bulletins/{bulletin['id']}", headers=a_h))["application"]["id"]
        == app_id
    )
    assert c.get(f"/api/v1/applications/{app_id}", headers=a_h).status_code == 200

    # Заявка уже в бюллетене — второй привязать нельзя.
    r = api.create_bulletin(fund_h, application_id=app_id)
    assert r.status_code == 400 and r.json()["code"] == "bulletin_application"

    r = api.sign(a_h, bulletin["id"], a_me["pinfl"], "AGAINST", comment="TEST недостаточно данных")
    assert r.status_code == 200, r.text
    assert status(api, app_id, applicant) == "COUNCIL_REJECTED"
    detail = data(c.get(f"/api/v1/applications/{app_id}", headers=applicant))
    assert detail["rejection_reason"] == "TEST недостаточно данных"


def test_cancel_returns_application_to_fund(
    api,
    role_ids,
    applicant,
    submitted_application,
    council,
):
    c, app_id = api.client, submitted_application
    fund_h, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    a_h, _ = council[0]

    bulletin = api.bulletin(fund_h, application_id=app_id)
    assert status(api, app_id, applicant) == "COUNCIL_REVIEW"
    r = c.post(
        f"/api/v1/fund/bulletins/{bulletin['id']}/cancel", headers=fund_h, json={"reason": "TEST"}
    )
    assert r.status_code == 200, r.text
    assert status(api, app_id, applicant) == "FUND_REVIEW"
    # Назначения сняты: член Совета больше не видит заявку.
    assert c.get(f"/api/v1/applications/{app_id}", headers=a_h).status_code in (403, 404)

    # Заявку снова можно отправить в Совет — новым бюллетенем (отложенным, затем удалить).
    pending = api.bulletin(
        fund_h, application_id=app_id, status="PENDING", send_at=api.iso(timedelta(days=1))
    )
    assert status(api, app_id, applicant) == "COUNCIL_REVIEW"
    assert c.delete(f"/api/v1/fund/bulletins/{pending['id']}", headers=fund_h).status_code == 200
    assert status(api, app_id, applicant) == "FUND_REVIEW"


def test_council_bulletin_endpoints_need_auth(client):
    assert client.get("/api/v1/council/bulletins").status_code == 401
    assert client.get("/api/v1/fund/bulletins").status_code == 401


# ---------- админ-панель ----------


@pytest.fixture
def admin_client(client, superadmin):
    r = client.post(
        "/admin/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    return client


def test_admin_bulletin_pages(api, admin_client, fund, council):
    a_h, a_me = council[0]
    bulletin = api.bulletin(fund, name="TEST Admin bulletin", file=pdf_upload())
    bid = bulletin["id"]
    assert api.sign(a_h, bid, a_me["pinfl"]).status_code == 200

    for path in ("/admin/", "/admin/bulletin-orm/list", "/admin/bulletin-signature-orm/list"):
        assert admin_client.get(path).status_code == 200, path

    page = admin_client.get(f"/admin/bulletin-orm/details/{bid}")
    assert page.status_code == 200
    assert "TEST Admin bulletin" in page.text and bulletin["number"] in page.text
    assert a_me["full_name"] in page.text and "modal-confirmation-cancel" in page.text

    r = admin_client.get(f"/admin/bulletin-file/{bid}")
    assert r.status_code == 200 and r.content == PDF
    r = admin_client.get(f"/admin/bulletin-qr/{bid}")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")

    signature_id = next(
        s["id"] for s in bulletin["signature_list"] if s["member"]["id"] == a_me["id"]
    )
    page = admin_client.get(f"/admin/bulletin-signature-orm/details/{signature_id}")
    assert page.status_code == 200 and a_me["pinfl"] in page.text

    r = admin_client.get(f"/admin/bulletin-orm/action/cancel?pks={bid}", follow_redirects=False)
    assert r.status_code == 302, r.text
    detail = data(api.client.get(f"/api/v1/fund/bulletins/{bid}", headers=fund))
    assert detail["status"] == "CANCELLED" and detail["signatures"]["signed"] == 1


def test_admin_publishes_and_deletes_bulletin_with_application(
    api, role_ids, admin_client, applicant, submitted_application, council
):
    app_id = submitted_application
    fund_h, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    bulletin = api.bulletin(
        fund_h, application_id=app_id, status="PENDING", send_at=api.iso(timedelta(days=1))
    )
    bid = bulletin["id"]

    page = admin_client.get(f"/admin/application-orm/details/{app_id}")
    assert page.status_code == 200 and bulletin["number"] in page.text

    r = admin_client.get(f"/admin/bulletin-orm/action/publish?pks={bid}", follow_redirects=False)
    assert r.status_code == 302, r.text
    assert (
        data(api.client.get(f"/api/v1/fund/bulletins/{bid}", headers=fund_h))["status"]
        == "PUBLISHED"
    )

    # Override Super Admin: удаляется и отправленный бюллетень, заявка возвращается Фонду.
    r = admin_client.delete(f"/admin/bulletin-orm/delete?pks={bid}")
    assert r.status_code == 200, r.text
    assert api.client.get(f"/api/v1/fund/bulletins/{bid}", headers=fund_h).status_code == 404
    assert status(api, app_id, applicant) == "FUND_REVIEW"
