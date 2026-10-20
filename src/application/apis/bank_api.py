from fastapi import APIRouter, Depends, Query

from src.application.enums import SubjectType
from src.application.schemas.bank_schema import BankRequestAddDTO, BankRequestUpdateDTO
from src.application.services.bank_service import BankService
from src.common.dependencies import DBDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, CONFLICT, success_example
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/banks", tags=["Каталог банков"])

BANK_EXAMPLE = {
    "id": 1,
    "code": "microcreditbank",
    "name": "Microcreditbank",
    "official_name": "АКБ «Микрокредитбанк»",
    "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
    "is_active": True,
    "sort_order": 1,
}


@router.get(
    "",
    summary="Банки для окна выбора (фильтр по типу субъекта)",
    description="ИП и ООО — все 9 банков; самозанятым — только Microcreditbank, Xalq banki и Agrobank.",
    dependencies=[Depends(require_permission(Module.BANKS, Action.READ))],
    responses={
        200: success_example([BANK_EXAMPLE], "Banks retrieved successfully."),
        **COMMON_ERRORS,
    },
)
async def get_banks(
    db: DBDep,
    subject_type: SubjectType | None = Query(
        None, description="Тип субъекта: YATT, MCHJ, SELF_EMPLOYED"
    ),
    include_inactive: bool = Query(False),
):
    data = await BankService(db).get_banks(subject_type, only_active=not include_inactive)
    return ResponseBuilder.success(data=data, message="Banks retrieved successfully.")


@router.get(
    "/{bank_id}",
    summary="Банк по ID",
    dependencies=[Depends(require_permission(Module.BANKS, Action.READ))],
    responses={200: success_example(BANK_EXAMPLE, "Bank found."), **COMMON_ERRORS},
)
async def get_bank(bank_id: int, db: DBDep):
    data = await BankService(db).get_bank(bank_id)
    return ResponseBuilder.success(data=data, message="Bank found.")


@router.post(
    "",
    summary="Добавление банка в каталог",
    dependencies=[Depends(require_permission(Module.BANKS, Action.CREATE))],
    responses={
        201: success_example(BANK_EXAMPLE, "Bank created successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def create_bank(data: BankRequestAddDTO, db: DBDep):
    bank = await BankService(db).add_bank(data)
    return ResponseBuilder.success(data=bank, message="Bank created successfully.", status_code=201)


@router.patch(
    "/{bank_id}",
    summary="Изменение банка и правил выбора по типу субъекта",
    dependencies=[Depends(require_permission(Module.BANKS, Action.UPDATE))],
    responses={200: success_example(BANK_EXAMPLE, "Bank updated successfully."), **COMMON_ERRORS},
)
async def update_bank(bank_id: int, data: BankRequestUpdateDTO, db: DBDep):
    bank = await BankService(db).update_bank(bank_id, data)
    return ResponseBuilder.success(data=bank, message="Bank updated successfully.")


@router.delete(
    "/{bank_id}",
    summary="Деактивация банка (история заявок сохраняется)",
    dependencies=[Depends(require_permission(Module.BANKS, Action.DELETE))],
    responses={200: success_example(None, "Bank deactivated."), **COMMON_ERRORS},
)
async def deactivate_bank(bank_id: int, db: DBDep):
    await BankService(db).deactivate_bank(bank_id)
    return ResponseBuilder.success(message="Bank deactivated.")
