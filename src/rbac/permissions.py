"""Каталог прав платформы.

Код права — "<модуль>.<действие>". Действия (ТЗ, п. 2.2 «Роли и RBAC»):
create / read / update / delete / approve управляются раздельно.
Роль с is_superuser=True имеет все права без явного назначения.

При добавлении нового права нужна миграция, которая вставит его в таблицу
permissions (см. src/alembic/versions/*_seed_rbac.py).
"""

from enum import StrEnum


class Module(StrEnum):
    USERS = "users"
    ROLES = "roles"
    BANKS = "banks"
    APPLICATIONS = "applications"
    SCORING = "scoring"
    BANK_REVIEW = "bank_review"
    COUNCIL_REVIEW = "council_review"
    ALLOCATION = "allocation"


class Action(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"


MODULE_NAMES: dict[Module, str] = {
    Module.USERS: "Пользователи",
    Module.ROLES: "Роли и права",
    Module.BANKS: "Каталог банков",
    Module.APPLICATIONS: "Заявки",
    Module.SCORING: "Скоринг KATM",
    Module.BANK_REVIEW: "Этап банка",
    Module.COUNCIL_REVIEW: "Этап Совета",
    Module.ALLOCATION: "Выделение ресурсов",
}

ACTION_NAMES: dict[Action, str] = {
    Action.CREATE: "Создание",
    Action.READ: "Просмотр",
    Action.UPDATE: "Изменение",
    Action.DELETE: "Удаление",
    Action.APPROVE: "Утверждение / решение",
}


def permission_code(module: Module | str, action: Action | str) -> str:
    return f"{module}.{action}"


# Полный каталог: code -> (name, description)
PERMISSIONS: dict[str, tuple[str, str]] = {
    "users.create": ("Создание пользователей", "Создание внутренних пользователей"),
    "users.read": ("Просмотр пользователей", "Просмотр, поиск и фильтрация профилей"),
    "users.update": ("Изменение пользователей", "Назначение роли, scope, блокировка"),
    "users.delete": ("Удаление пользователей", "Удаление профилей"),
    "roles.create": ("Создание ролей", "Ведение каталога ролей"),
    "roles.read": ("Просмотр ролей", "Просмотр ролей и матрицы прав"),
    "roles.update": ("Изменение ролей", "Настройка разрешений роли по модулям"),
    "roles.delete": ("Удаление ролей", "Удаление ролей без пользователей"),
    "banks.create": ("Добавление банков", "Ведение каталога банков"),
    "banks.read": ("Просмотр банков", "Каталог банков-партнёров"),
    "banks.update": ("Изменение банков", "Правила выбора банка по типу субъекта"),
    "banks.delete": ("Удаление банков", "Деактивация банков"),
    "applications.create": ("Создание заявки", "Подача заявки заявителем"),
    "applications.read": ("Просмотр заявок", "Просмотр заявок в рамках scope"),
    "applications.update": ("Изменение заявки", "Редактирование черновика, запрос дополнений"),
    "applications.delete": ("Удаление заявки", "Удаление черновика"),
    "applications.approve": ("Направление в Совет", "Подготовка и отправка заявки в Совет"),
    "scoring.read": ("Просмотр скоринга", "Полные причины результата KATM"),
    "scoring.update": ("Повторный скоринг", "Повторная обработка после технической ошибки"),
    "scoring.approve": ("Ручной результат скоринга", "Внесение результата KATM вручную"),
    "bank_review.read": ("Просмотр заявок банка", "Заявки, направленные в банк сотрудника"),
    "bank_review.update": ("Приём заявки банком", "Принять заявку в рассмотрение"),
    "bank_review.approve": ("Решение банка", "Одобрение или отказ с причиной"),
    "council_review.read": ("Просмотр заявок Совета", "Заявки, направленные члену Совета"),
    "council_review.approve": ("Решение Совета", "«Согласен» / «Отклоняю» с причиной"),
    "allocation.create": ("Фиксация выделения ресурсов", "Внесение факта выделения ресурсов"),
    "allocation.read": ("Просмотр выделения ресурсов", "Просмотр этапа выделения"),
    "allocation.approve": ("Завершение заявки", "Перевод заявки в COMPLETED"),
}


class RoleCode(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    FUND_OPERATOR = "FUND_OPERATOR"
    BANK_EMPLOYEE = "BANK_EMPLOYEE"
    COUNCIL_MEMBER = "COUNCIL_MEMBER"
    APPLICANT = "APPLICANT"


# Системные роли создаются миграцией. code -> (name, description, is_superuser, permissions)
ROLE_PRESETS: dict[str, tuple[str, str, bool, list[str]]] = {
    RoleCode.SUPER_ADMIN: (
        "Super Admin",
        "Управление платформой: пользователи, RBAC, справочники, аудит",
        True,
        [],
    ),
    RoleCode.FUND_OPERATOR: (
        "Оператор Фонда",
        "Повседневные бизнес-процессы Фонда: заявки, Совет, финансирование",
        False,
        [
            "users.read",
            "roles.read",
            "banks.read",
            "applications.read",
            "applications.update",
            "applications.approve",
            "scoring.read",
            "scoring.update",
            "scoring.approve",
            "bank_review.read",
            "council_review.read",
            "allocation.create",
            "allocation.read",
            "allocation.approve",
        ],
    ),
    RoleCode.BANK_EMPLOYEE: (
        "Ответственный сотрудник банка",
        "Только заявки, направленные в его банк",
        False,
        [
            "banks.read",
            "applications.read",
            "bank_review.read",
            "bank_review.update",
            "bank_review.approve",
        ],
    ),
    RoleCode.COUNCIL_MEMBER: (
        "Член Совета",
        "Только заявки, направленные ему",
        False,
        [
            "applications.read",
            "council_review.read",
            "council_review.approve",
        ],
    ),
    RoleCode.APPLICANT: (
        "Заявитель",
        "Только свой профиль и свои заявки",
        False,
        [
            "banks.read",
            "applications.create",
            "applications.read",
            "applications.update",
            "applications.delete",
        ],
    ),
}
