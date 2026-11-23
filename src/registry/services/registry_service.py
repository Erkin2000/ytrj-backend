"""Реестр проектов: программы, проекты, импорт Excel и аналитика."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from zipfile import BadZipFile

import anyio
from fastapi import UploadFile

from src.account.models.user_model import Gender
from src.account.schemas.user_schema import CurrentUserDTO
from src.common.responses.exceptions import (
    RegistryImportFileException,
    RegistryImportTemplateException,
    RegistryProgramCodeTakenException,
    RegistryProgramInUseException,
    RegistryProgramNotFoundException,
    RegistryProjectNotFoundException,
)
from src.product.services.product_service import apply_translations
from src.registry.dictionaries import (
    BANKS,
    LABELS,
    REGIONS,
    bank_labels,
    district_key,
    district_name,
    enum_labels,
    labels,
    region_labels,
)
from src.registry.enums import (
    Decision,
    GroupBy,
    ImportTemplate,
    ProgramKind,
    ProjectStatus,
    RegistrySubjectType,
    Sector,
    Source,
)
from src.registry.importer import TemplateMismatchError, parse_workbook
from src.registry.mappers import program_dto, program_short, project_dto
from src.registry.models.registry_model import (
    RegistryProgramORM,
    RegistryProgramTranslationORM,
    RegistryProjectORM,
)
from src.registry.schemas.registry_schema import (
    BreakdownDTO,
    BreakdownRowDTO,
    CodeLabelDTO,
    DictionariesDTO,
    ImportResultDTO,
    ProgramCreateDTO,
    ProgramDTO,
    ProgramUpdateDTO,
    ProjectCreateDTO,
    ProjectDTO,
    ProjectFilterDTO,
    ProjectUpdateDTO,
    PublicAnalyticsFilterDTO,
    PublicProgramDTO,
    PublicScopeFilterDTO,
    SummaryDTO,
    TotalsDTO,
)
from src.utils.base_service import BaseService

IMPORT_MAX_SIZE_MB = 30
EXCEL_SIGNATURE = b"PK\x03\x04"  # xlsx — zip-архив


def _codes(enum_cls) -> list[CodeLabelDTO]:
    return [CodeLabelDTO(code=m.value, translations=enum_labels(enum_cls, m)) for m in enum_cls]


class RegistryProgramService(BaseService):
    async def get_list(self) -> list[ProgramDTO]:
        counts = await self.db.registry.projects_count_by_program()
        return [program_dto(p, counts.get(p.id, 0)) for p in await self.db.registry.get_programs()]

    async def get_detail(self, program_id: int) -> ProgramDTO:
        program = await self._get(program_id)
        counts = await self.db.registry.projects_count_by_program()
        return program_dto(program, counts.get(program.id, 0))

    async def create(self, data: ProgramCreateDTO) -> ProgramDTO:
        if await self.db.registry.get_program_by_code(data.code):
            raise RegistryProgramCodeTakenException()
        program = RegistryProgramORM(
            code=data.code,
            kind=data.kind,
            import_template=data.import_template,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )
        apply_translations(program.translations, data.translations, RegistryProgramTranslationORM)
        self.db.session.add(program)
        await self.db.commit()
        return await self.get_detail(program.id)

    async def update(self, program_id: int, data: ProgramUpdateDTO) -> ProgramDTO:
        program = await self._get(program_id)
        changes = data.model_fields_set
        if data.code is not None and data.code != program.code:
            if await self.db.registry.get_program_by_code(data.code):
                raise RegistryProgramCodeTakenException()
            program.code = data.code
        if data.kind is not None:
            program.kind = data.kind
        if "import_template" in changes:
            program.import_template = data.import_template
        if data.translations is not None:
            apply_translations(
                program.translations, data.translations, RegistryProgramTranslationORM
            )
        if data.is_active is not None:
            program.is_active = data.is_active
        if data.sort_order is not None:
            program.sort_order = data.sort_order
        await self.db.commit()
        return await self.get_detail(program_id)

    async def delete(self, program_id: int) -> None:
        program = await self._get(program_id)
        counts = await self.db.registry.projects_count_by_program()
        if counts.get(program_id):
            raise RegistryProgramInUseException()
        await self.db.session.delete(program)
        await self.db.commit()

    async def _get(self, program_id: int) -> RegistryProgramORM:
        program = await self.db.registry.get_program(program_id)
        if program is None:
            raise RegistryProgramNotFoundException()
        return program


class RegistryProjectService(BaseService):
    async def get_page(
        self, filters: ProjectFilterDTO, page: int | None, per_page: int | None
    ) -> dict:
        return await self.db.registry.get_projects_page(filters, page, per_page, project_dto)

    async def get_detail(self, project_id: int) -> ProjectDTO:
        return project_dto(await self._get(project_id))

    async def create(self, user: CurrentUserDTO, data: ProjectCreateDTO) -> ProjectDTO:
        await self._program(data.program_id)
        project = RegistryProjectORM(
            source=Source.MANUAL, created_by_id=user.id, updated_by_id=user.id
        )
        self._apply(project, data.model_dump())
        self.db.session.add(project)
        await self.db.commit()
        return await self.get_detail(project.id)

    async def update(
        self, user: CurrentUserDTO, project_id: int, data: ProjectUpdateDTO
    ) -> ProjectDTO:
        project = await self._get(project_id)
        changes = data.model_dump(exclude_unset=True)
        for required in ("program_id", "applicant_name", "status"):
            if required in changes and changes[required] is None:
                changes.pop(required)
        if "program_id" in changes:
            await self._program(changes["program_id"])
        self._apply(project, changes)
        project.updated_by_id = user.id
        await self.db.commit()
        return await self.get_detail(project_id)

    async def delete(self, project_id: int) -> None:
        await self.db.session.delete(await self._get(project_id))
        await self.db.commit()

    @staticmethod
    def _apply(project: RegistryProjectORM, values: dict) -> None:
        for name, value in values.items():
            setattr(project, name, value)
        if "district" in values:
            project.district = district_name(values["district"])
            project.district_key = district_key(project.district)

    async def _program(self, program_id: int) -> RegistryProgramORM:
        program = await self.db.registry.get_program(program_id)
        if program is None:
            raise RegistryProgramNotFoundException(field="program_id")
        return program

    async def _get(self, project_id: int) -> RegistryProjectORM:
        project = await self.db.registry.get_project(project_id)
        if project is None:
            raise RegistryProjectNotFoundException()
        return project


class RegistryImportService(BaseService):
    async def import_file(
        self, user: CurrentUserDTO, program_id: int, file: UploadFile
    ) -> ImportResultDTO:
        program = await self.db.registry.get_program(program_id)
        if program is None:
            raise RegistryProgramNotFoundException(field="program_id")
        if program.import_template is None:
            raise RegistryImportTemplateException(
                "Program has no import template", field="program_id"
            )
        content = await file.read(IMPORT_MAX_SIZE_MB * 1024 * 1024 + 1)
        if len(content) > IMPORT_MAX_SIZE_MB * 1024 * 1024:
            raise RegistryImportFileException(f"File is larger than {IMPORT_MAX_SIZE_MB} MB")
        if not content.startswith(EXCEL_SIGNATURE):
            raise RegistryImportFileException("Only .xlsx / .xlsm files are accepted")
        name = Path(file.filename or "import.xlsx").name[:255]
        return await self.import_bytes(user, program, content, name)

    async def import_bytes(
        self, user: CurrentUserDTO | None, program: RegistryProgramORM, content: bytes, name: str
    ) -> ImportResultDTO:
        template = ImportTemplate(program.import_template)
        try:
            parsed = await anyio.to_thread.run_sync(parse_workbook, content, template)
        except TemplateMismatchError:
            raise RegistryImportTemplateException(
                f"No sheet with {template.value} template headers found in the file"
            ) from None
        except (BadZipFile, KeyError, ValueError, OSError):
            raise RegistryImportFileException(
                "The file cannot be read as an Excel workbook"
            ) from None

        replaced = await self.db.registry.delete_imported(program.id)
        author = user.id if user else None
        self.db.session.add_all(
            RegistryProjectORM(
                program_id=program.id,
                source=Source.IMPORT,
                created_by_id=author,
                updated_by_id=author,
                **row,
            )
            for row in parsed.rows
        )
        program.last_import_file = name
        program.last_import_at = datetime.now(UTC)
        await self.db.commit()
        program = await self.db.registry.get_program(program.id)
        return ImportResultDTO(
            program=program_short(program),
            file_name=name,
            sheet=parsed.sheet,
            imported=len(parsed.rows),
            replaced=replaced,
            skipped=parsed.skipped,
            unknown_regions=sorted(parsed.unknown_regions),
            unknown_banks=sorted(parsed.unknown_banks),
        )


class RegistryAnalyticsService(BaseService):
    async def dictionaries(self) -> DictionariesDTO:
        return DictionariesDTO(
            regions=[CodeLabelDTO(code=c, translations=region_labels(c)) for c in REGIONS],
            banks=[CodeLabelDTO(code=c, translations=bank_labels(c)) for c in BANKS],
            kinds=_codes(ProgramKind),
            statuses=_codes(ProjectStatus),
            decisions=_codes(Decision),
            subject_types=_codes(RegistrySubjectType),
            sectors=_codes(Sector),
            genders=_codes(Gender),
            import_templates=[t.value for t in ImportTemplate],
            group_by=[g.value for g in GroupBy],
        )

    async def summary(self, filters: ProjectFilterDTO) -> SummaryDTO:
        repo = self.db.registry
        totals = TotalsDTO(**await repo.totals(filters))
        date_min, date_max = await repo.date_range(filters)
        average = (
            (totals.allocated_amount / totals.allocated_count).quantize(Decimal("0.01"))
            if totals.allocated_count
            else Decimal(0)
        )
        P = RegistryProjectORM
        return SummaryDTO(
            **totals.model_dump(),
            average_allocated=average,
            by_gender=await repo.counts_by(P.gender, filters),
            by_subject_type=await repo.counts_by(P.subject_type, filters),
            by_status=await repo.counts_by(P.status, filters),
            date_min=date_min,
            date_max=date_max,
        )

    async def breakdown(self, group_by: GroupBy, filters: ProjectFilterDTO) -> BreakdownDTO:
        rows = await self.db.registry.breakdown(group_by, filters)
        programs = (
            {p.id: p for p in await self.db.registry.get_programs()}
            if group_by == GroupBy.PROGRAM
            else {}
        )
        result = []
        for row in rows:
            key = row.pop("key")
            label = row.pop("label", None)
            row.pop("region", None)
            if hasattr(key, "value"):
                key = key.value
            if isinstance(key, Decimal):
                key = int(key)
            result.append(
                BreakdownRowDTO(
                    key=None if key is None else str(key),
                    translations=self._label(group_by, key, label, programs),
                    **row,
                )
            )
        if group_by in (GroupBy.YEAR, GroupBy.MONTH):
            result.sort(key=lambda r: (r.key is None, r.key or ""))
        return BreakdownDTO(
            group_by=group_by,
            rows=result,
            total=TotalsDTO(**await self.db.registry.totals(filters)),
        )

    @staticmethod
    def _label(group_by: GroupBy, key, label, programs) -> list:
        if key is None:
            return labels(("Не указано", "Koʻrsatilmagan", "Not specified"))
        enum_for = {
            GroupBy.KIND: ProgramKind,
            GroupBy.SECTOR: Sector,
            GroupBy.GENDER: Gender,
            GroupBy.SUBJECT_TYPE: RegistrySubjectType,
            GroupBy.STATUS: ProjectStatus,
        }
        if group_by in enum_for and key in LABELS[enum_for[group_by]]:
            return enum_labels(enum_for[group_by], key)
        if group_by == GroupBy.REGION and key in REGIONS:
            return region_labels(key)
        if group_by == GroupBy.BANK and key in BANKS:
            return bank_labels(key)
        if group_by == GroupBy.PROGRAM and key in programs:
            return [{"language": t.language, "name": t.name} for t in programs[key].translations]
        text = str(label or key)
        return labels((text, text, text))


class PublicAnalyticsService(BaseService):
    """Аналитика для сайта без токена: только агрегаты по активным программам —
    без списка проектов, имён, ПИНФЛ, телефонов и поиска."""

    @staticmethod
    def _scope(filters: PublicAnalyticsFilterDTO) -> PublicScopeFilterDTO:
        return PublicScopeFilterDTO(**filters.model_dump())

    async def programs(self) -> list[PublicProgramDTO]:
        counts = await self.db.registry.projects_count_by_program()
        return [
            PublicProgramDTO(
                **program_short(p).model_dump(),
                projects_count=counts.get(p.id, 0),
                last_import_at=p.last_import_at,
            )
            for p in await self.db.registry.get_programs(only_active=True)
        ]

    async def dictionaries(self) -> DictionariesDTO:
        return await RegistryAnalyticsService(self.db).dictionaries()

    async def summary(self, filters: PublicAnalyticsFilterDTO) -> SummaryDTO:
        return await RegistryAnalyticsService(self.db).summary(self._scope(filters))

    async def breakdown(self, group_by: GroupBy, filters: PublicAnalyticsFilterDTO) -> BreakdownDTO:
        return await RegistryAnalyticsService(self.db).breakdown(group_by, self._scope(filters))
