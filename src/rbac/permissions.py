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
    PRODUCTS = "products"
    APPLICATIONS = "applications"
    SCORING = "scoring"
    BANK_REVIEW = "bank_review"
    COUNCIL_REVIEW = "council_review"
    ALLOCATION = "allocation"
    BULLETINS = "bulletins"
    FAQ = "faq"
    NEWS = "news"
    EVENTS = "events"
    ABOUT = "about"
    COUNCIL_PROFILES = "council_profiles"
    LEADERSHIP = "leadership"


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
    Module.PRODUCTS: "Продукты",
    Module.APPLICATIONS: "Заявки",
    Module.SCORING: "Скоринг KATM",
    Module.BANK_REVIEW: "Этап банка",
    Module.COUNCIL_REVIEW: "Этап Совета",
    Module.ALLOCATION: "Выделение ресурсов",
    Module.BULLETINS: "Бюллетени Совета",
    Module.FAQ: "FAQ сайта",
    Module.NEWS: "Новости сайта",
    Module.EVENTS: "События сайта",
    Module.ABOUT: "Страница «О нас»",
    Module.COUNCIL_PROFILES: "Члены Совета на сайте",
    Module.LEADERSHIP: "Руководство на сайте",
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
    "products.create": ("Создание продуктов", "Новый продукт и копия существующего"),
    "products.read": ("Просмотр продуктов", "Каталог продуктов; заявитель видит опубликованные"),
    "products.update": ("Изменение продуктов", "Названия, банки, сроки, этапы и поля анкеты"),
    "products.delete": ("Удаление продуктов", "Удаление продукта без заявок"),
    "products.approve": ("Публикация продуктов", "Публикация и снятие с публикации"),
    "applications.create": ("Создание заявки", "Подача заявки заявителем"),
    "applications.read": ("Просмотр заявок", "Просмотр заявок в рамках scope"),
    "applications.update": ("Изменение заявки", "Редактирование черновика, запрос дополнений"),
    "applications.delete": ("Удаление заявки", "Удаление черновика"),
    "applications.approve": ("Направление в Совет", "Подготовка и отправка заявки в Совет"),
    "scoring.read": ("Просмотр скоринга", "Полные причины результата KATM"),
    "scoring.update": ("Повторный скоринг", "Повторная обработка после технической ошибки"),
    "bank_review.read": ("Просмотр заявок банка", "Заявки, направленные в банк сотрудника"),
    "bank_review.update": ("Приём заявки банком", "Принять заявку в рассмотрение"),
    "bank_review.approve": ("Решение банка", "Одобрение или отказ с причиной"),
    "council_review.read": ("Просмотр заявок Совета", "Заявки, направленные члену Совета"),
    "council_review.approve": ("Решение Совета", "«Согласен» / «Отклоняю» с причиной"),
    "allocation.create": ("Фиксация выделения ресурсов", "Внесение факта выделения ресурсов"),
    "allocation.read": ("Просмотр выделения ресурсов", "Просмотр этапа выделения"),
    "allocation.approve": ("Завершение заявки", "Перевод заявки в COMPLETED"),
    "bulletins.create": ("Создание бюллетеней", "Новый бюллетень для членов Совета"),
    "bulletins.read": ("Просмотр бюллетеней", "Все бюллетени и статус подписания"),
    "bulletins.update": ("Изменение бюллетеней", "Данные, файл и срок подписания бюллетеня"),
    "bulletins.delete": ("Удаление бюллетеней", "Удаление неотправленного бюллетеня"),
    "bulletins.approve": ("Отправка бюллетеней", "Отправка членам Совета и аннулирование"),
    "faq.create": ("Создание вопросов FAQ", "Новый вопрос и ответ для сайта"),
    "faq.read": ("Просмотр вопросов FAQ", "Все вопросы, включая скрытые с сайта"),
    "faq.update": ("Изменение вопросов FAQ", "Текст, порядок и показ на сайте"),
    "faq.delete": ("Удаление вопросов FAQ", "Удаление вопроса"),
    "news.create": ("Создание новостей", "Новая новость: сразу, в выбранное время или черновик"),
    "news.read": ("Просмотр новостей", "Все новости, включая черновики и отложенные"),
    "news.update": ("Изменение новостей", "Текст, дата, фото и публикация"),
    "news.delete": ("Удаление новостей", "Удаление новости вместе с фото"),
    "events.create": ("Создание событий", "Новое событие для сайта"),
    "events.read": ("Просмотр событий", "Все события, включая скрытые"),
    "events.update": ("Изменение событий", "Текст, дата и показ на сайте"),
    "events.delete": ("Удаление событий", "Удаление события"),
    "about.create": ("Создание разделов «О нас»", "Новый раздел страницы «О нас»"),
    "about.read": ("Просмотр разделов «О нас»", "Все разделы, включая скрытые"),
    "about.update": ("Изменение разделов «О нас»", "Текст, порядок и показ на сайте"),
    "about.delete": ("Удаление разделов «О нас»", "Удаление раздела"),
    "council_profiles.create": ("Добавление членов Совета на сайт", "Новая карточка члена Совета"),
    "council_profiles.read": ("Просмотр членов Совета на сайте", "Все карточки, включая скрытые"),
    "council_profiles.update": ("Изменение членов Совета на сайте", "Данные, фото, место в списке"),
    "council_profiles.delete": ("Удаление членов Совета с сайта", "Удаление карточки с фото"),
    "leadership.create": ("Добавление руководства на сайт", "Новая карточка руководителя"),
    "leadership.read": ("Просмотр руководства на сайте", "Все карточки, включая скрытые"),
    "leadership.update": ("Изменение руководства на сайте", "Данные, фото, место в списке"),
    "leadership.delete": ("Удаление руководства с сайта", "Удаление карточки с фото"),
}


class RoleCode(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    FUND_OPERATOR = "FUND_OPERATOR"
    BANK_EMPLOYEE = "BANK_EMPLOYEE"
    COUNCIL_MEMBER = "COUNCIL_MEMBER"
    MARKETING = "MARKETING"
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
            "products.create",
            "products.read",
            "products.update",
            "products.delete",
            "products.approve",
            "applications.read",
            "applications.update",
            "applications.approve",
            "scoring.read",
            "scoring.update",
            "bank_review.read",
            "council_review.read",
            "allocation.create",
            "allocation.read",
            "allocation.approve",
            "bulletins.create",
            "bulletins.read",
            "bulletins.update",
            "bulletins.delete",
            "bulletins.approve",
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
    RoleCode.MARKETING: (
        "Маркетинг",
        "Контент сайта: новости, события, FAQ, «О нас», члены Совета и руководство",
        False,
        [
            "faq.create",
            "faq.read",
            "faq.update",
            "faq.delete",
            "news.create",
            "news.read",
            "news.update",
            "news.delete",
            "events.create",
            "events.read",
            "events.update",
            "events.delete",
            "about.create",
            "about.read",
            "about.update",
            "about.delete",
            "council_profiles.create",
            "council_profiles.read",
            "council_profiles.update",
            "council_profiles.delete",
            "leadership.create",
            "leadership.read",
            "leadership.update",
            "leadership.delete",
        ],
    ),
    RoleCode.APPLICANT: (
        "Заявитель",
        "Только свой профиль и свои заявки",
        False,
        [
            "banks.read",
            "products.read",
            "applications.create",
            "applications.read",
            "applications.update",
            "applications.delete",
        ],
    ),
}
