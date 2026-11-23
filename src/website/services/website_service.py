"""Контент сайта: события, «О нас», члены Совета и руководство, контакты, отзывы."""

from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import UploadFile

from src.account.schemas.user_schema import CurrentUserDTO
from src.bulletin.enums import TASHKENT_TZ
from src.common.responses.exceptions import (
    AboutSectionNotFoundException,
    CouncilProfileNotFoundException,
    EventCalendarRangeException,
    EventNotFoundException,
    EventPhotoNotFoundException,
    LeadershipProfileNotFoundException,
    PersonPhotoNotFoundException,
    SiteContactEmptyException,
    SiteContactNotFoundException,
    TestimonialNotFoundException,
    TestimonialPhotoNotFoundException,
)
from src.product.services.product_service import apply_translations
from src.utils.base_service import BaseService
from src.website.enums import PersonKind
from src.website.mappers import (
    about_dto,
    about_public,
    contact_dto,
    contact_public,
    event_dto,
    event_public,
    person_dto,
    person_public,
    testimonial_dto,
    testimonial_public,
)
from src.website.models.website_model import (
    AboutSectionORM,
    AboutTranslationORM,
    EventORM,
    EventTranslationORM,
    PersonORM,
    PersonTranslationORM,
    SiteContactORM,
    TestimonialORM,
    TestimonialTranslationORM,
)
from src.website.schemas.website_schema import (
    AboutCreateDTO,
    AboutDTO,
    AboutPublicDTO,
    AboutUpdateDTO,
    EventCalendarDayDTO,
    EventCreateForm,
    EventDTO,
    EventFilterDTO,
    EventPublicDTO,
    EventUpdateDTO,
    PersonCreateForm,
    PersonDTO,
    PersonPublicDTO,
    PersonUpdateDTO,
    SiteContactCreateDTO,
    SiteContactDTO,
    SiteContactPublicDTO,
    SiteContactUpdateDTO,
    TestimonialCreateForm,
    TestimonialDTO,
    TestimonialPublicDTO,
    TestimonialUpdateDTO,
)
from src.website.storage import (
    EventPhotoStorage,
    PersonPhotoStorage,
    SitePhotoStorage,
    TestimonialPhotoStorage,
)

# Календарь событий: не больше ~квартала за один запрос.
CALENDAR_MAX_DAYS = 93


def month_bounds(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    """Диапазон календаря включительно; по умолчанию — текущий месяц по Ташкенту."""
    if date_from is None:
        date_from = datetime.now(TASHKENT_TZ).date().replace(day=1)
    if date_to is None:
        next_month = (date_from.replace(day=28) + timedelta(days=4)).replace(day=1)
        date_to = next_month - timedelta(days=1)
    if date_to < date_from:
        raise EventCalendarRangeException("date_to must not be earlier than date_from")
    if (date_to - date_from).days >= CALENDAR_MAX_DAYS:
        raise EventCalendarRangeException(
            f"Calendar range must not exceed {CALENDAR_MAX_DAYS} days"
        )
    return date_from, date_to


async def store_photo(storage: SitePhotoStorage, model, photo: UploadFile) -> None:
    path, size, content_type = await storage.save(model.id, photo)
    model.photo_path = path
    model.photo_name = (Path(photo.filename or "").name or Path(path).name)[:255]
    model.photo_content_type = content_type
    model.photo_size = size


def clear_photo(model) -> None:
    model.photo_path = model.photo_name = model.photo_content_type = None
    model.photo_size = None


def photo_file(storage: SitePhotoStorage, model, not_found) -> tuple[Path, str, str]:
    if not model.photo_path:
        raise not_found()
    path = storage.absolute_path(model.photo_path)
    if not path.is_file():
        raise not_found()
    return path, model.photo_content_type or "image/jpeg", model.photo_name or path.name


class EventService(BaseService):
    storage = EventPhotoStorage()

    async def get_calendar(
        self, date_from: date | None, date_to: date | None, public: bool
    ) -> list[EventCalendarDayDTO]:
        start, end = month_bounds(date_from, date_to)
        days = await self.db.website.get_event_days(start, end, only_active=public)
        return [EventCalendarDayDTO(date=day, count=count) for day, count in days]

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

    async def create(self, user: CurrentUserDTO, form: EventCreateForm) -> EventDTO:
        event = EventORM(
            event_date=form.date,
            is_active=form.is_active,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        apply_translations(event.translations, form.translations(), EventTranslationORM)
        self.db.session.add(event)
        await self.db.flush()
        try:
            if form.photo is not None:
                await store_photo(self.storage, event, form.photo)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            await self.storage.delete_dir(event.id)
            raise
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
        await self.storage.delete_dir(event_id)

    async def public_photo(self, event_id: int) -> tuple[Path, str, str]:
        event = await self._get(event_id)
        if not event.is_active:
            raise EventNotFoundException()
        return photo_file(self.storage, event, EventPhotoNotFoundException)

    async def photo(self, event_id: int) -> tuple[Path, str, str]:
        return photo_file(self.storage, await self._get(event_id), EventPhotoNotFoundException)

    async def set_photo(self, user: CurrentUserDTO, event_id: int, photo: UploadFile) -> EventDTO:
        event = await self._get(event_id)
        old_path = event.photo_path
        await store_photo(self.storage, event, photo)
        event.updated_by_id = user.id
        try:
            await self.db.commit()
        except Exception:
            await self.storage.delete(event.photo_path)
            raise
        if old_path:
            await self.storage.delete(old_path)
        return await self.get_detail(event_id)

    async def delete_photo(self, user: CurrentUserDTO, event_id: int) -> EventDTO:
        event = await self._get(event_id)
        if not event.photo_path:
            raise EventPhotoNotFoundException()
        old_path = event.photo_path
        clear_photo(event)
        event.updated_by_id = user.id
        await self.db.commit()
        await self.storage.delete(old_path)
        return await self.get_detail(event_id)

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


class SiteContactService(BaseService):
    """Контакты организации на сайте: телефон и/или email, несколько записей."""

    async def get_public_list(self) -> list[SiteContactPublicDTO]:
        return [contact_public(c) for c in await self.db.website.get_contacts(only_active=True)]

    async def get_list(self) -> list[SiteContactDTO]:
        return [contact_dto(c) for c in await self.db.website.get_contacts(only_active=False)]

    async def get_detail(self, contact_id: int) -> SiteContactDTO:
        return contact_dto(await self._get(contact_id))

    async def create(self, user: CurrentUserDTO, data: SiteContactCreateDTO) -> SiteContactDTO:
        contact = SiteContactORM(
            phone=data.phone,
            email=data.email.lower() if data.email else None,
            sort_order=data.sort_order,
            is_active=data.is_active,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        self.db.session.add(contact)
        await self.db.commit()
        return await self.get_detail(contact.id)

    async def update(
        self, user: CurrentUserDTO, contact_id: int, data: SiteContactUpdateDTO
    ) -> SiteContactDTO:
        contact = await self._get(contact_id)
        changes = data.model_fields_set
        if "phone" in changes:
            contact.phone = data.phone
        if "email" in changes:
            contact.email = data.email.lower() if data.email else None
        if not contact.phone and not contact.email:
            raise SiteContactEmptyException()
        if data.sort_order is not None:
            contact.sort_order = data.sort_order
        if data.is_active is not None:
            contact.is_active = data.is_active
        contact.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(contact_id)

    async def delete(self, contact_id: int) -> None:
        await self.db.session.delete(await self._get(contact_id))
        await self.db.commit()

    async def _get(self, contact_id: int) -> SiteContactORM:
        contact = await self.db.website.get_contact(contact_id)
        if contact is None:
            raise SiteContactNotFoundException()
        return contact


class TestimonialService(BaseService):
    """Отзывы пользователей сайта: фото, Ф.И.О. и текст на ru / uz / en."""

    storage = TestimonialPhotoStorage()

    # ---------- сайт ----------

    async def get_public_list(self) -> list[TestimonialPublicDTO]:
        items = await self.db.website.get_testimonials(only_active=True)
        return [testimonial_public(t) for t in items]

    async def get_public(self, testimonial_id: int) -> TestimonialPublicDTO:
        return testimonial_public(await self._get(testimonial_id, active=True))

    async def public_photo(self, testimonial_id: int) -> tuple[Path, str, str]:
        return self._photo_file(await self._get(testimonial_id, active=True))

    # ---------- маркетинг ----------

    async def get_list(self) -> list[TestimonialDTO]:
        items = await self.db.website.get_testimonials(only_active=False)
        return [testimonial_dto(t) for t in items]

    async def get_detail(self, testimonial_id: int) -> TestimonialDTO:
        return testimonial_dto(await self._get(testimonial_id))

    async def photo(self, testimonial_id: int) -> tuple[Path, str, str]:
        return self._photo_file(await self._get(testimonial_id))

    async def create(self, user: CurrentUserDTO, form: TestimonialCreateForm) -> TestimonialDTO:
        testimonial = TestimonialORM(
            sort_order=form.sort_order,
            is_active=form.is_active,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        apply_translations(testimonial.translations, form.translations(), TestimonialTranslationORM)
        self.db.session.add(testimonial)
        await self.db.flush()
        try:
            if form.photo is not None:
                await store_photo(self.storage, testimonial, form.photo)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            await self.storage.delete_dir(testimonial.id)
            raise
        return await self.get_detail(testimonial.id)

    async def update(
        self, user: CurrentUserDTO, testimonial_id: int, data: TestimonialUpdateDTO
    ) -> TestimonialDTO:
        testimonial = await self._get(testimonial_id)
        if data.translations is not None:
            apply_translations(
                testimonial.translations, data.translations, TestimonialTranslationORM
            )
        if data.sort_order is not None:
            testimonial.sort_order = data.sort_order
        if data.is_active is not None:
            testimonial.is_active = data.is_active
        testimonial.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(testimonial_id)

    async def delete(self, testimonial_id: int) -> None:
        await self.db.session.delete(await self._get(testimonial_id))
        await self.db.commit()
        await self.storage.delete_dir(testimonial_id)

    async def set_photo(
        self, user: CurrentUserDTO, testimonial_id: int, photo: UploadFile
    ) -> TestimonialDTO:
        testimonial = await self._get(testimonial_id)
        old_path = testimonial.photo_path
        await store_photo(self.storage, testimonial, photo)
        testimonial.updated_by_id = user.id
        try:
            await self.db.commit()
        except Exception:
            await self.storage.delete(testimonial.photo_path)
            raise
        if old_path and old_path != testimonial.photo_path:
            await self.storage.delete(old_path)
        return await self.get_detail(testimonial_id)

    async def delete_photo(self, user: CurrentUserDTO, testimonial_id: int) -> TestimonialDTO:
        testimonial = await self._get(testimonial_id)
        if not testimonial.photo_path:
            raise TestimonialPhotoNotFoundException()
        old_path = testimonial.photo_path
        clear_photo(testimonial)
        testimonial.updated_by_id = user.id
        await self.db.commit()
        await self.storage.delete(old_path)
        return await self.get_detail(testimonial_id)

    async def _get(self, testimonial_id: int, active: bool = False) -> TestimonialORM:
        testimonial = await self.db.website.get_testimonial(testimonial_id)
        if testimonial is None or (active and not testimonial.is_active):
            raise TestimonialNotFoundException()
        return testimonial

    def _photo_file(self, testimonial: TestimonialORM) -> tuple[Path, str, str]:
        return photo_file(self.storage, testimonial, TestimonialPhotoNotFoundException)


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
                await store_photo(self.storage, person, form.photo)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            await self.storage.delete_dir(person.id)
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
        await self.storage.delete_dir(person_id)

    async def set_photo(self, user: CurrentUserDTO, person_id: int, photo: UploadFile) -> PersonDTO:
        person = await self._get(person_id)
        old_path = person.photo_path
        await store_photo(self.storage, person, photo)
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
        clear_photo(person)
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

    def _photo_file(self, person: PersonORM) -> tuple[Path, str, str]:
        return photo_file(self.storage, person, PersonPhotoNotFoundException)
