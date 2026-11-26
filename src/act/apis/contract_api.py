"""Договоры исполнителей: ведёт Фонд; исполнитель видит свои (`/my/contracts`)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.act.apis.examples import CONTRACT, PEOPLE
from src.act.schemas.act_schema import ContractCreateDTO, ContractFilterDTO, ContractUpdateDTO
from src.act.services.contract_service import ContractService
from src.common.dependencies import (
    CurrentUserDep,
    DBDep,
    PaginationDep,
    require_any_permission,
    require_permission,
)
from src.common.responses.exceptions import (
    ContractApproverException,
    ContractContractorException,
    ContractDatesException,
    ContractInUseException,
    ContractNotFoundException,
    ContractNumberTakenException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    READ_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/contracts", tags=["Договоры исполнителей"])
my_router = APIRouter(prefix="/my/contracts", tags=["Мои акты выполненных работ"])

FilterDep = Annotated[ContractFilterDTO, Depends()]
NOT_FOUND = {404: error_examples(ContractNotFoundException)}


@router.get(
    "",
    summary="Договоры: поиск по номеру и исполнителю, фильтр по статусу",
    dependencies=[Depends(require_permission(Module.CONTRACTS, Action.READ))],
    responses={200: paginated_example(CONTRACT), **READ_ERRORS},
)
async def get_contracts(db: DBDep, pagination: PaginationDep, filters: FilterDep):
    data = await ContractService(db).get_list(filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Contracts retrieved.")


@router.get(
    "/people",
    summary="Кого можно выбрать в договоре: исполнители и подписывающие руководители",
    description=(
        "`contractors` — активные пользователи с ролью CONTRACTOR и ПИНФЛ; `approvers` — "
        "сотрудники с правом act_signing.approve и ПИНФЛ."
    ),
    dependencies=[Depends(require_any_permission("contracts.create", "contracts.update"))],
    responses={200: success_example(PEOPLE, "People retrieved."), **READ_ERRORS},
)
async def get_people(db: DBDep):
    data = await ContractService(db).people()
    return ResponseBuilder.success(data=data, message="People retrieved.")


@router.post(
    "",
    status_code=201,
    summary="Создать договор с исполнителем",
    description=(
        "Имена в акте (`contractor_name`, `approver_name`) по умолчанию берутся из Ф.И.О.: "
        "фамилия и имя («Ahmadjonov Ziyodbek»)."
    ),
    dependencies=[Depends(require_permission(Module.CONTRACTS, Action.CREATE))],
    responses={
        201: success_example(CONTRACT, "Contract created."),
        **COMMON_ERRORS,
        400: error_examples(
            ContractDatesException, ContractContractorException, ContractApproverException
        ),
        409: error_examples(ContractNumberTakenException),
    },
)
async def create_contract(data: ContractCreateDTO, db: DBDep, user: CurrentUserDep):
    result = await ContractService(db).create(data, user)
    return ResponseBuilder.success(data=result, message="Contract created.", status_code=201)


@router.get(
    "/{contract_id}",
    summary="Договор",
    dependencies=[Depends(require_permission(Module.CONTRACTS, Action.READ))],
    responses={200: success_example(CONTRACT, "Contract retrieved."), **READ_ERRORS, **NOT_FOUND},
)
async def get_contract(contract_id: int, db: DBDep):
    data = await ContractService(db).get_detail(contract_id)
    return ResponseBuilder.success(data=data, message="Contract retrieved.")


@router.patch(
    "/{contract_id}",
    summary="Изменить договор или закрыть его (status=CLOSED)",
    description=(
        "Пока по договору есть отправленные или подписанные акты, номер, дата, исполнитель "
        "и имена сторон не меняются (409 `contract_in_use`): они вошли в подписанное содержимое."
    ),
    dependencies=[Depends(require_permission(Module.CONTRACTS, Action.UPDATE))],
    responses={
        200: success_example(CONTRACT, "Contract updated."),
        **COMMON_ERRORS,
        400: error_examples(
            ContractDatesException, ContractContractorException, ContractApproverException
        ),
        409: error_examples(ContractNumberTakenException, ContractInUseException),
        **NOT_FOUND,
    },
)
async def update_contract(contract_id: int, data: ContractUpdateDTO, db: DBDep):
    result = await ContractService(db).update(contract_id, data)
    return ResponseBuilder.success(data=result, message="Contract updated.")


@router.delete(
    "/{contract_id}",
    summary="Удалить договор без актов",
    dependencies=[Depends(require_permission(Module.CONTRACTS, Action.DELETE))],
    responses={
        200: success_example(None, "Contract deleted."),
        **COMMON_ERRORS,
        409: error_examples(ContractInUseException),
        **NOT_FOUND,
    },
)
async def delete_contract(contract_id: int, db: DBDep):
    await ContractService(db).delete(contract_id)
    return ResponseBuilder.success(message="Contract deleted.")


@my_router.get(
    "",
    summary="Мои договоры",
    dependencies=[Depends(require_permission(Module.ACTS, Action.READ))],
    responses={200: paginated_example(CONTRACT), **READ_ERRORS},
)
async def get_my_contracts(
    db: DBDep, user: CurrentUserDep, pagination: PaginationDep, filters: FilterDep
):
    data = await ContractService(db).my_list(user, filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Contracts retrieved.")
