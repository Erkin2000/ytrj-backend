"""Хэши того, что подписано.

`content_hash` — SHA-256 канонического JSON содержимого акта: договор, стороны, период,
вводная часть, строки таблицы и SHA-256 каждого файла приложения. Его фиксирует подпись
исполнителя, и с ним сверяется акт при принятии, подписи руководителя и проверке по QR.

`signature_hash` — SHA-256 подписи: хэш содержимого, роль, ПИНФЛ подписанта и время;
у руководителя — ещё хэш подписи исполнителя (цепочка: руководитель утверждает именно
то, что подписал исполнитель).
"""

import hashlib
import json
from datetime import datetime

from src.act.models.act_model import ActORM


def _sha256(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def content_hash(act: ActORM) -> str:
    contract = act.contract
    return _sha256(
        {
            "act": {
                "number": act.number,
                "public_id": act.public_id,
                "period_from": act.period_from.isoformat(),
                "period_to": act.period_to.isoformat(),
                "act_date": act.act_date.isoformat(),
                "intro": act.intro,
                "appendix_title": act.appendix_title,
            },
            "contract": {
                "number": contract.number,
                "signed_on": contract.signed_on.isoformat(),
                "contractor_name": contract.contractor_name,
                "approver_name": contract.approver_name,
                "approver_title": contract.approver_title,
            },
            "items": [
                {"content": i.content, "period_text": i.period_text, "note": i.note}
                for i in act.items
            ],
            "attachments": [
                {"caption": a.caption, "url": a.url, "sha256": a.sha256} for a in act.attachments
            ],
        }
    )


def signature_hash(
    content: str,
    role: str,
    pinfl: str,
    signed_at: datetime,
    previous: str | None = None,
) -> str:
    return _sha256(
        {
            "content_hash": content,
            "role": role,
            "signer_pinfl": pinfl,
            "signed_at": signed_at.isoformat(),
            "previous_signature": previous,
        }
    )
