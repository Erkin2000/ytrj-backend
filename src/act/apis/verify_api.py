"""Публичная проверка акта выполненных работ по QR-коду (без авторизации).

- ``GET /api/v1/public/acts/{public_id}`` — данные проверки (JSON);
- ``GET /acts/verify/{public_id}`` — веб-страница, на которую ведёт QR (ACT_VERIFY_BASE_URL).

Показываются номер, период, стороны, кто и когда подписал (с серийным номером
сертификата), совпадает ли содержимое с подписанным и SHA-256 итогового PDF.
Строки работ и скриншоты не раскрываются. Черновики не проверяются (404).
"""

from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from src.act.apis.examples import VERIFY
from src.act.services.act_service import ActService
from src.bulletin.enums import TASHKENT_TZ
from src.common.dependencies import DBDep
from src.common.responses.exceptions import ActNotFoundException
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import PUBLIC_ERRORS, error_examples, success_example

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

api_router = APIRouter(prefix="/public/acts", tags=["Акты выполненных работ: проверка по QR"])
web_router = APIRouter(prefix="/acts/verify", include_in_schema=False)


@api_router.get(
    "/{public_id}",
    summary="Проверка акта по QR: стороны, подписи и неизменность содержимого",
    description=(
        "Публичная ручка без авторизации. `validity`: `VALID` — подписан руководителем и не "
        "менялся, `NOT_SIGNED` — ещё не подписан, `CANCELLED` — аннулирован, `MODIFIED` — "
        "содержимое не совпадает с подписанным. Неизвестный `public_id` или черновик — 404."
    ),
    responses={
        200: success_example(VERIFY, "Act verified."),
        **PUBLIC_ERRORS,
        404: error_examples(ActNotFoundException),
    },
)
async def verify_act(public_id: str, db: DBDep):
    data = await ActService(db).verify(public_id)
    return ResponseBuilder.success(data=data, message="Act verified.")


STATUSES = {
    "uz": {
        "SUBMITTED": "Ijrochi imzolagan, tekshiruvda",
        "ACCEPTED": "Qabul qilingan, rahbar imzosi kutilmoqda",
        "SIGNED": "Rahbar tomonidan imzolangan",
        "RETURNED": "Qayta ishlashga qaytarilgan",
        "CANCELLED": "Bekor qilingan",
        "DRAFT": "Qoralama",
    },
    "ru": {
        "SUBMITTED": "Подписан исполнителем, на проверке",
        "ACCEPTED": "Принят, ждёт подписи руководителя",
        "SIGNED": "Подписан руководителем",
        "RETURNED": "Возвращён на доработку",
        "CANCELLED": "Аннулирован",
        "DRAFT": "Черновик",
    },
}

LABELS = {
    "uz": {
        "title": "Hujjatni tekshirish",
        "document_type": "Bajarilgan ishlarni qabul qilish va topshirish dalolatnomasi",
        "status": "Holati",
        "date": "Dalolatnoma sanasi",
        "period": "Ishlar davri",
        "contract": "Shartnoma",
        "contractor": "Ijrochi",
        "approver": "Buyurtmachi (rahbar)",
        "content": "Mazmuni",
        "unchanged": "Imzolangandan keyin oʻzgarmagan",
        "not_confirmed": "Tasdiqlanmagan",
        "pdf_hash": "PDF SHA-256",
        "signatures": "Elektron imzolar (E-IMZO)",
        "certificate": "sertifikat",
        "no_signatures": "Imzolar yoʻq",
        "roles": {"CONTRACTOR": "Topshiruvchi", "APPROVER": "Qabul qiluvchi"},
        "valid": "Hujjat haqiqiy",
        "validity": {
            "NOT_SIGNED": "Hujjat hali rahbar tomonidan imzolanmagan",
            "CANCELLED": "Bekor qilingan",
            "MODIFIED": "Mazmuni imzolangan nusxaga mos emas",
        },
        "not_found": "Hujjatni tasdiqlab boʻlmaydi",
        "not_found_text": "Bunday identifikatorli hujjat topilmadi.",
        "statuses": STATUSES["uz"],
    },
    "ru": {
        "title": "Проверка документа",
        "document_type": "Акт приёма-передачи выполненных работ",
        "status": "Статус",
        "date": "Дата акта",
        "period": "Период работ",
        "contract": "Договор",
        "contractor": "Исполнитель",
        "approver": "Заказчик (руководитель)",
        "content": "Содержимое",
        "unchanged": "Не менялось после подписи",
        "not_confirmed": "Не подтверждено",
        "pdf_hash": "SHA-256 PDF",
        "signatures": "Электронные подписи (E-IMZO)",
        "certificate": "сертификат",
        "no_signatures": "Подписей нет",
        "roles": {"CONTRACTOR": "Сдал", "APPROVER": "Принял"},
        "valid": "Документ действителен",
        "validity": {
            "NOT_SIGNED": "Документ ещё не подписан руководителем",
            "CANCELLED": "Аннулирован",
            "MODIFIED": "Содержимое не совпадает с подписанным",
        },
        "not_found": "Подтвердить документ невозможно",
        "not_found_text": "Документ с таким идентификатором не найден.",
        "statuses": STATUSES["ru"],
    },
}


def local_time(value) -> str:
    return value.astimezone(TASHKENT_TZ).strftime("%d.%m.%Y %H:%M") if value else ""


@web_router.get("/{public_id}")
async def verify_page(
    public_id: str, request: Request, db: DBDep, lang: str = Query("uz", pattern="^(uz|ru)$")
):
    try:
        document = await ActService(db).verify(public_id)
    except ActNotFoundException:
        document = None
    return templates.TemplateResponse(
        request,
        "act_verify.html",
        {
            "doc": document,
            "t": LABELS[lang],
            "lang": lang,
            "other_lang": "ru" if lang == "uz" else "uz",
            "local_time": local_time,
        },
        status_code=200 if document else 404,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
