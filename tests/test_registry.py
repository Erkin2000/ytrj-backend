"""Реестр проектов: программы, импорт Excel по шаблонам, CRUD проектов, аналитика.

Работает только с тестовыми программами (код TEST_…) — загруженные данные отдела не трогаются.
"""

import io
import uuid
from datetime import datetime

import openpyxl
import pytest
from sqlalchemy import text

from tests.conftest import data, db_run

LABELS = [
    {"language": "ru", "name": "TEST Программа"},
    {"language": "uz", "name": "TEST Dastur"},
    {"language": "en", "name": "TEST Programme"},
]


def pq60_workbook() -> bytes:
    """Минимальный файл в шаблоне ПҚ-60: заголовки + 3 строки (суммы в млн сўм)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "буюртмалар номма ном"
    ws.append(["Agrobank", "Т/р", "Банк номи", "Лойиҳа ташаббускори хақида"])
    ws.append([])
    ws.append(
        [None, None, None, "Лойиҳа ташаббускори номи", "СТИР", "Ҳудуд номи", "Туман номи",
         "Раҳбар", "Телефон", "Мақсад", "Иш ўрни", "Сумма", "Муддат", "Кредит таъминоти"]
    )  # fmt: skip
    rows = [
        # bank, №, branch, name, tin, region, district, head, phone, purpose, jobs, sum, term,
        # collateral, date, decision, protocol, request, allocated, credit, awaiting, refusal,
        # mfy, subject, sector, direction, gender, age
        ["Агробанк", 1, "Agrobank", "TEST Алиев Вали", "50205050005127", "Андижон вилоят",
         "Булоқбоши туман", "Алиев", "998901234567", "Тикувчилик", 2, 100, "60 ой", "Суғурта",
         datetime(2025, 8, 28), "Маъқулланди", "05.09.2025 6 сон", "09.09.2025 11-1/742",
         100, 100, None, None, "#N/A", 1, "Ишлаб чикариш", "чеварчилик", 2, 21],
        ["Халқ банки", 2, "Халқ банк", "TEST ЯТТ Каримов", "52011058090034", "Хоразм вилоят",
         "Урганч шахар", "Каримов", "93", "Савдо", 1, 50, 60, "Кафиллик",
         datetime(2026, 2, 1), "Маъқулланди", "13.02.2026 28 сон баён", None,
         50, None, None, 1, None, 3, "Хизмат кўрсатиш", "Савдо", 1, 30],
        ["Халқ банки", 3, "Халқ банк", "TEST Отказник", None, "Хоразм вилоят",
         "Урганч тумани", None, None, "Иссиқхона", 3, 70, datetime(1900, 2, 28), "Суғурта",
         datetime(2026, 3, 1), "Маъқулланди", "10.04.2026 36 сон", None,
         None, None, None, 2, None, 2, "Қишлоқ хўжалиги", "Иссиқхона", 1, 25],
    ]  # fmt: skip
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def registry(client, superadmin):
    """Тестовая программа с шаблоном ПҚ-60; после теста — удаляется вместе с проектами."""
    code = f"TEST_{uuid.uuid4().hex[:8].upper()}"
    r = client.post(
        "/api/v1/registry/programs",
        headers=superadmin,
        json={
            "code": code,
            "kind": "CREDIT",
            "import_template": "PQ60",
            "translations": LABELS,
        },
    )
    assert r.status_code == 201, r.text
    program = data(r)
    yield program

    async def run(session):
        await session.execute(
            text("DELETE FROM registry_projects WHERE program_id = :id"), {"id": program["id"]}
        )
        await session.execute(
            text("DELETE FROM registry_programs WHERE id = :id"), {"id": program["id"]}
        )

    db_run(run)


def upload(client, headers, program_id, content, name="pq60.xlsx"):
    return client.post(
        "/api/v1/registry/import",
        headers=headers,
        data={"program_id": str(program_id)},
        files={"file": (name, io.BytesIO(content), "application/vnd.ms-excel")},
    )


def test_import_and_analytics(client, superadmin, registry):
    pid = registry["id"]
    r = upload(client, superadmin, pid, pq60_workbook())
    assert r.status_code == 200, r.text
    result = data(r)
    assert result["imported"] == 3 and result["replaced"] == 0
    assert result["sheet"] == "буюртмалар номма ном"
    assert result["unknown_regions"] == [] and result["unknown_banks"] == []

    # Повторный импорт заменяет данные программы.
    r = upload(client, superadmin, pid, pq60_workbook())
    assert data(r)["replaced"] == 3

    items = data(client.get(f"/api/v1/registry/projects?program_id={pid}", headers=superadmin))[
        "items"
    ]
    by_name = {i["applicant_name"]: i for i in items}
    first = by_name["TEST Алиев Вали"]
    assert first["status"] == "CREDIT_ISSUED"
    assert first["requested_amount"] == "100000000.00"  # млн → сўм
    assert first["region"]["code"] == "ANDIJAN"
    assert first["bank"]["code"] == "AGROBANK"
    assert first["district"] == "Buloqboshi tumani"
    assert first["gender"] == "FEMALE" and first["subject_type"] == "INDIVIDUAL"
    assert first["sector"] == "PRODUCTION" and first["term_months"] == 60
    assert first["council_date"] == "2025-09-05" and first["mahalla"] is None
    assert by_name["TEST ЯТТ Каримов"]["status"] == "RETURNED"
    refused = by_name["TEST Отказник"]
    assert refused["status"] == "CLIENT_REFUSED" and refused["term_months"] == 60

    summary = data(
        client.get(f"/api/v1/registry/analytics/summary?program_id={pid}", headers=superadmin)
    )
    assert summary["projects"] == 3 and summary["jobs"] == 6
    assert summary["allocated_count"] == 2 and summary["allocated_amount"] == "150000000.00"
    assert summary["credit_count"] == 1 and summary["returned_count"] == 1
    assert summary["returned_amount"] == "50000000.00"
    assert summary["by_gender"] == {"MALE": 2, "FEMALE": 1}

    regions = data(
        client.get(
            f"/api/v1/registry/analytics/breakdown?group_by=region&program_id={pid}",
            headers=superadmin,
        )
    )
    assert [r["key"] for r in regions["rows"]] == ["ANDIJAN", "KHOREZM"]
    assert regions["rows"][1]["translations"][1]["name"] == "Xorazm viloyati"
    assert regions["total"]["projects"] == 3

    districts = data(
        client.get(
            f"/api/v1/registry/analytics/breakdown?group_by=district&program_id={pid}"
            "&region=KHOREZM",
            headers=superadmin,
        )
    )
    assert {r["translations"][0]["name"] for r in districts["rows"]} == {
        "Urganch shahri",
        "Urganch tumani",
    }
    years = data(
        client.get(
            f"/api/v1/registry/analytics/breakdown?group_by=year&program_id={pid}",
            headers=superadmin,
        )
    )
    assert [r["key"] for r in years["rows"]] == ["2025", "2026"]

    # Фильтры: год, поиск, туман в другом написании
    q = f"/api/v1/registry/projects?program_id={pid}"
    assert data(client.get(f"{q}&year=2026", headers=superadmin))["pagination"]["total"] == 2
    assert data(client.get(f"{q}&search=Алиев", headers=superadmin))["pagination"]["total"] == 1
    total = data(client.get(f"{q}&district=Урганч шаҳар", headers=superadmin))["pagination"]
    assert total["total"] == 1

    # Программу с проектами удалить нельзя
    r = client.delete(f"/api/v1/registry/programs/{pid}", headers=superadmin)
    assert r.status_code == 409 and r.json()["code"] == "registry_program_in_use"


def test_import_rejects_bad_files(client, superadmin, registry):
    r = upload(client, superadmin, registry["id"], b"not an excel file", "x.xlsx")
    assert r.status_code == 400 and r.json()["code"] == "registry_import_file"

    wb = openpyxl.Workbook()
    wb.active.append(["Что-то другое"])
    buf = io.BytesIO()
    wb.save(buf)
    r = upload(client, superadmin, registry["id"], buf.getvalue())
    assert r.status_code == 400 and r.json()["code"] == "registry_import_template"


def test_project_crud(client, superadmin, registry):
    base = "/api/v1/registry/projects"
    body = {
        "program_id": registry["id"],
        "applicant_name": "TEST Ручной проект",
        "region": "SAMARKAND",
        "district": "Самарқанд туман",
        "bank": "NBU",
        "requested_amount": "130000000",
        "gender": "FEMALE",
        "jobs": 3,
    }
    r = client.post(base, headers=superadmin, json=body)
    assert r.status_code == 201, r.text
    project = data(r)
    assert project["source"] == "MANUAL" and project["status"] == "IN_PROGRESS"
    assert project["district"] == "Samarqand tumani"

    assert client.post(base, headers=superadmin, json={**body, "region": "MARS"}).status_code == 422
    r = client.post(base, headers=superadmin, json={**body, "program_id": 999999})
    assert r.status_code == 404 and r.json()["code"] == "registry_program_not_found"

    r = client.patch(
        f"{base}/{project['id']}",
        headers=superadmin,
        json={"status": "ALLOCATED", "allocated_amount": "130000000", "note": None},
    )
    assert r.status_code == 200 and data(r)["status"] == "ALLOCATED"

    # Ручной проект переживает импорт программы.
    upload(client, superadmin, registry["id"], pq60_workbook())
    assert client.get(f"{base}/{project['id']}", headers=superadmin).status_code == 200

    assert client.delete(f"{base}/{project['id']}", headers=superadmin).status_code == 200
    assert client.get(f"{base}/{project['id']}", headers=superadmin).status_code == 404


def test_registry_permissions(api, role_ids, registry):
    fund, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    marketing, _ = api.staff(role_id=role_ids["MARKETING"])
    c = api.client
    assert c.get("/api/v1/registry/programs", headers=fund).status_code == 200
    assert c.get("/api/v1/registry/analytics/summary", headers=fund).status_code == 200
    assert c.get("/api/v1/registry/programs", headers=marketing).status_code == 403
    assert c.get("/api/v1/registry/dictionaries").status_code == 401
    dictionaries = data(c.get("/api/v1/registry/dictionaries", headers=fund))
    assert len(dictionaries["regions"]) == 14 and "district" in dictionaries["group_by"]


def test_public_analytics_without_token(client, superadmin, registry):
    """Сайт: только агрегаты, без токена; неактивная программа не попадает."""
    pid = registry["id"]
    assert upload(client, superadmin, pid, pq60_workbook()).status_code == 200
    base = "/api/v1/public/analytics"

    programs = data(client.get(f"{base}/programs"))
    mine = next(p for p in programs if p["id"] == pid)
    assert mine["projects_count"] == 3 and mine["last_import_at"]
    assert "import_template" not in mine

    summary = data(client.get(f"{base}/summary?program_id={pid}"))
    assert summary["projects"] == 3 and summary["allocated_amount"] == "150000000.00"
    regions = data(client.get(f"{base}/breakdown?group_by=region&program_id={pid}"))
    assert [r["key"] for r in regions["rows"]] == ["ANDIJAN", "KHOREZM"]
    assert len(data(client.get(f"{base}/dictionaries"))["regions"]) == 14

    # Поиска и списка проектов на сайте нет; лишний параметр игнорируется.
    assert data(client.get(f"{base}/summary?program_id={pid}&search=Алиев"))["projects"] == 3
    assert client.get("/api/v1/public/analytics/projects").status_code == 404
    assert client.post(f"{base}/summary").status_code == 405

    # Неактивная программа исчезает с сайта.
    r = client.patch(
        f"/api/v1/registry/programs/{pid}", headers=superadmin, json={"is_active": False}
    )
    assert r.status_code == 200
    assert pid not in [p["id"] for p in data(client.get(f"{base}/programs"))]
    assert data(client.get(f"{base}/summary?program_id={pid}"))["projects"] == 0
