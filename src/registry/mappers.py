from src.application.mappers import actor
from src.registry.dictionaries import BANKS, REGIONS, bank_labels, region_labels
from src.registry.models.registry_model import RegistryProgramORM, RegistryProjectORM
from src.registry.schemas.registry_schema import (
    CodeLabelDTO,
    ProgramDTO,
    ProgramShortDTO,
    ProgramTranslationOutDTO,
    ProjectDTO,
)


def _program_translations(model: RegistryProgramORM) -> list[ProgramTranslationOutDTO]:
    return [
        ProgramTranslationOutDTO(language=t.language, name=t.name, description=t.description)
        for t in model.translations
    ]


def program_short(model: RegistryProgramORM) -> ProgramShortDTO:
    return ProgramShortDTO(
        id=model.id, code=model.code, kind=model.kind, translations=_program_translations(model)
    )


def program_dto(model: RegistryProgramORM, projects_count: int = 0) -> ProgramDTO:
    return ProgramDTO(
        **program_short(model).model_dump(),
        import_template=model.import_template,
        is_active=model.is_active,
        sort_order=model.sort_order,
        projects_count=projects_count,
        last_import_file=model.last_import_file,
        last_import_at=model.last_import_at,
    )


def region_dto(code: str | None) -> CodeLabelDTO | None:
    if not code or code not in REGIONS:
        return None
    return CodeLabelDTO(code=code, translations=region_labels(code))


def bank_dto(code: str | None) -> CodeLabelDTO | None:
    if not code or code not in BANKS:
        return None
    return CodeLabelDTO(code=code, translations=bank_labels(code))


PLAIN_FIELDS = (
    "id",
    "source",
    "number",
    "applicant_name",
    "organization",
    "tin",
    "subject_type",
    "head_info",
    "gender",
    "age",
    "phone",
    "district",
    "mahalla",
    "purpose",
    "sector",
    "direction",
    "jobs",
    "project_cost",
    "requested_amount",
    "allocated_amount",
    "credit_amount",
    "term_months",
    "collateral",
    "bank_branch",
    "bank_letter_date",
    "bank_request",
    "order_info",
    "application_date",
    "decision",
    "council_protocol",
    "council_date",
    "status",
    "note",
    "extra",
    "created_at",
    "updated_at",
)


def project_dto(model: RegistryProjectORM) -> ProjectDTO:
    return ProjectDTO(
        **{name: getattr(model, name) for name in PLAIN_FIELDS},
        program=program_short(model.program),
        region=region_dto(model.region),
        bank=bank_dto(model.bank),
        created_by=actor(model.created_by),
        updated_by=actor(model.updated_by),
    )
