from datetime import date, timedelta

import pytest

from tests.conftest import data, tr


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
    values = {f["id"]: f["value"] for f in data(r)["fields"]}
    assert values[number["id"]] == "1500.5" and values[comment["id"]] == "hi"
    assert not data(r)["is_complete"]

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
    assert list(items) == ["STRING", "NUMBER", "DATE", "PHONE", "EMAIL", "PHOTO", "FILE"]
    assert [t["language"] for t in items["PHONE"]["translations"]] == ["ru", "uz", "en"]
    assert items["PHONE"]["pattern"] and not items["PHONE"]["is_file"]
    assert items["PHOTO"]["is_file"] and items["PHOTO"]["max_files_limit"] == 10
    assert "application/pdf" in items["FILE"]["allowed_content_types"]
    assert items["STRING"]["max_length"] == 2000

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
    for path in (
        "/api/v1/fund/product-categories",
        f"/api/v1/fund/product-categories/{category['id']}",
        "/api/v1/banks",
        f"/api/v1/banks/{banks[0]['id']}",
        "/api/v1/fund/products",
        f"/api/v1/fund/products?category_id={category['id']}",
    ):
        assert c.get(path).status_code == 200, path
    assert c.get("/api/v1/fund/product-categories/999999999").status_code == 404
    assert c.get("/api/v1/banks/999999999").status_code == 404

    body = {"translations": tr("TEST К", "TEST K", "TEST C")}
    assert c.post("/api/v1/fund/product-categories", json=body).status_code == 401
    assert c.post("/api/v1/banks", json={"code": "test_x", "name": "TEST"}).status_code == 401
    assert c.post("/api/v1/fund/products", json={"category_id": category["id"]}).status_code == 401
    assert c.get("/api/v1/fund/products/1").status_code == 401
    assert c.get("/api/v1/products").status_code == 401
