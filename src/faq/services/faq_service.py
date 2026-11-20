from src.account.schemas.user_schema import CurrentUserDTO
from src.common.responses.exceptions import FaqNotFoundException
from src.faq.mappers import FaqDataMapper
from src.faq.models.faq_model import FaqORM, FaqTranslationORM
from src.faq.schemas.faq_schema import FaqCreateDTO, FaqDTO, FaqPublicDTO, FaqUpdateDTO
from src.product.services.product_service import apply_translations
from src.utils.base_service import BaseService


class FaqService(BaseService):
    # ---------- сайт ----------

    async def get_public_list(self) -> list[FaqPublicDTO]:
        return [
            FaqDataMapper.map_to_public(f) for f in await self.db.faq.get_list(only_active=True)
        ]

    # ---------- маркетинг ----------

    async def get_list(self) -> list[FaqDTO]:
        return [FaqDataMapper.map_to_domain_entity(f) for f in await self.db.faq.get_list()]

    async def get_detail(self, faq_id: int) -> FaqDTO:
        return FaqDataMapper.map_to_domain_entity(await self._get(faq_id))

    async def create(self, user: CurrentUserDTO, data: FaqCreateDTO) -> FaqDTO:
        faq = FaqORM(
            is_active=data.is_active,
            sort_order=data.sort_order,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        apply_translations(faq.translations, data.translations, FaqTranslationORM)
        self.db.session.add(faq)
        await self.db.commit()
        return await self.get_detail(faq.id)

    async def update(self, user: CurrentUserDTO, faq_id: int, data: FaqUpdateDTO) -> FaqDTO:
        faq = await self._get(faq_id)
        if data.translations is not None:
            apply_translations(faq.translations, data.translations, FaqTranslationORM)
        if data.is_active is not None:
            faq.is_active = data.is_active
        if data.sort_order is not None:
            faq.sort_order = data.sort_order
        faq.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(faq_id)

    async def delete(self, faq_id: int) -> None:
        faq = await self._get(faq_id)
        await self.db.session.delete(faq)
        await self.db.commit()

    async def _get(self, faq_id: int) -> FaqORM:
        faq = await self.db.faq.get_orm(faq_id)
        if faq is None:
            raise FaqNotFoundException()
        return faq
