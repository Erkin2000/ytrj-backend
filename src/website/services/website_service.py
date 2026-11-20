"""Контент сайта: события, «О нас», члены Совета и руководство."""

from pathlib import Path

from fastapi import UploadFile

from src.account.schemas.user_schema import CurrentUserDTO
from src.common.responses.exceptions import (
    AboutSectionNotFoundException,
    CouncilProfileNotFoundException,
    EventNotFoundException,
    LeadershipProfileNotFoundException,
    PersonPhotoNotFoundException,
)
from src.product.services.product_service import apply_translations
from src.utils.base_service import BaseService
from src.website.enums import PersonKind
from src.website.mappers import (
    about_dto,
    about_public,
    event_dto,
    event_public,
    person_dto,
    person_public,
)
from src.website.models.website_model import (
    AboutSectionORM,
    AboutTranslationORM,
    EventORM,
    EventTranslationORM,
    PersonORM,
    PersonTranslationORM,
)
from src.website.schemas.website_schema import (
    AboutCreateDTO,
    AboutDTO,
    AboutPublicDTO,
    AboutUpdateDTO,
    EventCreateDTO,
    EventDTO,
    EventFilterDTO,
    EventPublicDTO,
    EventUpdateDTO,
    PersonCreateForm,
    PersonDTO,
    PersonPublicDTO,
    PersonUpdateDTO,
)
from src.website.storage import PersonPhotoStorage


class EventService(BaseService):
    async def get_page(
        self, filters: EventFilterDTO, page: int | None, per_page: int | None, public: bool
    ) -> dict:
        return await self.db.website.get_events_page(filters, page, per_page, only_active=public)

    async def get_public(self, event_id: int) -> EventPublicDTO:
        event = await self._get(event_id)
        if not event.is_active:
            raise EventNotFoundException()
        return event_public(event)

    async def get_detail(self, event_id: int) -> EventDTO:
        return event_dto(await self._get(event_id))

    async def create(self, user: CurrentUserDTO, data: EventCreateDTO) -> EventDTO:
        event = EventORM(
            event_date=data.date,
            is_active=data.is_active,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        apply_translations(event.translations, data.translations, EventTranslationORM)
        self.db.session.add(event)
        await self.db.commit()
        return await self.get_detail(event.id)

    async def update(self, user: CurrentUserDTO, event_id: int, data: EventUpdateDTO) -> EventDTO:
        event = await self._get(event_id)
        if data.translations is not None:
            apply_translations(event.translations, data.translations, EventTranslationORM)
        if data.date is not None:
            event.event_date = data.date
        if data.is_active is not None:
            event.is_active = data.is_active
        event.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(event_id)

    async def delete(self, event_id: int) -> None:
        await self.db.session.delete(await self._get(event_id))
        await self.db.commit()

    async def _get(self, event_id: int) -> EventORM:
        event = await self.db.website.get_event(event_id)
        if event is None:
            raise EventNotFoundException()
        return event


class AboutService(BaseService):
    async def get_public_list(self) -> list[AboutPublicDTO]:
        return [about_public(s) for s in await self.db.website.get_about_list(only_active=True)]

    async def get_list(self) -> list[AboutDTO]:
        return [about_dto(s) for s in await self.db.website.get_about_list(only_active=False)]

    async def get_detail(self, section_id: int) -> AboutDTO:
        return about_dto(await self._get(section_id))

    async def create(self, user: CurrentUserDTO, data: AboutCreateDTO) -> AboutDTO:
        section = AboutSectionORM(
            sort_order=data.sort_order,
            is_active=data.is_active,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        apply_translations(section.translations, data.translations, AboutTranslationORM)
        self.db.session.add(section)
        await self.db.commit()
        return await self.get_detail(section.id)

    async def update(self, user: CurrentUserDTO, section_id: int, data: AboutUpdateDTO) -> AboutDTO:
        section = await self._get(section_id)
        if data.translations is not None:
            apply_translations(section.translations, data.translations, AboutTranslationORM)
        if data.sort_order is not None:
            section.sort_order = data.sort_order
        if data.is_active is not None:
            section.is_active = data.is_active
        section.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(section_id)

    async def delete(self, section_id: int) -> None:
        await self.db.session.delete(await self._get(section_id))
        await self.db.commit()

    async def _get(self, section_id: int) -> AboutSectionORM:
        section = await self.db.website.get_about(section_id)
        if section is None:
            raise AboutSectionNotFoundException()
        return section


NOT_FOUND = {
    PersonKind.COUNCIL: CouncilProfileNotFoundException,
    PersonKind.LEADERSHIP: LeadershipProfileNotFoundException,
}


class PersonService(BaseService):
    """Члены Совета и руководство на сайте — одна логика, раздел задаёт `kind`."""

    storage = PersonPhotoStorage()

    def __init__(self, db, kind: PersonKind):
        super().__init__(db)
        self.kind = kind

    # ---------- сайт ----------

    async def get_public_list(self) -> list[PersonPublicDTO]:
        people = await self.db.website.get_people(self.kind, only_active=True)
        return [person_public(p) for p in people]

    async def get_public(self, person_id: int) -> PersonPublicDTO:
        return person_public(await self._get(person_id, active=True))

    async def public_photo(self, person_id: int) -> tuple[Path, str, str]:
        return self._photo_file(await self._get(person_id, active=True))

    # ---------- маркетинг ----------

    async def get_list(self) -> list[PersonDTO]:
        return [person_dto(p) for p in await self.db.website.get_people(self.kind)]

    async def get_detail(self, person_id: int) -> PersonDTO:
        return person_dto(await self._get(person_id))

    async def photo(self, person_id: int) -> tuple[Path, str, str]:
        return self._photo_file(await self._get(person_id))

    async def create(self, user: CurrentUserDTO, form: PersonCreateForm) -> PersonDTO:
        people = await self.db.website.get_people(self.kind, for_update=True)
        person = PersonORM(
            kind=self.kind,
            queue_number=len(people) + 1,
            phone_number=form.phone_number,
            email=str(form.email) if form.email else None,
            is_active=form.is_active,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        apply_translations(person.translations, form.translations(), PersonTranslationORM)
        self.db.session.add(person)
        await self.db.flush()
        self._place(people, person, form.queue_number)
        try:
            if form.photo is not None:
                await self._store_photo(person, form.photo)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            await self.storage.delete_person_dir(person.id)
            raise
        return await self.get_detail(person.id)

    async def update(
        self, user: CurrentUserDTO, person_id: int, data: PersonUpdateDTO
    ) -> PersonDTO:
        people = await self.db.website.get_people(self.kind, for_update=True)
        person = await self._get(person_id)
        fields = data.model_fields_set
        if data.translations is not None:
            apply_translations(person.translations, data.translations, PersonTranslationORM)
        if "phone_number" in fields:
            person.phone_number = data.phone_number
        if "email" in fields:
            person.email = str(data.email) if data.email else None
        if data.is_active is not None:
            person.is_active = data.is_active
        if data.queue_number is not None:
            self._place([p for p in people if p.id != person.id], person, data.queue_number)
        person.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(person_id)

    async def delete(self, person_id: int) -> None:
        people = await self.db.website.get_people(self.kind, for_update=True)
        person = await self._get(person_id)
        await self.db.session.delete(person)
        self._renumber([p for p in people if p.id != person.id])
        await self.db.commit()
        await self.storage.delete_person_dir(person_id)

    async def set_photo(self, user: CurrentUserDTO, person_id: int, photo: UploadFile) -> PersonDTO:
        person = await self._get(person_id)
        old_path = person.photo_path
        await self._store_photo(person, photo)
        person.updated_by_id = user.id
        try:
            await self.db.commit()
        except Exception:
            await self.storage.delete(person.photo_path)
            raise
        if old_path:
            await self.storage.delete(old_path)
        return await self.get_detail(person_id)

    async def delete_photo(self, user: CurrentUserDTO, person_id: int) -> PersonDTO:
        person = await self._get(person_id)
        if not person.photo_path:
            raise PersonPhotoNotFoundException()
        old_path = person.photo_path
        person.photo_path = person.photo_name = person.photo_content_type = None
        person.photo_size = None
        person.updated_by_id = user.id
        await self.db.commit()
        await self.storage.delete(old_path)
        return await self.get_detail(person_id)

    # ---------- внутреннее ----------

    @classmethod
    def _place(cls, others: list[PersonORM], person: PersonORM, position: int | None) -> None:
        """Ставит человека на место `position` (1 — первый, больше длины — в конец)
        и перенумеровывает список раздела без пропусков."""
        ordered = list(others)
        index = len(ordered) if position is None else min(max(position, 1) - 1, len(ordered))
        ordered.insert(index, person)
        cls._renumber(ordered)

    @staticmethod
    def _renumber(people: list[PersonORM]) -> None:
        for number, item in enumerate(people, start=1):
            item.queue_number = number

    async def _get(self, person_id: int, active: bool = False) -> PersonORM:
        person = await self.db.website.get_person(self.kind, person_id)
        if person is None or (active and not person.is_active):
            raise NOT_FOUND[self.kind]()
        return person

    async def _store_photo(self, person: PersonORM, photo: UploadFile) -> None:
        path, size, content_type = await self.storage.save(person.id, photo)
        person.photo_path = path
        person.photo_name = (Path(photo.filename or "").name or Path(path).name)[:255]
        person.photo_content_type = content_type
        person.photo_size = size

    def _photo_file(self, person: PersonORM) -> tuple[Path, str, str]:
        if not person.photo_path:
            raise PersonPhotoNotFoundException()
        path = self.storage.absolute_path(person.photo_path)
        if not path.is_file():
            raise PersonPhotoNotFoundException()
        return path, person.photo_content_type or "image/jpeg", person.photo_name or path.name
