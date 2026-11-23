"""Разбор Excel-файлов отдела финансирования в строки реестра.

У каждой программы свой шаблон (`ImportTemplate`). Лист ищется по заголовкам, а не по имени
(имя меняется: «639 рухсат берилган»), строки данных — по номеру в первой колонке.
Суммы ПҚ-60 и ПҚ-400 в файле — в млн сўм, «Кўмак» и инкубации — в сўм; в реестр всё
пишется в сўм. Названия регионов, туманов и банков приводятся к справочникам.
"""

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl

from src.account.models.user_model import Gender
from src.registry.dictionaries import (
    bank_code,
    clean_text,
    district_key,
    district_name,
    key_of,
    region_code,
    sector_of,
    subject_type_of_name,
)
from src.registry.enums import Decision, ImportTemplate, ProjectStatus, RegistrySubjectType

MILLION = Decimal(1_000_000)
EXCEL_EPOCH = datetime(1899, 12, 30)


class TemplateMismatchError(ValueError):
    """В файле нет листа с заголовками нужного шаблона."""


@dataclass
class ParseResult:
    sheet: str
    rows: list[dict] = field(default_factory=list)
    skipped: int = 0
    unknown_regions: set[str] = field(default_factory=set)
    unknown_banks: set[str] = field(default_factory=set)


# ---------- значения ----------


def text(value, limit: int = 500) -> str | None:
    value = clean_text(value)
    if value is None or value.startswith("#"):  # #N/A, #REF!
        return None
    return value[:limit]


def number(value) -> Decimal | None:
    if value is None or isinstance(value, (datetime, date)):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    cleaned = re.sub(r"[^\d,.\-]", "", str(value)).replace(",", ".")
    try:
        return Decimal(cleaned) if cleaned else None
    except InvalidOperation:
        return None


def money(value, unit: Decimal = Decimal(1)) -> Decimal | None:
    amount = number(value)
    if amount is None:
        return None
    return (amount * unit).quantize(Decimal("0.01"))


def integer(value) -> int | None:
    amount = number(value)
    return int(amount) if amount is not None else None


def to_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    match = re.search(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})", str(value))
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def months(value) -> int | None:
    """«60 ой», «60 oy», 60 или дата 1900-02-28 (Excel показал число 60 как дату)."""
    if isinstance(value, datetime):
        if value.year < 1905:
            return (value - EXCEL_EPOCH).days
        return None
    if isinstance(value, (int, float)):
        return int(value) if value >= 1 else None
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else None


def decision(value) -> Decision | None:
    key = key_of(clean_text(value))
    if not key:
        return None
    if "madi" in key or "rad" in key:
        return Decision.REJECTED
    if "qullan" in key or "kullan" in key:
        return Decision.APPROVED
    return None


def gender(value) -> Gender | None:
    return {1: Gender.MALE, 2: Gender.FEMALE}.get(integer(value))


def phone(value) -> str | None:
    return text(value, 100)


def remember(result: ParseResult, region_raw, bank_raw=None) -> tuple[str | None, str | None]:
    region = region_code(region_raw)
    if region is None and clean_text(region_raw):
        result.unknown_regions.add(clean_text(region_raw))
    bank = bank_code(bank_raw) if bank_raw is not None else None
    if bank_raw is not None and bank is None and clean_text(bank_raw):
        result.unknown_banks.add(clean_text(bank_raw))
    return region, bank


def district(value) -> tuple[str | None, str | None]:
    name = district_name(text(value, 255))
    return name, district_key(name)


# ---------- поиск листа ----------

SIGNATURES: dict[ImportTemplate, tuple[str, ...]] = {
    ImportTemplate.PQ60: ("loyihatashabbuskorinomi", "stir", "tumannomi", "kredittaminoti"),
    ImportTemplate.PQ400: ("loyihatashabbuskorinomi", "hududnomi", "kreditsummasi"),
    ImportTemplate.KOMAK: ("fish", "qarzmiqdori", "viloyat", "tuman"),
    ImportTemplate.INCUBATION: ("loyihanomi", "tashabbuskoriifo", "jamgarmaqoplashikerak"),
}


def find_sheet(workbook, template: ImportTemplate):
    wanted = SIGNATURES[template]
    for sheet in workbook.worksheets:
        if sheet.sheet_state != "visible":
            continue
        head = set()
        for row in sheet.iter_rows(min_row=1, max_row=8, values_only=True):
            head.update(key_of(clean_text(v)) for v in row if isinstance(v, str))
        if all(any(w in h for h in head) for w in wanted):
            return sheet
    raise TemplateMismatchError(template.value)


def data_rows(sheet, number_col: int, name_col: int):
    """Строки данных: в колонке номера — целое число."""
    for row in sheet.iter_rows(values_only=True):
        if len(row) <= max(number_col, name_col):
            continue
        num = row[number_col]
        if isinstance(num, bool) or not isinstance(num, (int, float)) or num != int(num):
            continue
        yield int(num), row


def col(row, index):
    return row[index] if index < len(row) else None


# ---------- шаблоны ----------


def parse_pq60(sheet, result: ParseResult) -> None:
    subject_codes = {
        1: RegistrySubjectType.INDIVIDUAL,
        2: RegistrySubjectType.LEGAL_ENTITY,
        3: RegistrySubjectType.SOLE_PROPRIETOR,
    }
    for num, row in data_rows(sheet, 1, 3):
        name = text(col(row, 3))
        if not name:
            result.skipped += 1
            continue
        region, bank = remember(result, col(row, 5), col(row, 0) or col(row, 2))
        dist, dist_key = district(col(row, 6))
        allocated = money(col(row, 18), MILLION)
        credit = money(col(row, 19), MILLION)
        refusal, awaiting = integer(col(row, 21)), integer(col(row, 20))
        if refusal == 1:
            status = ProjectStatus.RETURNED
        elif refusal == 2:
            status = ProjectStatus.CLIENT_REFUSED
        elif credit:
            status = ProjectStatus.CREDIT_ISSUED
        elif awaiting == 1:
            status = ProjectStatus.AWAITING_BANK_REQUEST
        elif allocated:
            status = ProjectStatus.ALLOCATED
        else:
            status = ProjectStatus.IN_PROGRESS
        mahalla = text(col(row, 22), 255)
        if mahalla and "mavjud" in key_of(mahalla):  # «Паспорт серия тизимда мавжуд эмас»
            mahalla = None
        protocol = text(col(row, 16), 255)
        result.rows.append(
            {
                "number": num,
                "applicant_name": name,
                "tin": text(col(row, 4), 20),
                "subject_type": subject_codes.get(integer(col(row, 23))),
                "head_info": text(col(row, 7), 2000),
                "phone": phone(col(row, 8)),
                "region": region,
                "district": dist,
                "district_key": dist_key,
                "mahalla": mahalla,
                "purpose": text(col(row, 9), 4000),
                "sector": sector_of(col(row, 24)),
                "direction": (text(col(row, 25), 255) or "").capitalize() or None,
                "jobs": integer(col(row, 10)),
                "requested_amount": money(col(row, 11), MILLION),
                "term_months": months(col(row, 12)),
                "collateral": text(col(row, 13), 255),
                "application_date": to_date(col(row, 14)),
                "decision": decision(col(row, 15)),
                "council_protocol": protocol,
                "council_date": to_date(protocol),
                "bank": bank,
                "bank_branch": text(col(row, 2), 255),
                "bank_request": text(col(row, 17), 255),
                "allocated_amount": allocated,
                "credit_amount": credit,
                "gender": gender(col(row, 26)),
                "age": integer(col(row, 27)),
                "status": status,
                "note": text(col(row, 28), 4000),
            }
        )


def parse_pq400(sheet, result: ParseResult) -> None:
    for num, row in data_rows(sheet, 0, 2):
        name = text(col(row, 2))
        if not name:
            result.skipped += 1
            continue
        region, bank = remember(result, col(row, 3), col(row, 1))
        allocated = money(col(row, 14), MILLION)
        credit = money(col(row, 15), MILLION)
        protocol = text(col(row, 10), 255)
        result.rows.append(
            {
                "number": num,
                "applicant_name": name,
                "organization": name,
                "subject_type": subject_type_of_name(name),
                "region": region,
                "phone": phone(col(row, 4)),
                "purpose": text(col(row, 5), 4000),
                "requested_amount": money(col(row, 6), MILLION),
                "term_months": months(col(row, 7)),
                "application_date": to_date(col(row, 8)),
                "decision": decision(col(row, 9)),
                "council_protocol": protocol,
                "council_date": to_date(protocol),
                "bank": bank,
                "bank_branch": text(col(row, 1), 255),
                "bank_letter_date": to_date(col(row, 11)),
                "bank_request": text(col(row, 12), 255),
                "order_info": text(col(row, 13), 255),
                "allocated_amount": allocated,
                "credit_amount": credit,
                "status": (
                    ProjectStatus.CREDIT_ISSUED
                    if credit
                    else ProjectStatus.ALLOCATED
                    if allocated
                    else ProjectStatus.IN_PROGRESS
                ),
            }
        )


def parse_komak(sheet, result: ParseResult) -> None:
    for num, row in data_rows(sheet, 0, 1):
        name = text(col(row, 1))
        if not name:
            result.skipped += 1
            continue
        region, _ = remember(result, col(row, 3))
        dist, dist_key = district(col(row, 23) or col(row, 21) or col(row, 4))
        amount = money(col(row, 6))
        financed = "moliyalashtirildi" in key_of(clean_text(col(row, 11)))
        organization = text(col(row, 8))
        if organization and key_of(organization) in ("yatt", "mchj"):
            organization = None
        protocol = text(col(row, 10), 255)
        extra = {
            "mahalla_check": text(col(row, 9)),
            "financing_date": str(to_date(col(row, 12)) or text(col(row, 12)) or "") or None,
            "stage": text(col(row, 11)),
        }
        result.rows.append(
            {
                "number": num,
                "applicant_name": name,
                "organization": organization,
                "subject_type": subject_type_of_name(col(row, 8)),
                "gender": gender(col(row, 15)) or gender(col(row, 2)),
                "phone": phone(col(row, 7)),
                "region": region,
                "district": dist,
                "district_key": dist_key,
                "mahalla": text(col(row, 5), 255),
                "requested_amount": amount,
                "allocated_amount": amount if financed else None,
                "decision": Decision.APPROVED,
                "council_protocol": protocol,
                "council_date": to_date(col(row, 17)) or to_date(protocol),
                "status": ProjectStatus.ALLOCATED if financed else ProjectStatus.IN_PROGRESS,
                "note": text(col(row, 16), 4000),
                "extra": {k: v for k, v in extra.items() if v},
            }
        )


def parse_incubation(sheet, result: ParseResult) -> None:
    for num, row in data_rows(sheet, 0, 2):
        name = text(col(row, 2))
        if not name:
            result.skipped += 1
            continue
        allocated = money(col(row, 11))
        protocol = text(col(row, 10), 255)
        extra = {"program": text(col(row, 3)), "duration": text(col(row, 4))}
        result.rows.append(
            {
                "number": num,
                "applicant_name": name,
                "organization": text(col(row, 1)),
                "subject_type": RegistrySubjectType.INDIVIDUAL,
                "purpose": text(col(row, 5), 4000),
                "project_cost": money(col(row, 6)),
                "requested_amount": money(col(row, 7)),
                "application_date": to_date(col(row, 8)),
                "decision": decision(col(row, 9)),
                "council_protocol": protocol,
                "council_date": to_date(protocol),
                "allocated_amount": allocated,
                "status": ProjectStatus.ALLOCATED if allocated else ProjectStatus.IN_PROGRESS,
                "extra": {k: v for k, v in extra.items() if v},
            }
        )


PARSERS = {
    ImportTemplate.PQ60: parse_pq60,
    ImportTemplate.PQ400: parse_pq400,
    ImportTemplate.KOMAK: parse_komak,
    ImportTemplate.INCUBATION: parse_incubation,
}


def parse_workbook(content: bytes, template: ImportTemplate) -> ParseResult:
    """Синхронный разбор (вызывать в потоке): bytes файла → строки реестра."""
    workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=False)
    try:
        sheet = find_sheet(workbook, template)
        result = ParseResult(sheet=sheet.title)
        PARSERS[template](sheet, result)
        return result
    finally:
        workbook.close()
