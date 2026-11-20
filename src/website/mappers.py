from src.application.mappers import actor
from src.website.enums import PersonKind
from src.website.models.website_model import AboutSectionORM, EventORM, PersonORM
from src.website.schemas.website_schema import (
    AboutDTO,
    AboutPublicDTO,
    EventDTO,
    EventPublicDTO,
    PersonDTO,
    PersonPublicDTO,
    PersonTranslationOutDTO,
    PhotoDTO,
    TitleTextOutDTO,
)

# Пути разделов людей: публичный и для маркетинга.
PERSON_PATHS: dict[PersonKind, tuple[str, str]] = {
    PersonKind.COUNCIL: ("/api/v1/council-members", "/api/v1/marketing/council-members"),
    PersonKind.LEADERSHIP: ("/api/v1/leadership", "/api/v1/marketing/leadership"),
}


def _audit(model) -> dict:
    return {
        "created_by": actor(model.created_by),
        "updated_by": actor(model.updated_by),
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _title_text(model) -> list[TitleTextOutDTO]:
    return [
        TitleTextOutDTO(language=t.language, title=t.title, text=t.text) for t in model.translations
    ]


def event_public(model: EventORM) -> EventPublicDTO:
    return EventPublicDTO(id=model.id, translations=_title_text(model), date=model.event_date)


def event_dto(model: EventORM) -> EventDTO:
    return EventDTO(
        id=model.id,
        translations=_title_text(model),
        date=model.event_date,
        is_active=model.is_active,
        **_audit(model),
    )


def about_public(model: AboutSectionORM) -> AboutPublicDTO:
    return AboutPublicDTO(id=model.id, translations=_title_text(model), sort_order=model.sort_order)


def about_dto(model: AboutSectionORM) -> AboutDTO:
    return AboutDTO(
        id=model.id,
        translations=_title_text(model),
        sort_order=model.sort_order,
        is_active=model.is_active,
        **_audit(model),
    )


def _person_fields(model: PersonORM, prefix: str) -> dict:
    photo = None
    if model.photo_path:
        photo = PhotoDTO(
            url=f"{prefix}/{model.id}/photo",
            name=model.photo_name,
            content_type=model.photo_content_type or "image/jpeg",
            size=model.photo_size or 0,
        )
    return {
        "id": model.id,
        "translations": [
            PersonTranslationOutDTO(
                language=t.language, full_name=t.full_name, description=t.description
            )
            for t in model.translations
        ],
        "phone_number": model.phone_number,
        "email": model.email,
        "queue_number": model.queue_number,
        "photo": photo,
    }


def person_public(model: PersonORM) -> PersonPublicDTO:
    return PersonPublicDTO(**_person_fields(model, PERSON_PATHS[model.kind][0]))


def person_dto(model: PersonORM) -> PersonDTO:
    return PersonDTO(
        **_person_fields(model, PERSON_PATHS[model.kind][1]),
        is_active=model.is_active,
        **_audit(model),
    )


class WebsiteDataMapper:
    """Для BaseRepository.paginate: событие — основной объект репозитория."""

    @staticmethod
    def map_to_domain_entity(model: EventORM) -> EventDTO:
        return event_dto(model)
