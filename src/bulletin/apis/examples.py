"""Примеры ответов бюллетеней для документации."""

APPLICATION = {
    "id": 12,
    "number": "JG-2026-000012",
    "status": "COUNCIL_REVIEW",
    "applicant_full_name": "Aliyev Ali Aliyevich",
    "url": "/api/v1/fund/applications/12",
}

SUMMARY = {"total": 5, "signed": 2, "pending": 3, "agree": 2, "against": 0}

FILE = {
    "name": "byulleten-46.pdf",
    "content_type": "application/pdf",
    "size": 248133,
    "sha256": "9f2c4e1b7a0d3c5e8f1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f70",
    "url": "/api/v1/fund/bulletins/7/file",
}

LIST_ITEM = {
    "id": 7,
    "number": "BYU-2026-000007",
    "name": "Kengash majlisi №46",
    "status": "PARTIALLY_SIGNED",
    "send_at": "2026-11-20T05:00:00Z",
    "published_at": "2026-11-20T05:00:00Z",
    "deadline_at": "2026-11-27T13:00:00Z",
    "is_overdue": False,
    "has_file": True,
    "application": APPLICATION,
    "signatures": SUMMARY,
    "created_at": "2026-11-18T09:30:00Z",
}

CERTIFICATE = {
    "pinfl": "31234567890123",
    "full_name": "VALIYEV ALI KARIMOVICH",
    "serial_number": "7a1b2c3d",
    "valid_from": "2026.01.10 10:00:00",
    "valid_to": "2028.01.10 23:59:59",
}

DETAIL = {
    **LIST_ITEM,
    "public_id": "Jk3s9QwErTy0uIoPaSdFgHjKl1zXcVbN",
    "description": "Kun tartibi: grant ajratish toʻgʻrisida.",
    "file": FILE,
    "signature_list": [
        {
            "id": 31,
            "member": {
                "id": 41,
                "full_name": "Valiyev Ali Karimovich",
                "username": "council_valiyev",
            },
            "member_full_name": "Valiyev Ali Karimovich",
            "status": "SIGNED",
            "viewed_at": "2026-11-20T06:10:00Z",
            "file_viewed_at": "2026-11-20T06:11:00Z",
            "decision": "AGREE",
            "comment": None,
            "signed_at": "2026-11-20T06:15:00Z",
            "certificate": CERTIFICATE,
            "document_hash": "4be1f0c2d3a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e",
        },
        {
            "id": 32,
            "member": {"id": 42, "full_name": "Karimova Nodira", "username": "council_karimova"},
            "member_full_name": "Karimova Nodira",
            "status": "NEW",
            "viewed_at": None,
            "file_viewed_at": None,
            "decision": None,
            "comment": None,
            "signed_at": None,
            "certificate": None,
            "document_hash": None,
        },
    ],
    "created_by": {"id": 5, "full_name": "Fund Operator", "username": "fund1"},
    "completed_at": None,
    "cancelled_at": None,
    "cancelled_by": None,
    "cancel_reason": None,
    "verify_url": "https://yoshlarfondi.uz/bulletins/verify/Jk3s9QwErTy0uIoPaSdFgHjKl1zXcVbN",
    "qr_url": "/api/v1/fund/bulletins/7/qr",
}

COUNCIL_ITEM = {
    "id": 7,
    "number": "BYU-2026-000007",
    "name": "Kengash majlisi №46",
    "status": "PUBLISHED",
    "published_at": "2026-11-20T05:00:00Z",
    "deadline_at": "2026-11-27T13:00:00Z",
    "has_file": True,
    "application": {**APPLICATION, "url": "/api/v1/applications/12"},
    "my_status": "NEW",
    "my_decision": None,
    "signed_at": None,
}

COUNCIL_DETAIL = {
    **COUNCIL_ITEM,
    "my_status": "VIEWED",
    "description": "Kun tartibi: grant ajratish toʻgʻrisida.",
    "file": {**FILE, "url": "/api/v1/council/bulletins/7/file"},
    "created_at": "2026-11-18T09:30:00Z",
    "my": {
        "status": "VIEWED",
        "viewed_at": "2026-11-20T06:10:00Z",
        "file_viewed_at": None,
        "decision": None,
        "comment": None,
        "signed_at": None,
        "certificate": None,
        "can_sign": False,
        "sign_blockers": ["bulletin_file_not_viewed"],
    },
    "verify_url": "https://yoshlarfondi.uz/bulletins/verify/Jk3s9QwErTy0uIoPaSdFgHjKl1zXcVbN",
}

CALENDAR = [
    {
        "date": "2026-11-20",
        "events": [
            {
                "type": "SEND",
                "at": "2026-11-20T05:00:00Z",
                "bulletin_id": 7,
                "number": "BYU-2026-000007",
                "name": "Kengash majlisi №46",
                "status": "PUBLISHED",
                "my_status": "NEW",
            }
        ],
    },
    {
        "date": "2026-11-27",
        "events": [
            {
                "type": "DEADLINE",
                "at": "2026-11-27T13:00:00Z",
                "bulletin_id": 7,
                "number": "BYU-2026-000007",
                "name": "Kengash majlisi №46",
                "status": "PUBLISHED",
                "my_status": "NEW",
            }
        ],
    },
]

VERIFY = {
    "document_type": "Kengash aʼzosi byulleteni",
    "number": "BYU-2026-000007",
    "name": "Kengash majlisi №46",
    "description": "Kun tartibi: grant ajratish toʻgʻrisida.",
    "bulletin_date": "2026-11-18",
    "status": "PARTIALLY_SIGNED",
    "validity": "VALID",
    "file": {**FILE, "url": None},
    "signers": [
        {"full_name": "Valiyev Ali Karimovich", "signed": True},
        {"full_name": "Karimova Nodira", "signed": False},
    ],
    "signed_count": 1,
    "total_count": 2,
}
