"""Примеры ответов для документации."""

PERSON = {"id": 41, "full_name": "AHMADJONOV ZIYODBEK MURODJON O‘G‘LI"}
APPROVER = {"id": 7, "full_name": "QULDOSHOV MIRZOBEK BERUNIY O‘G‘LI"}

CONTRACT = {
    "id": 3,
    "number": "12/2026",
    "signed_on": "2026-10-01",
    "contractor": PERSON,
    "contractor_name": "Ahmadjonov Ziyodbek",
    "position": "Loyiha menejeri (PM)",
    "subject": "YTRJ-EP moliyalashtirish modulini ishlab chiqish loyihasini boshqarish",
    "start_date": "2026-10-01",
    "end_date": "2026-12-31",
    "amount": "15000000.00",
    "approver": APPROVER,
    "approver_name": "Quldoshov Mirzobek",
    "approver_title": "ijrochi direktori",
    "status": "ACTIVE",
    "acts_count": 2,
    "created_at": "2026-10-01T09:00:00+05:00",
}

CONTRACT_SHORT = {
    "id": 3,
    "number": "12/2026",
    "signed_on": "2026-10-01",
    "contractor_name": "Ahmadjonov Ziyodbek",
    "position": "Loyiha menejeri (PM)",
    "approver_name": "Quldoshov Mirzobek",
}

LIST_ITEM = {
    "id": 15,
    "number": "DAL-2026-000015",
    "status": "SUBMITTED",
    "contract": CONTRACT_SHORT,
    "period_from": "2026-10-23",
    "period_to": "2026-11-26",
    "act_date": "2026-11-26",
    "items_count": 11,
    "attachments_count": 8,
    "submitted_at": "2026-11-26T15:20:00+05:00",
    "accepted_at": None,
    "signed_at": None,
    "returned_at": None,
    "updated_at": "2026-11-26T15:20:00+05:00",
}

SIGNATURE = {
    "role": "CONTRACTOR",
    "signer": PERSON,
    "signer_full_name": "AHMADJONOV ZIYODBEK MURODJON O‘G‘LI",
    "signed_at": "2026-11-26T15:20:00+05:00",
    "cert_full_name": "AHMADJONOV ZIYODBEK MURODJON O‘G‘LI",
    "cert_serial_number": "7a1b2c3d",
    "cert_valid_to": "2028-03-01",
    "document_hash": "3f1c…",
}

DETAIL = {
    **LIST_ITEM,
    "intro": "YTRJ-EP moliyalashtirish modulini ishlab chiqish loyihasini boshqarish",
    "appendix_title": "Ilova: bajarilgan ishlarni tasdiqlovchi skrinshotlar",
    "return_comment": None,
    "cancel_reason": None,
    "cancelled_at": None,
    "content_hash": "9b2e…",
    "final_pdf_sha256": None,
    "items": [
        {
            "id": 101,
            "position": 0,
            "content": "Mahsulotlar konstruktori talablari ishlab chiqildi;",
            "period_text": "6-noyabr – 24-noyabr",
            "note": "Mahsulotlar",
        }
    ],
    "attachments": [
        {
            "id": 55,
            "position": 0,
            "caption": "Tahlil paneli",
            "url": "https://admin.yoshlarfondi.uz/dashboard",
            "file_name": "dashboard.png",
            "content_type": "image/png",
            "size": 245112,
            "sha256": "c0ffee…",
        }
    ],
    "signatures": [SIGNATURE],
    "events": [
        {
            "event": "SUBMITTED",
            "from_status": "DRAFT",
            "to_status": "SUBMITTED",
            "actor": PERSON,
            "actor_name": "AHMADJONOV ZIYODBEK MURODJON O‘G‘LI",
            "comment": None,
            "created_at": "2026-11-26T15:20:00+05:00",
        }
    ],
    "verify_url": "https://api.yoshlarfondi.uz/acts/verify/Qm3…",
    "actions": {
        "edit": False,
        "delete": False,
        "submit": False,
        "withdraw": True,
        "accept": False,
        "send_back": False,
        "sign": False,
        "cancel": False,
    },
}

FUND_COUNTERS = {
    "submitted": 3,
    "accepted": 1,
    "signed": 12,
    "returned": 1,
    "cancelled": 0,
    "to_sign_mine": 1,
}

MY_COUNTERS = {
    "draft": 1,
    "submitted": 1,
    "accepted": 0,
    "signed": 2,
    "returned": 0,
    "cancelled": 0,
}

PEOPLE = {"contractors": [PERSON], "approvers": [APPROVER]}

CHECK = {"ready": False, "missing": ["items"]}

VERIFY = {
    "number": "DAL-2026-000015",
    "status": "SIGNED",
    "validity": "VALID",
    "contract_number": "12/2026",
    "contract_signed_on": "2026-10-01",
    "contractor_name": "Ahmadjonov Ziyodbek",
    "approver_name": "Quldoshov Mirzobek",
    "period_from": "2026-10-23",
    "period_to": "2026-11-26",
    "act_date": "2026-11-26",
    "signatures": [
        {
            "role": "CONTRACTOR",
            "name": "AHMADJONOV ZIYODBEK MURODJON O‘G‘LI",
            "signed_at": "2026-11-26T15:20:00+05:00",
            "cert_serial_number": "7a1b2c3d",
        }
    ],
    "content_unchanged": True,
    "pdf_sha256": "ab12…",
}
