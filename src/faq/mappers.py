from src.application.mappers import actor
from src.faq.models.faq_model import FaqORM
from src.faq.schemas.faq_schema import FaqDTO, FaqPublicDTO, FaqTranslationOutDTO
from src.utils.base_rep.mappers.base import DataMapper


def _translations(model: FaqORM) -> list[FaqTranslationOutDTO]:
    return [
        FaqTranslationOutDTO(language=t.language, question=t.question, answer=t.answer)
        for t in model.translations
    ]


class FaqDataMapper(DataMapper):
    db_model = FaqORM
    schema = FaqDTO

    @classmethod
    def map_to_domain_entity(cls, data: FaqORM) -> FaqDTO:
        return FaqDTO(
            id=data.id,
            translations=_translations(data),
            sort_order=data.sort_order,
            is_active=data.is_active,
            created_by=actor(data.created_by),
            updated_by=actor(data.updated_by),
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

    @staticmethod
    def map_to_public(data: FaqORM) -> FaqPublicDTO:
        return FaqPublicDTO(
            id=data.id, translations=_translations(data), sort_order=data.sort_order
        )
