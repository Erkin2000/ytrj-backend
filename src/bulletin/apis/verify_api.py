"""Публичная проверка бюллетеня по QR-коду (без авторизации).

- ``GET /api/v1/public/bulletins/{public_id}`` — данные проверки (JSON) для фронтенда;
- ``GET /bulletins/verify/{public_id}`` — готовая веб-страница, на которую ведёт QR
  по умолчанию (BULLETIN_VERIFY_BASE_URL).

Показываются название, описание, дата бюллетеня, данные прикреплённого файла
(имя, тип, размер, SHA-256 — по нему можно сверить имеющийся файл), кто из членов
Совета подписал, а кто нет, и статус. Сам файл, решения и время подписи не раскрываются.
"""

from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from src.bulletin.apis.examples import VERIFY
from src.bulletin.services.bulletin_service import BulletinService
from src.common.dependencies import DBDep
from src.common.responses.exceptions import BulletinNotFoundException
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import PUBLIC_ERRORS, error_examples, success_example

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

api_router = APIRouter(prefix="/public/bulletins", tags=["Бюллетени: проверка по QR"])
web_router = APIRouter(prefix="/bulletins/verify", include_in_schema=False)


@api_router.get(
    "/{public_id}",
    summary="Проверка бюллетеня по QR: данные документа, кто подписал и статус",
    description=(
        "Публичная ручка без авторизации. `validity`: `VALID` — документ действителен, "
        "`CANCELLED` — аннулирован. Неизвестный `public_id` — 404."
    ),
    responses={
        200: success_example(VERIFY, "Bulletin verified."),
        **PUBLIC_ERRORS,
        404: error_examples(BulletinNotFoundException),
    },
)
async def verify_bulletin(public_id: str, db: DBDep):
    data = await BulletinService(db).verify(public_id)
    return ResponseBuilder.success(data=data, message="Bulletin verified.")


LABELS = {
    "uz": {
        "title": "Hujjatni tekshirish",
        "document_type": "Kengash aʼzosi byulleteni",
        "number": "Byulleten raqami",
        "date": "Byulleten sanasi",
        "status": "Holati",
        "description": "Tavsif",
        "file": "Biriktirilgan fayl",
        "file_name": "Nomi",
        "file_type": "Turi",
        "file_size": "Hajmi",
        "file_hash": "SHA-256",
        "no_file": "Fayl biriktirilmagan",
        "signers": "Kengash aʼzolari",
        "signed": "Imzolagan",
        "not_signed": "Imzolamagan",
        "no_signers": "Byulleten hali Kengash aʼzolariga yuborilmagan",
        "valid": "Hujjat haqiqiy",
        "cancelled": "Bekor qilingan",
        "not_found": "Hujjatni tasdiqlab boʻlmaydi",
        "not_found_text": "Bunday identifikatorli hujjat topilmadi.",
        "progress": "Imzolar",
        "statuses": {
            "PENDING": "Yuborish kutilmoqda",
            "PUBLISHED": "Kengash aʼzolariga yuborilgan",
            "PARTIALLY_SIGNED": "Qisman imzolangan",
            "COMPLETED": "Barcha aʼzolar imzolagan",
            "CANCELLED": "Bekor qilingan",
        },
    },
    "ru": {
        "title": "Проверка документа",
        "document_type": "Бюллетень члена Совета",
        "number": "Номер бюллетеня",
        "date": "Дата бюллетеня",
        "status": "Статус",
        "description": "Описание",
        "file": "Прикреплённый файл",
        "file_name": "Имя",
        "file_type": "Тип",
        "file_size": "Размер",
        "file_hash": "SHA-256",
        "no_file": "Файл не прикреплён",
        "signers": "Члены Совета",
        "signed": "Подписал",
        "not_signed": "Не подписал",
        "no_signers": "Бюллетень ещё не отправлен членам Совета",
        "valid": "Документ действителен",
        "cancelled": "Аннулирован",
        "not_found": "Подтвердить документ невозможно",
        "not_found_text": "Документ с таким идентификатором не найден.",
        "progress": "Подписи",
        "statuses": {
            "PENDING": "Ожидает отправки",
            "PUBLISHED": "Отправлен членам Совета",
            "PARTIALLY_SIGNED": "Подписан частично",
            "COMPLETED": "Подписан всеми членами",
            "CANCELLED": "Аннулирован",
        },
    },
}


def human_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


@web_router.get("/{public_id}")
async def verify_page(
    public_id: str, request: Request, db: DBDep, lang: str = Query("uz", pattern="^(uz|ru)$")
):
    labels = LABELS[lang]
    try:
        document = await BulletinService(db).verify(public_id)
    except BulletinNotFoundException:
        document = None
    return templates.TemplateResponse(
        request,
        "bulletin_verify.html",
        {
            "doc": document,
            "t": labels,
            "lang": lang,
            "other_lang": "ru" if lang == "uz" else "uz",
            "human_size": human_size,
        },
        status_code=200 if document else 404,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
