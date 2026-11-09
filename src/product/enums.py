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


FILE_FIELD_TYPES = {FieldType.PHOTO, FieldType.FILE}
