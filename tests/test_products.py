from datetime import date, timedelta

import pytest

from tests.conftest import by_ru, data, tr


@pytest.fixture
def fund(api, role_ids):
    headers, _ = api.staff(role_id=role_ids["FUND_OPERATOR"])
    return headers


@pytest.fixture
def bank_pair(banks):
    usable = [
        b
        for b in banks
        if b.get("is_active", True) and "SELF_EMPLOYED" in (b.get("allowed_subject_types") or [])
    ]
    if len(usable) < 1 or len(banks) < 2:
        pytest.skip("Нужен активный банк для SELF_EMPLOYED и ещё один банк")
    other = next(b for b in banks if b["id"] != usable[0]["id"])
    return usable[0], other


def available_ids(api, headers, subject_type=None):
    query = f"?subject_type={subject_type}" if subject_type else ""
    return [p["id"] for p in data(api.client.get(f"/api/v1/products{query}", headers=headers))]


def create_application(api, headers, product_id, bank_id=None, subject_type="SELF_EMPLOYED"):
    body = {"product_id": product_id, "subject_type": subject_type}
    if bank_id is not None:
        body["bank_id"] = bank_id
    r = api.client.post("/api/v1/applications", headers=headers, json=body)
    if r.status_code == 201:
        api.application_ids.append(data(r)["id"])
    return r


def test_fund_builds_and_publishes_product(api, fund, bank_pair, applicant):
    c = api.client
    bank, _ = bank_pair

    category = api.category(fund)
    r = c.post(
        "/api/v1/fund/products",
        headers=fund,
        json={"translations": tr("TEST П", "TEST M", "TEST P")},
    )
    assert r.status_code == 422
    r = c.post(
        "/api/v1/fund/products",
        headers=fund,
        json={"category_id": category["id"], "translations": tr("TEST П", "TEST M", "TEST P")},
    )
    assert r.status_code == 201, r.text
    product = data(r)
    api.product_ids.append(product["id"])
    assert product["category"]["id"] == category["id"]
    assert product["status"] == "DRAFT" and product["stages"] == []
    assert product["allowed_subject_types"] == ["YATT", "MCHJ", "SELF_EMPLOYED"]

    publish = f"/api/v1/fund/products/{product['id']}/publish"
    r = c.post(publish, headers=fund)
    assert r.status_code == 400
    assert r.json()["code"] == "product_not_ready"
    assert [e["field"] for e in r.json()["errors"]] == ["bank_ids", "stages"]

    c.patch(f"/api/v1/fund/products/{product['id']}", headers=fund, json={"bank_ids": [bank["id"]]})
    stage_body = {"number": 1, "translations": tr("Этап", "Bosqich", "Stage")}
    r = c.post(f"/api/v1/fund/products/{product['id']}/stages", headers=fund, json=stage_body)
    assert r.status_code == 201
    stage_id = data(r)["stages"][0]["id"]
    r = c.post(f"/api/v1/fund/products/{product['id']}/stages", headers=fund, json=stage_body)
    assert r.status_code == 409 and r.json()["code"] == "stage_number_taken"

    r = c.post(publish, headers=fund)
    assert r.status_code == 400
    assert [e["field"] for e in r.json()["errors"]] == ["stages.1.fields"]

    r = c.post(
        f"/api/v1/fund/products/{product['id']}/stages/{stage_id}/fields",
        headers=fund,
        json={"field_type": "EMAIL", "translations": tr("Почта", "Pochta", "Mail")},
    )
    assert r.status_code == 201
    field = data(r)["stages"][0]["fields"][0]
    assert field["field_type"] == "EMAIL" and field["is_required"] and field["max_files"] == 1

    assert product["id"] not in available_ids(api, applicant)
    r = c.post(publish, headers=fund)
    assert r.status_code == 200 and data(r)["status"] == "PUBLISHED"
    assert product["id"] in available_ids(api, applicant, "SELF_EMPLOYED")

    r = c.get(f"/api/v1/products/{product['id']}", headers=applicant)
    assert r.status_code == 200
    assert data(r)["stages"][0]["fields"][0]["translations"][1] == {
        "language": "uz",
        "name": "Pochta",
    }

    r = c.post(f"/api/v1/fund/products/{product['id']}/archive", headers=fund)
    assert r.status_code == 200 and data(r)["status"] == "ARCHIVED"
    assert product["id"] not in available_ids(api, applicant)
    assert c.get(f"/api/v1/products/{product['id']}", headers=applicant).status_code == 404


def test_product_management_permissions(api, role_ids, bank_pair, applicant):
    c = api.client
    bank_h, _ = api.staff(role_id=role_ids["BANK_EMPLOYEE"], bank_id=bank_pair[0]["id"])
    body = {"translations": tr("TEST П", "TEST M", "TEST P")}

    assert c.post("/api/v1/fund/products", headers=applicant, json=body).status_code == 403
    assert c.get("/api/v1/products", headers=applicant).status_code == 200
    assert c.get("/api/v1/products", headers=bank_h).status_code == 403
    assert c.post("/api/v1/fund/products", headers=bank_h, json=body).status_code == 403


def test_product_is_locked_after_application(api, fund, bank_pair, applicant):
    c = api.client
    bank, _ = bank_pair
    product = api.product(fund, [bank["id"]])
    base = f"/api/v1/fund/products/{product['id']}"

    assert create_application(api, applicant, product["id"]).status_code == 201

    detail = data(c.get(base, headers=fund))
    assert detail["applications_count"] == 1 and detail["is_locked"]

    stage_body = {"number": 2, "translations": tr("Ещё", "Yana", "More")}
    r = c.post(f"{base}/stages", headers=fund, json=stage_body)
    assert r.status_code == 409 and r.json()["code"] == "product_locked"
    field_id = product["stages"][0]["fields"][0]["id"]
    assert c.delete(f"{base}/fields/{field_id}", headers=fund).status_code == 409
    r = c.delete(base, headers=fund)
    assert r.status_code == 409 and r.json()["code"] == "product_in_use"

    renamed = tr("TEST Новое", "TEST Yangi", "TEST Renamed")
    r = c.patch(base, headers=fund, json={"translations": renamed})
    assert r.status_code == 200
    assert [t["name"] for t in data(r)["translations"]] == [t["name"] for t in renamed]

    r = c.post(f"{base}/copy", headers=fund)
    assert r.status_code == 201
    copy = data(r)
    api.product_ids.append(copy["id"])
    assert copy["status"] == "DRAFT" and copy["copied_from_id"] == product["id"]
    assert not copy["is_locked"]
    assert [b["id"] for b in copy["banks"]] == [bank["id"]]
    assert [f["field_type"] for f in copy["stages"][0]["fields"]] == ["NUMBER", "PHOTO", "STRING"]
    assert copy["stages"][0]["id"] != product["stages"][0]["id"]


def test_applicant_fills_product_form(api, fund, bank_pair, applicant, photo_upload):
    c = api.client
    bank, other_bank = bank_pair
    product = api.product(fund, [bank["id"]])
    stage = product["stages"][0]
    number, photo, comment = stage["fields"]

    r = create_application(api, applicant, product["id"], bank_id=other_bank["id"])
    assert r.status_code in (400, 404)
    r = create_application(api, applicant, product["id"])
    assert r.status_code == 201, r.text
    app_id = data(r)["id"]
    assert data(r)["product"]["id"] == product["id"]

    def progress():
        items = data(c.get("/api/v1/applications?per_page=100", headers=applicant))["items"]
        listed = next(item for item in items if item["id"] == app_id)["form_progress"]
        detail = data(c.get(f"/api/v1/applications/{app_id}", headers=applicant))["form_progress"]
        assert listed == detail
        return listed

    assert progress() == {"stages_total": 1, "stages_complete": 0, "is_complete": False}

    check = data(c.get(f"/api/v1/applications/{app_id}/submission-check", headers=applicant))
    assert not check["is_ready"] and check["product_available"]
    assert set(check["missing"]) == {"bank_id", f"fields.{number['id']}", f"fields.{photo['id']}"}

    stage_url = f"/api/v1/applications/{app_id}/stages/{stage['id']}"
    r = c.put(stage_url, headers=applicant, json={"values": {str(number["id"]): "abc"}})
    assert r.status_code == 400 and r.json()["code"] == "field_value_invalid"
    assert r.json()["errors"][0]["field"] == f"values.{number['id']}"
    r = c.put(stage_url, headers=applicant, json={"values": {str(photo["id"]): "x"}})
    assert r.status_code == 400
    r = c.put(stage_url, headers=applicant, json={"values": {"999999999": "1"}})
    assert r.status_code == 400

    r = c.put(
        stage_url,
        headers=applicant,
        json={"values": {str(number["id"]): "1 500,50", str(comment["id"]): " hi "}},
    )
    assert r.status_code == 200, r.text
    saved = data(r)[0]  # ответ — вся видимая анкета
    values = {f["id"]: f["value"] for f in saved["fields"]}
    assert values[number["id"]] == "1500.5" and values[comment["id"]] == "hi"
    assert not saved["is_complete"]

    files_url = f"/api/v1/applications/{app_id}/fields"
    r = c.post(f"{files_url}/{number['id']}/files", headers=applicant, files=photo_upload())
    assert r.status_code == 400 and r.json()["code"] == "file_field"
    uploaded = []
    for name in ("a.png", "b.png"):
        r = c.post(f"{files_url}/{photo['id']}/files", headers=applicant, files=photo_upload(name))
        assert r.status_code == 201, r.text
        uploaded.append(data(r))
    r = c.post(f"{files_url}/{photo['id']}/files", headers=applicant, files=photo_upload())
    assert r.status_code == 400 and r.json()["code"] == "field_file_limit_exceeded"

    assert c.get(uploaded[0]["url"], headers=applicant).status_code == 200
    assert c.delete(uploaded[1]["url"], headers=applicant).status_code == 200

    r = c.put(
        f"/api/v1/applications/{app_id}/bank", headers=applicant, json={"bank_id": bank["id"]}
    )
    assert r.status_code == 200, r.text

    check = data(c.get(f"/api/v1/applications/{app_id}/submission-check", headers=applicant))
    assert check["is_ready"], check["missing"]
    assert progress() == {"stages_total": 1, "stages_complete": 1, "is_complete": True}

    r = c.put(stage_url, headers=applicant, json={"values": {str(comment["id"]): None}})
    form = data(c.get(f"/api/v1/applications/{app_id}", headers=applicant))["form"]
    fields = {f["id"]: f for f in form[0]["fields"]}
    assert fields[comment["id"]]["value"] is None
    assert len(fields[photo["id"]]["files"]) == 1
    assert form[0]["is_complete"]


def test_product_availability_rules(api, fund, bank_pair, applicant):
    c = api.client
    bank, _ = bank_pair
    r = c.post("/api/v1/applications", headers=applicant, json={"subject_type": "SELF_EMPLOYED"})
    assert r.status_code == 422
    r = c.post(
        "/api/v1/applications",
        headers=applicant,
        json={"product_id": 999999999, "subject_type": "SELF_EMPLOYED"},
    )
    assert r.status_code == 400 and r.json()["code"] == "product_not_available"

    only_llc = api.product(fund, [bank["id"]], subject_types=["MCHJ"])
    r = create_application(api, applicant, only_llc["id"])
    assert r.status_code == 400 and r.json()["code"] == "product_not_available"
    assert only_llc["id"] not in available_ids(api, applicant, "SELF_EMPLOYED")
    assert only_llc["id"] in available_ids(api, applicant, "MCHJ")

    draft = api.product(fund, [bank["id"]], publish=False)
    assert create_application(api, applicant, draft["id"]).status_code == 400

    expired = api.product(fund, [bank["id"]])
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    r = c.patch(
        f"/api/v1/fund/products/{expired['id']}",
        headers=fund,
        json={"accept_from": "2020-01-01", "accept_to": yesterday},
    )
    assert r.status_code == 200, r.text
    assert expired["id"] not in available_ids(api, applicant)
    assert create_application(api, applicant, expired["id"]).status_code == 400


def test_translations_require_each_language_once(api, fund):
    c = api.client
    url = "/api/v1/fund/products"
    ru, uz, en = tr("TEST П", "TEST M", "TEST P")
    category_id = api.category(fund)["id"]

    for translations in ([ru, uz], [ru, uz, en, ru], [ru, ru, en], [ru, uz, {**en, "name": " "}]):
        r = c.post(
            url, headers=fund, json={"category_id": category_id, "translations": translations}
        )
        assert r.status_code == 422, translations

    partial = [{**ru, "description": "Описание"}, uz, en]
    body = {"category_id": category_id, "translations": partial}
    assert c.post(url, headers=fund, json=body).status_code == 422

    r = c.post(url, headers=fund, json={"category_id": category_id, "translations": [en, ru, uz]})
    assert r.status_code == 201, r.text
    product = data(r)
    api.product_ids.append(product["id"])
    assert [t["language"] for t in product["translations"]] == ["ru", "uz", "en"]

    r = c.patch(f"{url}/{product['id']}", headers=fund, json={"translations": [ru, uz]})
    assert r.status_code == 422
    r = c.post(
        f"{url}/{product['id']}/stages",
        headers=fund,
        json={"number": 1, "translations": [ru, ru, en]},
    )
    assert r.status_code == 422


def test_field_types_catalog(api, fund, applicant, role_ids, bank_pair):
    c = api.client
    r = c.get("/api/v1/products/field-types", headers=fund)
    assert r.status_code == 200
    items = {item["type"]: item for item in data(r)}
    assert list(items) == [
        "STRING",
        "NUMBER",
        "DATE",
        "PHONE",
        "EMAIL",
        "PHOTO",
        "FILE",
        "SELECT",
        "RADIO",
        "CHECKBOX",
    ]
    assert [t["language"] for t in items["PHONE"]["translations"]] == ["ru", "uz", "en"]
    assert items["PHONE"]["pattern"] and not items["PHONE"]["is_file"]
    assert items["PHOTO"]["is_file"] and items["PHOTO"]["max_files_limit"] == 10
    assert "application/pdf" in items["FILE"]["allowed_content_types"]
    assert items["STRING"]["max_length"] == 2000
    for choice in ("SELECT", "RADIO", "CHECKBOX"):
        assert items[choice]["has_options"] and not items[choice]["is_file"]
        assert items[choice]["min_options"] == 2 and items[choice]["max_options"] == 50
    assert items["CHECKBOX"]["multiple"] and not items["SELECT"]["multiple"]
    assert not items["STRING"]["has_options"]

    assert c.get("/api/v1/products/field-types", headers=applicant).status_code == 200
    bank_h, _ = api.staff(role_id=role_ids["BANK_EMPLOYEE"], bank_id=bank_pair[0]["id"])
    assert c.get("/api/v1/products/field-types", headers=bank_h).status_code == 403


def test_product_categories(api, fund, bank_pair, applicant):
    c = api.client
    bank, _ = bank_pair
    url = "/api/v1/fund/product-categories"

    body = {"translations": tr("TEST К", "TEST K", "TEST C")}
    assert c.post(url, headers=applicant, json=body).status_code == 403
    r = c.post(url, headers=fund, json={"translations": tr("TEST К", "TEST K", "TEST C")[:2]})
    assert r.status_code == 422

    category = api.category(fund)
    other = api.category(fund)
    inactive = api.category(fund, active=False)
    assert category["products_count"] == 0

    r = c.post(
        "/api/v1/fund/products",
        headers=fund,
        json={"category_id": inactive["id"], "translations": tr("TEST П", "TEST M", "TEST P")},
    )
    assert r.status_code == 400 and r.json()["code"] == "product_category_inactive"
    r = c.post(
        "/api/v1/fund/products",
        headers=fund,
        json={"category_id": 999999999, "translations": tr("TEST П", "TEST M", "TEST P")},
    )
    assert r.status_code == 404 and r.json()["code"] == "product_category_not_found"

    product = api.product(fund, [bank["id"]], category_id=category["id"])
    assert product["category"]["id"] == category["id"]
    assert data(c.get(f"{url}/{category['id']}", headers=fund))["products_count"] == 1

    categories = {x["id"]: x for x in data(c.get("/api/v1/products/categories", headers=applicant))}
    assert categories[category["id"]]["products_count"] == 1
    assert other["id"] not in categories and inactive["id"] not in categories
    query = f"/api/v1/products?category_id={category['id']}"
    assert [p["id"] for p in data(c.get(query, headers=applicant))] == [product["id"]]
    query = f"/api/v1/products?category_id={other['id']}"
    assert data(c.get(query, headers=applicant)) == []

    r = c.delete(f"{url}/{category['id']}", headers=fund)
    assert r.status_code == 409 and r.json()["code"] == "product_category_in_use"

    r = c.patch(f"{url}/{category['id']}", headers=fund, json={"is_active": False})
    assert r.status_code == 200 and not data(r)["is_active"]
    assert product["id"] not in available_ids(api, applicant)
    r = create_application(api, applicant, product["id"])
    assert r.status_code == 400 and r.json()["code"] == "product_not_available"

    r = c.patch(
        f"/api/v1/fund/products/{product['id']}", headers=fund, json={"category_id": other["id"]}
    )
    assert r.status_code == 200 and data(r)["category"]["id"] == other["id"]
    assert product["id"] in available_ids(api, applicant)

    assert c.delete(f"{url}/{category['id']}", headers=fund).status_code == 200
    api.category_ids.remove(category["id"])
    assert c.get(f"{url}/{category['id']}", headers=fund).status_code == 404


def test_public_catalog_endpoints(api, fund, banks):
    c = api.client
    category = api.category(fund)
    product = api.product(fund, [banks[0]["id"]], category_id=category["id"], publish=False)
    for path in (
        "/api/v1/fund/product-categories",
        f"/api/v1/fund/product-categories/{category['id']}",
        "/api/v1/banks",
        f"/api/v1/banks/{banks[0]['id']}",
        "/api/v1/fund/products",
        f"/api/v1/fund/products?category_id={category['id']}",
        f"/api/v1/fund/products/{product['id']}",
    ):
        assert c.get(path).status_code == 200, path
    assert c.get("/api/v1/fund/product-categories/999999999").status_code == 404
    assert c.get("/api/v1/banks/999999999").status_code == 404

    body = {"translations": tr("TEST К", "TEST K", "TEST C")}
    assert c.post("/api/v1/fund/product-categories", json=body).status_code == 401
    assert c.post("/api/v1/banks", json={"code": "test_x", "name": "TEST"}).status_code == 401
    assert c.post("/api/v1/fund/products", json={"category_id": category["id"]}).status_code == 401
    assert c.get("/api/v1/fund/products/999999999").status_code == 404
    assert c.patch(f"/api/v1/fund/products/{product['id']}", json={}).status_code == 401
    assert c.post(f"/api/v1/fund/products/{product['id']}/publish").status_code == 401
    assert c.get("/api/v1/products").status_code == 401


# ---------- поля с вариантами и условный показ ----------


def test_choice_fields_require_options_and_validate_rules(api, fund, bank_pair):
    c = api.client
    bank, _ = bank_pair
    product = api.product(fund, [bank["id"]], publish=False)
    pid = product["id"]
    base = f"/api/v1/fund/products/{pid}"
    stage1 = product["stages"][0]
    number = stage1["fields"][0]

    # options только для полей с выбором и обязательны для них
    r = c.post(
        f"{base}/stages/{stage1['id']}/fields",
        headers=fund,
        json={"field_type": "SELECT", "translations": tr("Цвет", "Rang", "Colour")},
    )
    assert r.status_code == 422, r.text
    r = c.post(
        f"{base}/stages/{stage1['id']}/fields",
        headers=fund,
        json={
            "field_type": "STRING",
            "translations": tr("Текст", "Matn", "Text"),
            "options": [{"translations": tr("А", "A", "A")}, {"translations": tr("Б", "B", "B")}],
        },
    )
    assert r.status_code == 422, r.text
    r = c.post(
        f"{base}/fields/{number['id']}/options",
        headers=fund,
        json={"translations": tr("Лишний", "Ortiqcha", "Extra")},
    )
    assert r.status_code == 400 and r.json()["code"] == "field_options"

    r = c.post(
        f"{base}/stages/{stage1['id']}/fields",
        headers=fund,
        json={
            "field_type": "RADIO",
            "translations": tr("Цвет", "Rang", "Colour"),
            "sort_order": 5,
            "options": [
                {"translations": tr("Красный", "Qizil", "Red")},
                {"translations": tr("Синий", "Koʻk", "Blue")},
            ],
        },
    )
    assert r.status_code == 201, r.text
    colour = by_ru(data(r)["stages"][0]["fields"])["Цвет"]
    red, blue = (o["id"] for o in colour["options"])
    assert colour["field_type"] == "RADIO" and colour["visible_when"] is None

    # условие: не то поле / чужой вариант / управляющее поле ниже цели
    def add_field(body):
        return c.post(f"{base}/stages/{stage1['id']}/fields", headers=fund, json=body)

    for visible_when in (
        {"field_id": number["id"], "option_ids": [red]},
        {"field_id": colour["id"], "option_ids": [999999999]},
        {"field_id": 999999999, "option_ids": [red]},
    ):
        r = add_field(
            {
                "field_type": "STRING",
                "translations": tr("Фрукт", "Meva", "Fruit"),
                "sort_order": 6,
                "visible_when": visible_when,
            }
        )
        assert r.status_code == 400 and r.json()["code"] == "field_condition", r.text
        assert r.json()["errors"][0]["field"].endswith(".visible_when")
    r = add_field(
        {
            "field_type": "STRING",
            "translations": tr("Фрукт", "Meva", "Fruit"),
            "sort_order": 4,  # выше управляющего поля (sort_order 5)
            "visible_when": {"field_id": colour["id"], "option_ids": [red]},
        }
    )
    assert r.status_code == 400 and r.json()["code"] == "field_condition"
    r = add_field(
        {
            "field_type": "STRING",
            "translations": tr("Фрукт", "Meva", "Fruit"),
            "sort_order": 6,
            "visible_when": {"field_id": colour["id"], "option_ids": [red, red]},
        }
    )
    assert r.status_code == 201, r.text
    fruit = by_ru(data(r)["stages"][0]["fields"])["Фрукт"]
    assert fruit["visible_when"] == {"field_id": colour["id"], "option_ids": [red]}

    # этап-цель должен быть позже управляющего поля
    r = c.post(
        f"{base}/stages",
        headers=fund,
        json={
            "number": 2,
            "translations": tr("Синее", "Koʻk", "Blue"),
            "visible_when": {"field_id": colour["id"], "option_ids": [blue]},
        },
    )
    assert r.status_code == 201, r.text
    stage2 = by_ru(data(r)["stages"])["Синее"]
    assert stage2["visible_when"] == {"field_id": colour["id"], "option_ids": [blue]}
    # перенумерация, ломающая условие, отклоняется целиком
    r = c.patch(f"{base}/stages/{stage1['id']}", headers=fund, json={"number": 3})
    assert r.status_code == 400 and r.json()["code"] == "field_condition"
    assert r.json()["errors"][0]["field"] == "stages.2.visible_when"
    # перестановка поля выше управляющего тоже
    r = c.patch(f"{base}/fields/{fruit['id']}", headers=fund, json={"sort_order": 1})
    assert r.status_code == 400 and r.json()["code"] == "field_condition"

    # зависимые есть — удалять поле, вариант и менять тип на невыборный нельзя
    for method, path in (
        ("delete", f"{base}/fields/{colour['id']}"),
        ("delete", f"{base}/options/{red}"),
        ("delete", f"{base}/stages/{stage1['id']}"),
    ):
        r = getattr(c, method)(path, headers=fund)
        assert r.status_code == 409 and r.json()["code"] == "field_in_use_by_condition", path
    r = c.patch(f"{base}/fields/{colour['id']}", headers=fund, json={"field_type": "STRING"})
    assert r.status_code == 409 and r.json()["code"] == "field_in_use_by_condition"
    # смена RADIO → SELECT сохраняет варианты
    r = c.patch(f"{base}/fields/{colour['id']}", headers=fund, json={"field_type": "SELECT"})
    assert r.status_code == 200, r.text
    colour = by_ru(data(r)["stages"][0]["fields"])["Цвет"]
    assert colour["field_type"] == "SELECT" and len(colour["options"]) == 2

    # варианты: изменение, снятие условия, удаление
    r = c.patch(
        f"{base}/options/{blue}",
        headers=fund,
        json={"translations": tr("Голубой", "Havorang", "Light blue"), "sort_order": 9},
    )
    assert r.status_code == 200, r.text
    assert by_ru(by_ru(data(r)["stages"][0]["fields"])["Цвет"]["options"])["Голубой"]["id"] == blue
    r = c.patch(f"{base}/stages/{stage2['id']}", headers=fund, json={"visible_when": None})
    assert r.status_code == 200 and by_ru(data(r)["stages"])["Синее"]["visible_when"] is None
    r = c.delete(f"{base}/options/{blue}", headers=fund)
    assert r.status_code == 200, r.text
    assert len(by_ru(data(r)["stages"][0]["fields"])["Цвет"]["options"]) == 1

    # публикация требует минимум два варианта
    r = c.post(
        f"{base}/stages/{stage2['id']}/fields",
        headers=fund,
        json={"field_type": "STRING", "translations": tr("Оттенок", "Tus", "Shade")},
    )
    assert r.status_code == 201
    r = c.post(f"{base}/publish", headers=fund)
    assert r.status_code == 400 and r.json()["code"] == "product_not_ready"
    assert [e["field"] for e in r.json()["errors"]] == [f"stages.1.fields.{colour['id']}.options"]
    r = c.post(
        f"{base}/fields/{colour['id']}/options",
        headers=fund,
        json={"translations": tr("Зелёный", "Yashil", "Green")},
    )
    assert r.status_code == 201
    r = c.post(f"{base}/publish", headers=fund)
    assert r.status_code == 200, r.text


def test_conditional_form_flow(api, fund, bank_pair, applicant, photo_upload):
    c = api.client
    bank, _ = bank_pair
    product = api.conditional_product(fund, [bank["id"]])
    stages = by_ru(product["stages"])
    s1, s2, s3 = stages["Основное"], stages["Синее"], stages["Сок"]
    f1 = by_ru(s1["fields"])
    amount, colour, fruit, extras = f1["Сумма"], f1["Цвет"], f1["Фрукт"], f1["Дополнительно"]
    red, blue = (by_ru(colour["options"])[n]["id"] for n in ("Красный", "Синий"))
    jam, juice = (by_ru(extras["options"])[n]["id"] for n in ("Джем", "Сок"))
    shade, photo = (by_ru(s2["fields"])[n] for n in ("Оттенок", "Фото"))
    flavour = by_ru(s3["fields"])["Вкус"]

    # заявителю в каталоге видна полная структура с условиями
    r = c.get(f"/api/v1/products/{product['id']}", headers=applicant)
    assert r.status_code == 200
    assert by_ru(data(r)["stages"])["Синее"]["visible_when"] == {
        "field_id": colour["id"],
        "option_ids": [blue],
    }

    r = create_application(api, applicant, product["id"], bank_id=bank["id"])
    assert r.status_code == 201, r.text
    app_id = data(r)["id"]
    app_url = f"/api/v1/applications/{app_id}"

    def form():
        return by_ru(data(c.get(app_url, headers=applicant))["form"])

    def save(stage, values):
        return c.put(f"{app_url}/stages/{stage['id']}", headers=applicant, json={"values": values})

    def missing():
        return set(data(c.get(f"{app_url}/submission-check", headers=applicant))["missing"])

    # до выбора: только этап 1 без «Фрукт»; скрытые обязательные не требуются
    visible = form()
    assert list(visible) == ["Основное"]
    assert set(by_ru(visible["Основное"]["fields"])) == {"Сумма", "Цвет", "Дополнительно"}
    assert missing() == {f"fields.{amount['id']}", f"fields.{colour['id']}"}
    assert data(c.get(app_url, headers=applicant))["form_progress"]["stages_total"] == 1

    # скрытые этап / поле недоступны
    r = save(s2, {str(shade["id"]): "тёмный"})
    assert r.status_code == 400 and r.json()["code"] == "stage_hidden"
    r = save(s1, {str(fruit["id"]): "яблоко"})
    assert r.status_code == 400 and r.json()["code"] == "field_value_invalid"
    assert "hidden" in r.json()["errors"][0]["message"]
    r = c.post(f"{app_url}/fields/{photo['id']}/files", headers=applicant, files=photo_upload())
    assert r.status_code == 400 and r.json()["code"] == "field_hidden"

    # неверные варианты
    r = save(s1, {str(colour["id"]): "999999999"})
    assert r.status_code == 400 and r.json()["code"] == "field_value_invalid"
    r = save(s1, {str(colour["id"]): [red, blue]})
    assert r.status_code == 400 and "one option" in r.json()["errors"][0]["message"]
    r = save(s1, {str(extras["id"]): [jam, 999999999]})
    assert r.status_code == 400

    # красный → появляется «Фрукт» (обязательное)
    r = save(s1, {str(colour["id"]): str(red), str(amount["id"]): "10"})
    assert r.status_code == 200, r.text
    assert [s["number"] for s in data(r)] == [1]
    colour_field = by_ru(data(r)[0]["fields"])["Цвет"]
    assert colour_field["value"] == str(red)
    assert [o["id"] for o in colour_field["selected_options"]] == [red]
    assert "Фрукт" in by_ru(data(r)[0]["fields"])
    assert missing() == {f"fields.{fruit['id']}"}
    r = save(s1, {str(fruit["id"]): "яблоко"})
    assert r.status_code == 200 and missing() == set()

    # синий → «Фрукт» скрыт и его ответ удалён, появился этап 2
    r = save(s1, {str(colour["id"]): blue})  # число вместо строки тоже принимается
    assert r.status_code == 200, r.text
    assert [s["number"] for s in data(r)] == [1, 2]
    assert "Фрукт" not in by_ru(data(r)[0]["fields"])
    assert missing() == {f"fields.{shade['id']}"}
    r = save(s1, {str(colour["id"]): str(red)})
    assert "Фрукт" in by_ru(data(r)[0]["fields"])
    assert by_ru(data(r)[0]["fields"])["Фрукт"]["value"] is None  # ответ не вернулся
    r = save(s1, {str(colour["id"]): str(blue)})
    assert r.status_code == 200

    # этап 2 заполняем, включая фото
    r = save(s2, {str(shade["id"]): "тёмный"})
    assert r.status_code == 200, r.text
    r = c.post(f"{app_url}/fields/{photo['id']}/files", headers=applicant, files=photo_upload())
    assert r.status_code == 201, r.text
    file_url = data(r)["url"]
    assert c.get(file_url, headers=applicant).status_code == 200
    progress = data(c.get(app_url, headers=applicant))["form_progress"]
    assert progress == {"stages_total": 2, "stages_complete": 2, "is_complete": True}

    # CHECKBOX: джем + сок → этап 3; убрали сок → этап 3 и его ответ исчезли
    r = save(s1, {str(extras["id"]): [juice, jam, jam]})
    assert r.status_code == 200, r.text
    assert [s["number"] for s in data(r)] == [1, 2, 3]
    extras_field = by_ru(data(r)[0]["fields"])["Дополнительно"]
    assert extras_field["value"] == ",".join(map(str, sorted((jam, juice))))
    assert {o["id"] for o in extras_field["selected_options"]} == {jam, juice}
    r = save(s3, {str(flavour["id"]): "вишня"})
    assert r.status_code == 200 and missing() == set()
    r = save(s1, {str(extras["id"]): f"{jam}"})  # строка с id тоже принимается
    assert r.status_code == 200 and [s["number"] for s in data(r)] == [1, 2]
    r = save(s1, {str(extras["id"]): [juice]})
    assert r.status_code == 200
    assert by_ru(by_ru(data(r))["Сок"]["fields"])["Вкус"]["value"] is None
    r = save(s1, {str(extras["id"]): []})
    assert r.status_code == 200 and [s["number"] for s in data(r)] == [1, 2]

    # обратно на красный: файл этапа 2 удалён с диска и из заявки
    r = save(s1, {str(colour["id"]): str(red), str(fruit["id"]): "груша"})
    assert r.status_code == 400  # «Фрукт» ещё скрыт в момент запроса
    r = save(s1, {str(colour["id"]): str(red)})
    assert r.status_code == 200 and [s["number"] for s in data(r)] == [1]
    assert c.get(file_url, headers=applicant).status_code == 404
    r = save(s1, {str(fruit["id"]): "груша"})
    assert r.status_code == 200

    # отправка: только видимые обязательные
    assert missing() == set()
    r = c.post(f"{app_url}/submit", headers=applicant)
    assert r.status_code == 200, r.text
    detail = data(c.get(app_url, headers=applicant))
    assert [s["number"] for s in detail["form"]] == [1]
    fields = by_ru(detail["form"][0]["fields"])
    assert fields["Цвет"]["selected_options"][0]["translations"][0]["name"] == "Красный"
    assert fields["Фрукт"]["value"] == "груша"


def test_copy_remaps_conditions(api, fund, bank_pair):
    c = api.client
    bank, _ = bank_pair
    product = api.conditional_product(fund, [bank["id"]], publish=False)
    r = c.post(f"/api/v1/fund/products/{product['id']}/copy", headers=fund)
    assert r.status_code == 201, r.text
    copy = data(r)
    api.product_ids.append(copy["id"])
    assert copy["copied_from_id"] == product["id"]

    old_ids = {f["id"] for s in product["stages"] for f in s["fields"]}
    old_options = {o["id"] for s in product["stages"] for f in s["fields"] for o in f["options"]}
    new_fields = by_ru(by_ru(copy["stages"])["Основное"]["fields"])
    colour, extras = new_fields["Цвет"], new_fields["Дополнительно"]
    assert colour["id"] not in old_ids and len(colour["options"]) == 2
    assert not {o["id"] for o in colour["options"]} & old_options
    red = by_ru(colour["options"])["Красный"]["id"]
    juice = by_ru(extras["options"])["Сок"]["id"]
    assert new_fields["Фрукт"]["visible_when"] == {"field_id": colour["id"], "option_ids": [red]}
    assert by_ru(copy["stages"])["Сок"]["visible_when"] == {
        "field_id": extras["id"],
        "option_ids": [juice],
    }
    r = c.post(f"/api/v1/fund/products/{copy['id']}/publish", headers=fund)
    assert r.status_code == 200, r.text


def test_delete_product_and_stages_with_conditions(api, fund, bank_pair):
    c = api.client
    bank, _ = bank_pair
    base = "/api/v1/fund/products"

    product = api.conditional_product(fund, [bank["id"]], publish=False)
    r = c.delete(f"{base}/{product['id']}", headers=fund)
    assert r.status_code == 200, r.text
    assert c.get(f"{base}/{product['id']}", headers=fund).status_code == 404

    product = api.conditional_product(fund, [bank["id"]], publish=False)
    stages = by_ru(product["stages"])
    r = c.delete(f"{base}/{product['id']}/stages/{stages['Основное']['id']}", headers=fund)
    assert r.status_code == 409, r.text
    for name in ("Синее", "Сок"):
        r = c.delete(f"{base}/{product['id']}/stages/{stages[name]['id']}", headers=fund)
        assert r.status_code == 200, r.text
    r = c.delete(f"{base}/{product['id']}/stages/{stages['Основное']['id']}", headers=fund)
    assert r.status_code == 200, r.text
    assert data(r)["stages"] == []
