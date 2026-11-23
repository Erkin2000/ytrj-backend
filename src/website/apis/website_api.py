"""Контент сайта: события, «О нас», члены Совета, руководство и контакты.

Публичные ручки — без авторизации, для сайта; ручки `/marketing/...` — для отдела
маркетинга (права events.*, about.*, council_profiles.*, leadership.*, contacts.*).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    AboutSectionNotFoundException,
    CouncilProfileNotFoundException,
    EventCalendarRangeException,
    EventNotFoundException,
    EventPhotoNotFoundException,
    InvalidPhotoException,
    LeadershipProfileNotFoundException,
    PersonPhotoNotFoundException,
    PhotoTooLargeException,
    SiteContactEmptyException,
    SiteContactNotFoundException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    PUBLIC_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.rbac.permissions import Action, Module
from src.website.enums import PersonKind
from src.website.mappers import PERSON_PATHS
from src.website.schemas.website_schema import (
    ABOUT_TRANSLATIONS_EXAMPLE,
    EVENT_TRANSLATIONS_EXAMPLE,
    PERSON_TRANSLATIONS_EXAMPLE,
    AboutCreateDTO,
    AboutUpdateDTO,
    EventCreateForm,
    EventFilterDTO,
    EventUpdateDTO,
    PersonCreateForm,
    PersonUpdateDTO,
    SiteContactCreateDTO,
    SiteContactUpdateDTO,
)
from src.website.services.website_service import (
    AboutService,
    EventService,
    PersonService,
    SiteContactService,
)

AUDIT = {
    "created_by": {"id": 12, "full_name": "Marketing Operator", "username": "marketing1"},
    "updated_by": {"id": 12, "full_name": "Marketing Operator", "username": "marketing1"},
    "created_at": "2026-11-20T09:00:00Z",
    "updated_at": "2026-11-20T09:00:00Z",
}


def perm(module: Module, action: Action):
    return Depends(require_permission(module, action))


# ======================= события =======================

PHOTO = {"name": "portrait.jpg", "content_type": "image/jpeg", "size": 120400}
PHOTO_ERRORS = {400: error_examples(InvalidPhotoException, PhotoTooLargeException)}

EVENT_BASE = {"id": 3, "translations": EVENT_TRANSLATIONS_EXAMPLE, "date": "2026-12-05"}
EVENT_PUBLIC = {**EVENT_BASE, "photo": {"url": "/api/v1/events/3/photo", **PHOTO}}
EVENT = {
    **EVENT_BASE,
    "photo": {"url": "/api/v1/marketing/events/3/photo", **PHOTO},
    "is_active": True,
    **AUDIT,
}
EVENT_NOT_FOUND = {404: error_examples(EventNotFoundException)}
EVENT_PHOTO_NOT_FOUND = {404: error_examples(EventNotFoundException, EventPhotoNotFoundException)}

events_public = APIRouter(prefix="/events", tags=["События: сайт"])
events = APIRouter(prefix="/marketing/events", tags=["События: управление (маркетинг)"])
EventFilterDep = Annotated[EventFilterDTO, Depends()]

CALENDAR_EXAMPLE = [{"date": "2026-12-05", "count": 2}, {"date": "2026-12-18", "count": 1}]
CALENDAR_FROM = Query(None, description="Первый день; по умолчанию — 1-е число текущего месяца.")
CALENDAR_TO = Query(None, description="Последний день включительно; по умолчанию — конец месяца.")
CALENDAR_ERRORS = {400: error_examples(EventCalendarRangeException)}


@events_public.get(
    "/calendar",
    summary="Календарь событий: дни, в которые есть события (точки в календаре)",
    description=(
        "Без авторизации. Возвращает только дни с активными событиями и их число; "
        "дни без событий не приходят. По умолчанию — текущий месяц; диапазон — "
        "не больше 93 дней. События выбранного дня — `GET /events?date=YYYY-MM-DD`."
    ),
    responses={
        200: success_example(CALENDAR_EXAMPLE, "Calendar retrieved."),
        **PUBLIC_ERRORS,
        **CALENDAR_ERRORS,
    },
)
async def get_public_events_calendar(
    db: DBDep, date_from: date | None = CALENDAR_FROM, date_to: date | None = CALENDAR_TO
):
    data = await EventService(db).get_calendar(date_from, date_to, public=True)
    return ResponseBuilder.success(data=data, message="Calendar retrieved.")


@events_public.get(
    "",
    summary="События для сайта (активные), сначала поздние по дате",
    description=(
        "Без авторизации. Фильтр: `date` — события одного дня (клик по дню календаря) "
        "или диапазон `date_from`, `date_to`."
    ),
    responses={200: paginated_example(EVENT_PUBLIC, "Events retrieved."), **PUBLIC_ERRORS},
)
async def get_public_events(db: DBDep, pagination: PaginationDep, filters: EventFilterDep):
    data = await EventService(db).get_page(filters, pagination.page, pagination.per_page, True)
    return ResponseBuilder.success(data=data, message="Events retrieved.")


@events_public.get(
    "/{event_id}",
    summary="Событие для сайта",
    description="Без авторизации. Неактивное событие — 404.",
    responses={
        200: success_example(EVENT_PUBLIC, "Event found."),
        **PUBLIC_ERRORS,
        **EVENT_NOT_FOUND,
    },
)
async def get_public_event(event_id: int, db: DBDep):
    data = await EventService(db).get_public(event_id)
    return ResponseBuilder.success(data=data, message="Event found.")


@events_public.get(
    "/{event_id}/photo",
    summary="Фото события",
    description="Без авторизации.",
    response_class=FileResponse,
    responses=EVENT_PHOTO_NOT_FOUND,
)
async def get_public_event_photo(event_id: int, db: DBDep):
    path, content_type, name = await EventService(db).public_photo(event_id)
    return FileResponse(
        path,
        media_type=content_type,
        filename=name,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@events.get(
    "",
    summary="Все события, включая неактивные",
    dependencies=[perm(Module.EVENTS, Action.READ)],
    responses={200: paginated_example(EVENT, "Events retrieved."), **COMMON_ERRORS},
)
async def get_events(db: DBDep, pagination: PaginationDep, filters: EventFilterDep):
    data = await EventService(db).get_page(filters, pagination.page, pagination.per_page, False)
    return ResponseBuilder.success(data=data, message="Events retrieved.")


@events.get(
    "/calendar",
    summary="Календарь событий для админки: дни с событиями, включая неактивные",
    description="По умолчанию — текущий месяц; диапазон — не больше 93 дней.",
    dependencies=[perm(Module.EVENTS, Action.READ)],
    responses={
        200: success_example(CALENDAR_EXAMPLE, "Calendar retrieved."),
        **COMMON_ERRORS,
        **CALENDAR_ERRORS,
    },
)
async def get_events_calendar(
    db: DBDep, date_from: date | None = CALENDAR_FROM, date_to: date | None = CALENDAR_TO
):
    data = await EventService(db).get_calendar(date_from, date_to, public=False)
    return ResponseBuilder.success(data=data, message="Calendar retrieved.")


@events.post(
    "",
    status_code=201,
    summary="Создать событие (multipart/form-data)",
    description=(
        "Заголовок и текст — на трёх языках: `title_ru`, `title_uz`, `title_en`, "
        "`text_ru`, `text_uz`, `text_en`; `date` — дата события. Необязательно: "
        "`is_active`, `photo` (JPEG / PNG / WEBP)."
    ),
    dependencies=[perm(Module.EVENTS, Action.CREATE)],
    responses={201: success_example(EVENT, "Event created."), **COMMON_ERRORS, **PHOTO_ERRORS},
)
async def create_event(
    db: DBDep,
    user: CurrentUserDep,
    form: Annotated[EventCreateForm, Form(media_type="multipart/form-data")],
):
    event = await EventService(db).create(user, form)
    return ResponseBuilder.success(data=event, message="Event created.", status_code=201)


@events.get(
    "/{event_id}",
    summary="Событие по ID",
    dependencies=[perm(Module.EVENTS, Action.READ)],
    responses={200: success_example(EVENT, "Event found."), **COMMON_ERRORS, **EVENT_NOT_FOUND},
)
async def get_event(event_id: int, db: DBDep):
    data = await EventService(db).get_detail(event_id)
    return ResponseBuilder.success(data=data, message="Event found.")


@events.patch(
    "/{event_id}",
    summary="Изменить переводы, дату или активность события",
    description="Фото — `PUT` / `DELETE /{event_id}/photo`.",
    dependencies=[perm(Module.EVENTS, Action.UPDATE)],
    responses={200: success_example(EVENT, "Event updated."), **COMMON_ERRORS, **EVENT_NOT_FOUND},
)
async def update_event(event_id: int, data: EventUpdateDTO, db: DBDep, user: CurrentUserDep):
    event = await EventService(db).update(user, event_id, data)
    return ResponseBuilder.success(data=event, message="Event updated.")


@events.get(
    "/{event_id}/photo",
    summary="Фото события (в том числе неактивного)",
    dependencies=[perm(Module.EVENTS, Action.READ)],
    response_class=FileResponse,
    responses={**COMMON_ERRORS, **EVENT_PHOTO_NOT_FOUND},
)
async def get_event_photo(event_id: int, db: DBDep):
    path, content_type, name = await EventService(db).photo(event_id)
    return FileResponse(
        path, media_type=content_type, filename=name, content_disposition_type="inline"
    )


@events.put(
    "/{event_id}/photo",
    summary="Загрузить или заменить фото события",
    dependencies=[perm(Module.EVENTS, Action.UPDATE)],
    responses={
        200: success_example(EVENT, "Photo uploaded."),
        **COMMON_ERRORS,
        **EVENT_NOT_FOUND,
        **PHOTO_ERRORS,
    },
)
async def set_event_photo(
    event_id: int,
    db: DBDep,
    user: CurrentUserDep,
    photo: Annotated[UploadFile, File(description="JPEG / PNG / WEBP.")],
):
    data = await EventService(db).set_photo(user, event_id, photo)
    return ResponseBuilder.success(data=data, message="Photo uploaded.")


@events.delete(
    "/{event_id}/photo",
    summary="Удалить фото события",
    dependencies=[perm(Module.EVENTS, Action.UPDATE)],
    responses={
        200: success_example({**EVENT, "photo": None}, "Photo deleted."),
        **COMMON_ERRORS,
        **EVENT_PHOTO_NOT_FOUND,
    },
)
async def delete_event_photo(event_id: int, db: DBDep, user: CurrentUserDep):
    data = await EventService(db).delete_photo(user, event_id)
    return ResponseBuilder.success(data=data, message="Photo deleted.")


@events.delete(
    "/{event_id}",
    summary="Удалить событие вместе с фото",
    dependencies=[perm(Module.EVENTS, Action.DELETE)],
    responses={200: success_example(None, "Event deleted."), **COMMON_ERRORS, **EVENT_NOT_FOUND},
)
async def delete_event(event_id: int, db: DBDep):
    await EventService(db).delete(event_id)
    return ResponseBuilder.success(message="Event deleted.")


# ======================= «О нас» =======================

ABOUT_PUBLIC = {"id": 1, "translations": ABOUT_TRANSLATIONS_EXAMPLE, "sort_order": 0}
ABOUT = {**ABOUT_PUBLIC, "is_active": True, **AUDIT}
ABOUT_NOT_FOUND = {404: error_examples(AboutSectionNotFoundException)}

about_public = APIRouter(prefix="/about", tags=["О нас: сайт"])
about = APIRouter(prefix="/marketing/about", tags=["О нас: управление (маркетинг)"])


@about_public.get(
    "",
    summary="Разделы страницы «О нас» (активные), по порядку",
    description="Без авторизации. Порядок — по `sort_order`, затем по `id`.",
    responses={200: success_example([ABOUT_PUBLIC], "About retrieved."), **PUBLIC_ERRORS},
)
async def get_public_about(db: DBDep):
    data = await AboutService(db).get_public_list()
    return ResponseBuilder.success(data=data, message="About retrieved.")


@about.get(
    "",
    summary="Все разделы «О нас», включая неактивные",
    dependencies=[perm(Module.ABOUT, Action.READ)],
    responses={200: success_example([ABOUT], "About retrieved."), **COMMON_ERRORS},
)
async def get_about_list(db: DBDep):
    data = await AboutService(db).get_list()
    return ResponseBuilder.success(data=data, message="About retrieved.")


@about.post(
    "",
    status_code=201,
    summary="Создать раздел «О нас»: заголовок и текст на ru / uz / en",
    dependencies=[perm(Module.ABOUT, Action.CREATE)],
    responses={201: success_example(ABOUT, "About section created."), **COMMON_ERRORS},
)
async def create_about(data: AboutCreateDTO, db: DBDep, user: CurrentUserDep):
    section = await AboutService(db).create(user, data)
    return ResponseBuilder.success(data=section, message="About section created.", status_code=201)


@about.get(
    "/{section_id}",
    summary="Раздел «О нас» по ID",
    dependencies=[perm(Module.ABOUT, Action.READ)],
    responses={
        200: success_example(ABOUT, "About section found."),
        **COMMON_ERRORS,
        **ABOUT_NOT_FOUND,
    },
)
async def get_about(section_id: int, db: DBDep):
    data = await AboutService(db).get_detail(section_id)
    return ResponseBuilder.success(data=data, message="About section found.")


@about.patch(
    "/{section_id}",
    summary="Изменить переводы, порядок или активность раздела «О нас»",
    dependencies=[perm(Module.ABOUT, Action.UPDATE)],
    responses={
        200: success_example(ABOUT, "About section updated."),
        **COMMON_ERRORS,
        **ABOUT_NOT_FOUND,
    },
)
async def update_about(section_id: int, data: AboutUpdateDTO, db: DBDep, user: CurrentUserDep):
    section = await AboutService(db).update(user, section_id, data)
    return ResponseBuilder.success(data=section, message="About section updated.")


@about.delete(
    "/{section_id}",
    summary="Удалить раздел «О нас»",
    dependencies=[perm(Module.ABOUT, Action.DELETE)],
    responses={
        200: success_example(None, "About section deleted."),
        **COMMON_ERRORS,
        **ABOUT_NOT_FOUND,
    },
)
async def delete_about(section_id: int, db: DBDep):
    await AboutService(db).delete(section_id)
    return ResponseBuilder.success(message="About section deleted.")


# ======================= контакты организации =======================

CONTACT_PUBLIC = {
    "id": 1,
    "phone": "+998712000000",
    "email": "info@yoshlarfondi.uz",
    "sort_order": 0,
}
CONTACT = {**CONTACT_PUBLIC, "is_active": True, **AUDIT}
CONTACT_NOT_FOUND = {404: error_examples(SiteContactNotFoundException)}

contacts_public = APIRouter(prefix="/contacts", tags=["Контакты: сайт"])
contacts = APIRouter(prefix="/marketing/contacts", tags=["Контакты: управление (маркетинг)"])


@contacts_public.get(
    "",
    summary="Контакты организации (телефон, email) — активные, по порядку",
    description="Без авторизации. Порядок — по `sort_order`, затем по `id`.",
    responses={200: success_example([CONTACT_PUBLIC], "Contacts retrieved."), **PUBLIC_ERRORS},
)
async def get_public_contacts(db: DBDep):
    data = await SiteContactService(db).get_public_list()
    return ResponseBuilder.success(data=data, message="Contacts retrieved.")


@contacts.get(
    "",
    summary="Все контакты, включая неактивные",
    dependencies=[perm(Module.CONTACTS, Action.READ)],
    responses={200: success_example([CONTACT], "Contacts retrieved."), **COMMON_ERRORS},
)
async def get_contacts(db: DBDep):
    data = await SiteContactService(db).get_list()
    return ResponseBuilder.success(data=data, message="Contacts retrieved.")


@contacts.post(
    "",
    status_code=201,
    summary="Добавить контакт: телефон и/или email",
    description=(
        "Телефон — +998XXXXXXXXX, email сохраняется в нижнем регистре. Нужно хотя бы одно из "
        "двух, иначе 422."
    ),
    dependencies=[perm(Module.CONTACTS, Action.CREATE)],
    responses={201: success_example(CONTACT, "Contact created."), **COMMON_ERRORS},
)
async def create_contact(data: SiteContactCreateDTO, db: DBDep, user: CurrentUserDep):
    contact = await SiteContactService(db).create(user, data)
    return ResponseBuilder.success(data=contact, message="Contact created.", status_code=201)


@contacts.get(
    "/{contact_id}",
    summary="Контакт по ID",
    dependencies=[perm(Module.CONTACTS, Action.READ)],
    responses={
        200: success_example(CONTACT, "Contact found."),
        **COMMON_ERRORS,
        **CONTACT_NOT_FOUND,
    },
)
async def get_contact(contact_id: int, db: DBDep):
    data = await SiteContactService(db).get_detail(contact_id)
    return ResponseBuilder.success(data=data, message="Contact found.")


@contacts.patch(
    "/{contact_id}",
    summary="Изменить телефон, email, порядок или активность контакта",
    description=(
        "Передаются только изменяемые поля; `null` убирает телефон или email. Если не останется "
        "ни того, ни другого — 400 `site_contact_empty`."
    ),
    dependencies=[perm(Module.CONTACTS, Action.UPDATE)],
    responses={
        200: success_example(CONTACT, "Contact updated."),
        **COMMON_ERRORS,
        400: error_examples(SiteContactEmptyException),
        **CONTACT_NOT_FOUND,
    },
)
async def update_contact(
    contact_id: int, data: SiteContactUpdateDTO, db: DBDep, user: CurrentUserDep
):
    contact = await SiteContactService(db).update(user, contact_id, data)
    return ResponseBuilder.success(data=contact, message="Contact updated.")


@contacts.delete(
    "/{contact_id}",
    summary="Удалить контакт",
    dependencies=[perm(Module.CONTACTS, Action.DELETE)],
    responses={
        200: success_example(None, "Contact deleted."),
        **COMMON_ERRORS,
        **CONTACT_NOT_FOUND,
    },
)
async def delete_contact(contact_id: int, db: DBDep):
    await SiteContactService(db).delete(contact_id)
    return ResponseBuilder.success(message="Contact deleted.")


# ======================= члены Совета и руководство =======================

SECTIONS = {
    PersonKind.COUNCIL: {
        "module": Module.COUNCIL_PROFILES,
        "title": "Члены Совета",
        "one": "члена Совета",
        "not_found": CouncilProfileNotFoundException,
        "public_tag": "Члены Совета: сайт",
        "tag": "Члены Совета: управление (маркетинг)",
    },
    PersonKind.LEADERSHIP: {
        "module": Module.LEADERSHIP,
        "title": "Руководство",
        "one": "руководителя",
        "not_found": LeadershipProfileNotFoundException,
        "public_tag": "Руководство: сайт",
        "tag": "Руководство: управление (маркетинг)",
    },
}


def person_routers(kind: PersonKind) -> tuple[APIRouter, APIRouter]:
    """Публичный роутер и роутер маркетинга для раздела людей."""
    cfg = SECTIONS[kind]
    public_path, marketing_path = PERSON_PATHS[kind]
    module: Module = cfg["module"]
    one: str = cfg["one"]
    not_found = {404: error_examples(cfg["not_found"])}
    photo_not_found = {404: error_examples(cfg["not_found"], PersonPhotoNotFoundException)}

    base = {
        "id": 5,
        "translations": PERSON_TRANSLATIONS_EXAMPLE,
        "phone_number": "+998901234567",
        "email": "a.valiyev@yoshlarfondi.uz",
        "queue_number": 1,
    }
    public_example = {**base, "photo": {"url": f"{public_path}/5/photo", **PHOTO}}
    example = {
        **base,
        "photo": {"url": f"{marketing_path}/5/photo", **PHOTO},
        "is_active": True,
        **AUDIT,
    }

    public = APIRouter(prefix=public_path.removeprefix("/api/v1"), tags=[cfg["public_tag"]])
    router = APIRouter(prefix=marketing_path.removeprefix("/api/v1"), tags=[cfg["tag"]])

    def service(db) -> PersonService:
        return PersonService(db, kind)

    @public.get(
        "",
        summary=f"{cfg['title']} для сайта (активные), по `queue_number`",
        description="Без авторизации. Фото — по `photo.url`.",
        responses={200: success_example([public_example], "People retrieved."), **PUBLIC_ERRORS},
    )
    async def get_public_people(db: DBDep):
        data = await service(db).get_public_list()
        return ResponseBuilder.success(data=data, message="People retrieved.")

    @public.get(
        "/{person_id}",
        summary=f"Карточка {one} для сайта",
        description="Без авторизации. Неактивная карточка — 404.",
        responses={
            200: success_example(public_example, "Person found."),
            **PUBLIC_ERRORS,
            **not_found,
        },
    )
    async def get_public_person(person_id: int, db: DBDep):
        data = await service(db).get_public(person_id)
        return ResponseBuilder.success(data=data, message="Person found.")

    @public.get(
        "/{person_id}/photo",
        summary=f"Фото {one}",
        description="Без авторизации.",
        response_class=FileResponse,
        responses=photo_not_found,
    )
    async def get_public_photo(person_id: int, db: DBDep):
        path, content_type, name = await service(db).public_photo(person_id)
        return FileResponse(
            path,
            media_type=content_type,
            filename=name,
            content_disposition_type="inline",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @router.get(
        "",
        summary=f"{cfg['title']}: все карточки, включая неактивные, по `queue_number`",
        dependencies=[perm(module, Action.READ)],
        responses={200: success_example([example], "People retrieved."), **COMMON_ERRORS},
    )
    async def get_people(db: DBDep):
        data = await service(db).get_list()
        return ResponseBuilder.success(data=data, message="People retrieved.")

    @router.post(
        "",
        status_code=201,
        summary=f"Добавить {one} (multipart/form-data)",
        description=(
            "Ф.И.О. и описание — на трёх языках: `full_name_ru`, `full_name_uz`, `full_name_en`, "
            "`description_ru`, `description_uz`, `description_en`. Необязательно: "
            "`phone_number` (+998XXXXXXXXX), `email`, `queue_number` (место в списке; "
            "не указано — в конец), `photo` (JPEG / PNG / WEBP)."
        ),
        dependencies=[perm(module, Action.CREATE)],
        responses={
            201: success_example(example, "Person created."),
            **COMMON_ERRORS,
            **PHOTO_ERRORS,
        },
    )
    async def create_person(
        db: DBDep,
        user: CurrentUserDep,
        form: Annotated[PersonCreateForm, Form(media_type="multipart/form-data")],
    ):
        data = await service(db).create(user, form)
        return ResponseBuilder.success(data=data, message="Person created.", status_code=201)

    @router.get(
        "/{person_id}",
        summary=f"Карточка {one} по ID",
        dependencies=[perm(module, Action.READ)],
        responses={200: success_example(example, "Person found."), **COMMON_ERRORS, **not_found},
    )
    async def get_person(person_id: int, db: DBDep):
        data = await service(db).get_detail(person_id)
        return ResponseBuilder.success(data=data, message="Person found.")

    @router.patch(
        "/{person_id}",
        summary=f"Изменить карточку {one}: переводы, контакты, место в списке, активность",
        description=(
            "`queue_number` переставляет карточку на это место, остальные сдвигаются. "
            "Фото — `PUT` / `DELETE /{person_id}/photo`."
        ),
        dependencies=[perm(module, Action.UPDATE)],
        responses={
            200: success_example(example, "Person updated."),
            **COMMON_ERRORS,
            **not_found,
        },
    )
    async def update_person(person_id: int, data: PersonUpdateDTO, db: DBDep, user: CurrentUserDep):
        person = await service(db).update(user, person_id, data)
        return ResponseBuilder.success(data=person, message="Person updated.")

    @router.delete(
        "/{person_id}",
        summary=f"Удалить карточку {one} вместе с фото",
        description="Номера остальных карточек сдвигаются, пропусков в списке нет.",
        dependencies=[perm(module, Action.DELETE)],
        responses={200: success_example(None, "Person deleted."), **COMMON_ERRORS, **not_found},
    )
    async def delete_person(person_id: int, db: DBDep):
        await service(db).delete(person_id)
        return ResponseBuilder.success(message="Person deleted.")

    @router.get(
        "/{person_id}/photo",
        summary=f"Фото {one} (в том числе неактивной карточки)",
        dependencies=[perm(module, Action.READ)],
        response_class=FileResponse,
        responses={**COMMON_ERRORS, **photo_not_found},
    )
    async def get_photo(person_id: int, db: DBDep):
        path, content_type, name = await service(db).photo(person_id)
        return FileResponse(
            path, media_type=content_type, filename=name, content_disposition_type="inline"
        )

    @router.put(
        "/{person_id}/photo",
        summary=f"Загрузить или заменить фото {one}",
        dependencies=[perm(module, Action.UPDATE)],
        responses={
            200: success_example(example, "Photo uploaded."),
            **COMMON_ERRORS,
            **not_found,
            **PHOTO_ERRORS,
        },
    )
    async def set_photo(
        person_id: int,
        db: DBDep,
        user: CurrentUserDep,
        photo: Annotated[UploadFile, File(description="JPEG / PNG / WEBP.")],
    ):
        data = await service(db).set_photo(user, person_id, photo)
        return ResponseBuilder.success(data=data, message="Photo uploaded.")

    @router.delete(
        "/{person_id}/photo",
        summary=f"Удалить фото {one}",
        dependencies=[perm(module, Action.UPDATE)],
        responses={
            200: success_example({**example, "photo": None}, "Photo deleted."),
            **COMMON_ERRORS,
            **photo_not_found,
        },
    )
    async def delete_photo(person_id: int, db: DBDep, user: CurrentUserDep):
        data = await service(db).delete_photo(user, person_id)
        return ResponseBuilder.success(data=data, message="Photo deleted.")

    return public, router


council_public, council = person_routers(PersonKind.COUNCIL)
leadership_public, leadership = person_routers(PersonKind.LEADERSHIP)

ROUTERS = [
    events_public,
    events,
    about_public,
    about,
    council_public,
    council,
    leadership_public,
    leadership,
    contacts_public,
    contacts,
]
