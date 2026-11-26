"""Договоры исполнителей и акты выполненных работ (dalolatnoma): черновик исполнителя,
подпись E-IMZO и отправка, проверка Фондом, возврат, подпись руководителя, PDF и QR."""

import hashlib
import io
from datetime import date

import pytest
from sqlalchemy import text

from src.config import settings
from tests.conftest import data, db_run, png_bytes

pytestmark = pytest.mark.skipif(not settings.EIMZO_MOCK, reason="Нужен EIMZO_MOCK=true")

CONTRACTS = "/api/v1/contracts"
MY = "/api/v1/my/acts"
FUND = "/api/v1/fund/acts"


def code(me: dict) -> str:
    return f"mock-{me['pinfl']}"


def png(name="screen.png"):
    return {"file": (name, io.BytesIO(png_bytes()), "image/png")}


class Team:
    """Исполнитель, проверяющий Фонда, руководитель и созданные договоры (для очистки)."""

    def __init__(self, api, role_ids):
        self.api = api
        self.c = api.client
        self.contractor, self.contractor_me = self._login(
            api, role_ids["CONTRACTOR"], "AHMADJONOV ZIYODBEK MURODJON O‘G‘LI"
        )
        self.reviewer, self.reviewer_me = self._login(
            api, role_ids["FUND_OPERATOR"], "TEST REVIEWER"
        )
        self.approver, self.approver_me = self._login(
            api, role_ids["FUND_OPERATOR"], "QULDOSHOV MIRZOBEK BERUNIY O‘G‘LI"
        )
        self.contract_ids: list[int] = []

    @staticmethod
    def _login(api, role_id: int, full_name: str):
        pinfl = api.fresh_pinfl()
        r = api.create_user(pinfl=pinfl, role_id=role_id, full_name=full_name)
        assert r.status_code == 201, r.text
        login, me = api.sso_login(pinfl, full_name=full_name)
        return login["headers"], me

    def contract(self, **body) -> dict:
        payload = {
            "number": f"TEST-{self.api.username()}",
            "signed_on": "2026-10-01",
            "contractor_id": self.contractor_me["id"],
            "position": "Loyiha menejeri (PM)",
            "subject": "YTRJ-EP moliyalashtirish modulini ishlab chiqish loyihasini boshqarish",
            "start_date": "2026-10-01",
            "end_date": "2026-12-31",
            "approver_id": self.approver_me["id"],
            **body,
        }
        r = self.c.post(CONTRACTS, headers=self.reviewer, json=payload)
        assert r.status_code == 201, r.text
        contract = data(r)
        self.contract_ids.append(contract["id"])
        return contract

    def draft(self, contract_id: int, period=("2026-10-23", "2026-11-26"), **body) -> dict:
        r = self.c.post(
            MY,
            headers=self.contractor,
            json={
                "contract_id": contract_id,
                "period_from": period[0],
                "period_to": period[1],
                **body,
            },
        )
        assert r.status_code == 201, r.text
        return data(r)

    def ready_draft(self, contract_id: int, **kwargs) -> dict:
        act = self.draft(contract_id, **kwargs)
        r = self.c.put(
            f"{MY}/{act['id']}/items",
            headers=self.contractor,
            json={
                "items": [
                    {
                        "content": "Mahsulotlar konstruktori talablari ishlab chiqildi;",
                        "period_text": "6-noyabr – 24-noyabr",
                        "note": "Mahsulotlar",
                    },
                    {
                        "content": "Sinov va joylashtirish nazorat qilindi;",
                        "period_text": "23-oktabr – 26-noyabr",
                    },
                ]
            },
        )
        assert r.status_code == 200, r.text
        r = self.c.post(
            f"{MY}/{act['id']}/attachments",
            headers=self.contractor,
            data={"caption": "Tahlil paneli", "url": "https://admin.yoshlarfondi.uz/dashboard"},
            files=png(),
        )
        assert r.status_code == 200, r.text
        return data(r)

    def submit(self, act_id: int) -> dict:
        r = self.c.post(
            f"{MY}/{act_id}/submit",
            headers=self.contractor,
            json={"code": code(self.contractor_me)},
        )
        assert r.status_code == 200, r.text
        return data(r)

    def cleanup(self) -> None:
        if not self.contract_ids:
            return

        async def run(session):
            await session.execute(
                text("DELETE FROM acts WHERE contract_id = ANY(:ids) RETURNING id"),
                {"ids": self.contract_ids},
            )
            await session.execute(
                text("DELETE FROM contracts WHERE id = ANY(:ids)"), {"ids": self.contract_ids}
            )

        db_run(run)


@pytest.fixture
def team(api, role_ids):
    helper = Team(api, role_ids)
    try:
        yield helper
    finally:
        helper.cleanup()


# ---------- договоры ----------


def test_contract_validation_and_access(team):
    c = team.c
    base = {
        "number": "TEST-x",
        "signed_on": "2026-10-01",
        "subject": "Loyihani boshqarish xizmatlari",
        "start_date": "2026-10-01",
        "end_date": "2026-12-31",
    }
    # Исполнитель — не CONTRACTOR, руководитель — без права подписи.
    r = c.post(
        CONTRACTS,
        headers=team.reviewer,
        json={
            **base,
            "contractor_id": team.reviewer_me["id"],
            "approver_id": team.approver_me["id"],
        },
    )
    assert r.status_code == 400 and r.json()["code"] == "contract_contractor", r.text
    r = c.post(
        CONTRACTS,
        headers=team.reviewer,
        json={
            **base,
            "contractor_id": team.contractor_me["id"],
            "approver_id": team.contractor_me["id"],
        },
    )
    assert r.status_code == 400 and r.json()["code"] == "contract_approver", r.text
    r = c.post(
        CONTRACTS,
        headers=team.reviewer,
        json={
            **base,
            "end_date": "2026-09-01",
            "contractor_id": team.contractor_me["id"],
            "approver_id": team.approver_me["id"],
        },
    )
    assert r.status_code == 400 and r.json()["code"] == "contract_dates", r.text

    contract = team.contract()
    assert contract["contractor_name"] == "Ahmadjonov Ziyodbek"
    assert contract["approver_name"] == "Quldoshov Mirzobek"
    assert contract["approver_title"] == "ijrochi direktori" and contract["status"] == "ACTIVE"

    r = c.post(
        CONTRACTS,
        headers=team.reviewer,
        json={
            **base,
            "number": contract["number"].lower(),
            "contractor_id": team.contractor_me["id"],
            "approver_id": team.approver_me["id"],
        },
    )
    assert r.status_code == 409 and r.json()["code"] == "contract_number_taken", r.text

    people = data(c.get(f"{CONTRACTS}/people", headers=team.reviewer))
    assert team.contractor_me["id"] in {p["id"] for p in people["contractors"]}
    assert team.approver_me["id"] in {p["id"] for p in people["approvers"]}

    # Исполнитель не видит договоры Фонда, но видит свои.
    assert c.get(CONTRACTS, headers=team.contractor).status_code == 403
    mine = data(c.get("/api/v1/my/contracts", headers=team.contractor))["items"]
    assert [x["id"] for x in mine] == [contract["id"]]
    assert c.get(FUND, headers=team.contractor).status_code == 403


def test_contractor_role_is_staff(team):
    me = data(team.c.get("/api/v1/auth/me", headers=team.contractor))
    assert me["role"]["code"] == "CONTRACTOR" and me["is_staff"] is True
    assert {"acts.create", "acts.read", "acts.update", "acts.delete"} <= set(me["permissions"])


# ---------- полный путь ----------


def test_act_signing_flow(team):
    c = team.c
    contract = team.contract()

    r = c.post(
        MY,
        headers=team.contractor,
        json={
            "contract_id": contract["id"],
            "period_from": "2026-09-20",
            "period_to": "2026-10-10",
        },
    )
    assert r.status_code == 400 and r.json()["code"] == "act_period", r.text

    act = team.draft(contract["id"])
    aid = act["id"]
    assert act["status"] == "DRAFT" and act["number"].startswith("DAL-2026-")
    assert act["intro"] == contract["subject"] and act["act_date"] == "2026-11-26"
    assert act["actions"]["submit"] and act["actions"]["delete"]

    check = data(c.get(f"{MY}/{aid}/submission-check", headers=team.contractor))
    assert check == {"ready": False, "missing": ["items"]}
    r = c.post(
        f"{MY}/{aid}/submit", headers=team.contractor, json={"code": code(team.contractor_me)}
    )
    assert r.status_code == 400 and r.json()["code"] == "act_not_ready", r.text

    act = team.ready_draft(contract["id"], period=("2026-12-01", "2026-12-20"))
    aid = act["id"]
    assert act["items_count"] == 2 and act["attachments_count"] == 1
    assert act["attachments"][0]["sha256"] == hashlib.sha256(png_bytes()).hexdigest()

    # Фонд черновик не видит; чужой ключ не подходит.
    assert c.get(f"{FUND}/{aid}", headers=team.reviewer).status_code == 404
    r = c.post(f"{MY}/{aid}/submit", headers=team.contractor, json={"code": code(team.approver_me)})
    assert r.status_code == 403 and r.json()["code"] == "eimzo_signer_mismatch", r.text

    draft_pdf = c.get(f"{MY}/{aid}/pdf", headers=team.contractor)
    assert draft_pdf.status_code == 200 and draft_pdf.content.startswith(b"%PDF")

    act = team.submit(aid)
    assert act["status"] == "SUBMITTED" and len(act["content_hash"]) == 64
    assert [s["role"] for s in act["signatures"]] == ["CONTRACTOR"]
    assert act["actions"]["withdraw"] and not act["actions"]["edit"]
    r = c.put(f"{MY}/{aid}/items", headers=team.contractor, json={"items": []})
    assert r.status_code == 400 and r.json()["code"] == "act_not_editable"

    to_review = data(c.get(f"{FUND}?tab=to_review&per_page=100", headers=team.reviewer))["items"]
    assert aid in {a["id"] for a in to_review}
    detail = data(c.get(f"{FUND}/{aid}", headers=team.reviewer))
    assert (
        detail["actions"]["accept"]
        and detail["actions"]["send_back"]
        and not detail["actions"]["sign"]
    )

    # Подписать можно только принятый акт и только руководителю по договору.
    r = c.post(f"{FUND}/{aid}/sign", headers=team.approver, json={"code": code(team.approver_me)})
    assert r.status_code == 400 and r.json()["code"] == "act_status", r.text
    r = c.post(f"{FUND}/{aid}/accept", headers=team.reviewer)
    assert r.status_code == 200 and data(r)["status"] == "ACCEPTED", r.text
    r = c.post(f"{FUND}/{aid}/sign", headers=team.reviewer, json={"code": code(team.reviewer_me)})
    assert r.status_code == 403 and r.json()["code"] == "act_not_approver", r.text

    counters = data(c.get(f"{FUND}/counters", headers=team.approver))
    assert counters["to_sign_mine"] >= 1
    mine = data(c.get(f"{FUND}?mine=true&tab=to_sign&per_page=100", headers=team.approver))["items"]
    assert aid in {a["id"] for a in mine}

    r = c.post(f"{FUND}/{aid}/sign", headers=team.approver, json={"code": code(team.approver_me)})
    assert r.status_code == 200, r.text
    signed = data(r)
    assert signed["status"] == "SIGNED" and signed["signed_at"]
    assert [s["role"] for s in signed["signatures"]] == ["CONTRACTOR", "APPROVER"]
    assert len(signed["final_pdf_sha256"]) == 64
    assert not any(signed["actions"].values())

    pdf = c.get(f"{FUND}/{aid}/pdf", headers=team.reviewer)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert hashlib.sha256(pdf.content).hexdigest() == signed["final_pdf_sha256"]
    # Подписанный PDF не пересобирается.
    again = c.get(f"{MY}/{aid}/pdf", headers=team.contractor)
    assert again.content == pdf.content

    public_id = signed["verify_url"].rsplit("/", 1)[1]
    verify = data(c.get(f"/api/v1/public/acts/{public_id}"))
    assert verify["validity"] == "VALID" and verify["content_unchanged"] is True
    assert verify["pdf_sha256"] == signed["final_pdf_sha256"] and len(verify["signatures"]) == 2
    assert "items" not in verify
    page = c.get(f"/acts/verify/{public_id}")
    assert page.status_code == 200 and "DAL-2026-" in page.text
    assert c.get("/acts/verify/unknown").status_code == 404

    # Подписанный акт закрыт для любых действий.
    r = c.post(f"{FUND}/{aid}/cancel", headers=team.reviewer, json={"reason": "TEST reason"})
    assert r.status_code == 400 and r.json()["code"] == "act_status"

    events = [e["event"] for e in signed["events"]]
    assert events == ["CREATED", "SUBMITTED", "ACCEPTED", "SIGNED"]


def test_return_withdraw_overlap_and_cancel(team):
    c = team.c
    contract = team.contract()
    act = team.ready_draft(contract["id"], period=("2026-10-01", "2026-10-31"))
    aid = act["id"]

    # Пересечение периодов внутри договора.
    r = c.post(
        MY,
        headers=team.contractor,
        json={
            "contract_id": contract["id"],
            "period_from": "2026-10-20",
            "period_to": "2026-11-05",
        },
    )
    assert r.status_code == 409 and r.json()["code"] == "act_period_overlap", r.text

    # Отзыв до проверки возвращает черновик без подписи.
    team.submit(aid)
    r = c.post(f"{MY}/{aid}/withdraw", headers=team.contractor)
    assert r.status_code == 200 and data(r)["status"] == "DRAFT" and data(r)["signatures"] == []

    # Возврат проверяющим снимает подпись, исполнитель правит и подписывает заново.
    team.submit(aid)
    r = c.post(
        f"{FUND}/{aid}/return", headers=team.reviewer, json={"comment": "Skrinshotlarni yangilang"}
    )
    assert r.status_code == 200, r.text
    returned = data(r)
    assert returned["status"] == "RETURNED" and returned["signatures"] == []
    assert returned["return_comment"] == "Skrinshotlarni yangilang"
    mine = data(c.get(f"{MY}/{aid}", headers=team.contractor))
    assert mine["actions"]["edit"] and mine["return_comment"]
    r = c.patch(
        f"{MY}/{aid}",
        headers=team.contractor,
        json={"appendix_title": "Ilova: yangilangan skrinshotlar"},
    )
    assert r.status_code == 200, r.text
    resubmitted = team.submit(aid)
    assert resubmitted["status"] == "SUBMITTED" and resubmitted["return_comment"] is None

    # Руководитель тоже может вернуть принятый акт по своему договору.
    c.post(f"{FUND}/{aid}/accept", headers=team.reviewer)
    r = c.post(f"{FUND}/{aid}/return", headers=team.approver, json={"comment": "Sanani tuzating"})
    assert r.status_code == 200 and data(r)["status"] == "RETURNED", r.text

    # Пока по договору есть отправленный акт, реквизиты договора заблокированы.
    team.submit(aid)
    r = c.patch(f"{CONTRACTS}/{contract['id']}", headers=team.reviewer, json={"number": "TEST-new"})
    assert r.status_code == 409 and r.json()["code"] == "contract_in_use", r.text
    r = c.patch(f"{CONTRACTS}/{contract['id']}", headers=team.reviewer, json={"amount": "1000000"})
    assert r.status_code == 200 and data(r)["amount"] in ("1000000", "1000000.00"), r.text
    assert c.delete(f"{CONTRACTS}/{contract['id']}", headers=team.reviewer).status_code == 409

    r = c.post(f"{FUND}/{aid}/cancel", headers=team.reviewer, json={"reason": "TEST bekor"})
    assert r.status_code == 200 and data(r)["status"] == "CANCELLED", r.text
    public_id = data(r)["verify_url"].rsplit("/", 1)[1]
    assert data(c.get(f"/api/v1/public/acts/{public_id}"))["validity"] == "CANCELLED"

    # Отменённый акт не держит период: можно составить новый.
    team.draft(contract["id"], period=("2026-10-01", "2026-10-31"))


def test_copy_from_previous_and_delete_draft(team):
    c = team.c
    contract = team.contract()
    first = team.ready_draft(contract["id"], period=("2026-10-01", "2026-10-31"))
    copy = team.draft(contract["id"], period=("2026-11-01", "2026-11-30"), copy_from_id=first["id"])
    assert [i["content"] for i in copy["items"]] == [i["content"] for i in first["items"]]
    assert copy["attachments"] == [] and copy["act_date"] == "2026-11-30"

    r = c.delete(f"{MY}/{copy['id']}", headers=team.contractor)
    assert r.status_code == 200, r.text
    assert c.get(f"{MY}/{copy['id']}", headers=team.contractor).status_code == 404


def test_closed_contract_and_foreign_acts(api, team, role_ids):
    c = team.c
    contract = team.contract()
    act = team.draft(contract["id"], period=("2026-10-01", "2026-10-10"))

    # Другой исполнитель не видит чужой акт и не может писать по чужому договору.
    other, _ = Team._login(api, role_ids["CONTRACTOR"], "TEST OTHER")
    assert c.get(f"{MY}/{act['id']}", headers=other).status_code == 404
    r = c.post(
        MY,
        headers=other,
        json={
            "contract_id": contract["id"],
            "period_from": "2026-11-01",
            "period_to": "2026-11-02",
        },
    )
    assert r.status_code == 404 and r.json()["code"] == "contract_not_found", r.text

    r = c.patch(f"{CONTRACTS}/{contract['id']}", headers=team.reviewer, json={"status": "CLOSED"})
    assert data(r)["status"] == "CLOSED"
    r = c.post(
        MY,
        headers=team.contractor,
        json={
            "contract_id": contract["id"],
            "period_from": "2026-11-01",
            "period_to": "2026-11-02",
        },
    )
    assert r.status_code == 400 and r.json()["code"] == "contract_closed", r.text
    check = data(c.get(f"{MY}/{act['id']}/submission-check", headers=team.contractor))
    assert "contract" in check["missing"]


def test_attachment_rules(team):
    c = team.c
    contract = team.contract()
    act = team.draft(contract["id"], period=("2026-10-01", "2026-10-10"))
    aid = act["id"]
    r = c.post(
        f"{MY}/{aid}/attachments",
        headers=team.contractor,
        data={"caption": "PDF emas"},
        files={"file": ("a.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert r.status_code == 400 and r.json()["code"] == "invalid_photo", r.text
    ids = []
    for n in range(2):
        r = c.post(
            f"{MY}/{aid}/attachments",
            headers=team.contractor,
            data={"caption": f"S{n}"},
            files=png(),
        )
        ids.append(data(r)["attachments"][-1]["id"])
    r = c.put(f"{MY}/{aid}/attachments/order", headers=team.contractor, json={"ids": ids[::-1]})
    assert [a["caption"] for a in data(r)["attachments"]] == ["S1", "S0"]
    r = c.patch(
        f"{MY}/{aid}/attachments/{ids[0]}", headers=team.contractor, json={"caption": "Yangi"}
    )
    assert data(r)["attachments"][1]["caption"] == "Yangi"
    file = c.get(f"{MY}/{aid}/attachments/{ids[0]}", headers=team.contractor)
    assert file.status_code == 200 and file.content == png_bytes()
    r = c.delete(f"{MY}/{aid}/attachments/{ids[0]}", headers=team.contractor)
    assert [a["id"] for a in data(r)["attachments"]] == [ids[1]]
    assert date.fromisoformat(act["period_from"]) == date(2026, 10, 1)
