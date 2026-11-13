from enum import StrEnum


class Language(StrEnum):
    RU = "ru"
    UZ = "uz"
    EN = "en"


LANGUAGES: tuple[Language, ...] = tuple(Language)


class ProductStatus(StrEnum):
    DRAFT = "DRAFT"  # настраивается Фондом, заявителю не виден
    PUBLISHED = "PUBLISHED"  # доступен заявителям (в пределах сроков приёма)
    ARCHIVED = "ARCHIVED"  # снят с публикации: новые заявки не принимаются


class FieldType(StrEnum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    DATE = "DATE"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    PHOTO = "PHOTO"
    FILE = "FILE"
    SELECT = "SELECT"  # один вариант из списка (выпадающий список)
    RADIO = "RADIO"  # один вариант из списка (радиокнопки)
    CHECKBOX = "CHECKBOX"  # несколько вариантов из списка (флажки)


FILE_FIELD_TYPES = {FieldType.PHOTO, FieldType.FILE}
# Поля с вариантами ответа: имеют `options` и могут управлять условиями показа.
CHOICE_FIELD_TYPES = {FieldType.SELECT, FieldType.RADIO, FieldType.CHECKBOX}
MULTI_CHOICE_FIELD_TYPES = {FieldType.CHECKBOX}
