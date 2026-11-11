import asyncio
import io
import os
import random
import shutil
import struct
import zlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.account.models.user_model import UserORM
from src.config import settings
from src.main import app

ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", settings.SUPERUSER)
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin12345")
TEST_PINFL_PREFIX = "99999"


_Session = async_sessionmaker(create_async_engine(settings.DB_URL, poolclass=NullPool))


def db_run(coro_factory):

    async def runner():
        async with _Session() as session:
            result = await coro_factory(session)
            await session.commit()
            return result

    return asyncio.run(runner())


def db_scalar(stmt, params=None):
    return db_run(lambda s: s.scalar(stmt, params or {}))


def db_all(stmt, params=None):
    async def run(s):
        return (await s.execute(stmt, params or {})).all()

    return db_run(run)


def png_bytes() -> bytes:

    def chunk(kind: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
        + chunk(b"IEND", b"")
    )


def tr(ru: str, uz: str, en: str) -> list[dict[str, str]]:
    return [
        {"language": "ru", "name": ru},
        {"language": "uz", "name": uz},
        {"language": "en", "name": en},
    ]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def data(response):
    return response.json().get("data")


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    if not settings.SSO_MOCK:
        pytest.skip("Интеграционным тестам нужен SSO_MOCK=true (вход через /auth/sso/mock-login)")
    try:
        db_scalar(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"БД недоступна: {exc}")

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def superadmin(client) -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if r.status_code != 200:
        pytest.skip(f"Не удалось войти как {ADMIN_USERNAME}: задайте TEST_ADMIN_PASSWORD")
    return bearer(data(r)["access_token"])


@pytest.fixture(scope="session")
def role_ids(client, superadmin) -> dict[str, int]:
    roles = data(client.get("/api/v1/roles?per_page=100", headers=superadmin))
    roles = roles["items"] if isinstance(roles, dict) else roles
    return {role["code"]: role["id"] for role in roles}


@pytest.fixture(scope="session")
def banks(client, superadmin) -> list[dict]:
    items = data(client.get("/api/v1/banks?per_page=100", headers=superadmin))
    items = items["items"] if isinstance(items, dict) else items
    if len(items) < 2:
        pytest.skip("Нужно минимум два банка в каталоге")
    return items


class Api:
    def __init__(self, client: TestClient, superadmin: dict[str, str]):
        self.client = client
        self.superadmin = superadmin
        self.user_ids: list[int] = []
        self.application_ids: list[int] = []
        self.product_ids: list[int] = []
        self.category_ids: list[int] = []

    @staticmethod
    def fresh_pinfl() -> str:
        while True:
            pinfl = TEST_PINFL_PREFIX + "".join(random.choices("0123456789", k=9))
            if db_scalar(select(UserORM.id).where(UserORM.pinfl == pinfl)) is None:
                return pinfl

    @staticmethod
    def username() -> str:
        return "test_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=12))

    def remember_user(self, user_id: int) -> None:
        if user_id not in self.user_ids:
            self.user_ids.append(user_id)

    def create_user(self, headers: dict[str, str] | None = None, **body):
        body.setdefault("username", self.username())
        body.setdefault("pinfl", self.fresh_pinfl())
        r = self.client.post("/api/v1/users", headers=headers or self.superadmin, json=body)
        if r.status_code == 201:
            self.remember_user(data(r)["id"])
        return r

    def sso_login(self, pinfl: str | None = None, full_name: str = "TEST User"):
        pinfl = pinfl or self.fresh_pinfl()
        r = self.client.post(
            "/api/v1/auth/sso/mock-login", json={"pinfl": pinfl, "full_name": full_name}
        )
        assert r.status_code == 200, r.text
        login = data(r)
        headers = bearer(login["access_token"])
        me = data(self.client.get("/api/v1/auth/me", headers=headers))
        self.remember_user(me["id"])
        return {**login, "headers": headers}, me

    def staff(self, **body):
        pinfl = self.fresh_pinfl()
        r = self.create_user(pinfl=pinfl, **body)
        assert r.status_code == 201, r.text
        login, me = self.sso_login(pinfl)
        return login["headers"], me

    def category(self, headers, active=True):
        r = self.client.post(
            "/api/v1/fund/product-categories",
            headers=headers,
            json={
                "translations": tr("TEST Категория", "TEST Kategoriya", "TEST Category"),
                "is_active": active,
            },
        )
        assert r.status_code == 201, r.text
        self.category_ids.append(data(r)["id"])
        return data(r)

    def product(
        self, headers, bank_ids, subject_types=None, publish=True, category_id=None, uses_bank=True
    ):
        c = self.client
        if category_id is None:
            category_id = self.category(headers)["id"]
        body = {
            "category_id": category_id,
            "translations": tr("TEST Продукт", "TEST Mahsulot", "TEST Product"),
            "bank_ids": bank_ids,
            "uses_bank": uses_bank,
        }
        if subject_types:
            body["allowed_subject_types"] = subject_types
        r = c.post("/api/v1/fund/products", headers=headers, json=body)
        assert r.status_code == 201, r.text
        product_id = data(r)["id"]
        self.product_ids.append(product_id)

        r = c.post(
            f"/api/v1/fund/products/{product_id}/stages",
            headers=headers,
            json={"number": 1, "translations": tr("Проект", "Loyiha", "Project")},
        )
        assert r.status_code == 201, r.text
        stage_id = data(r)["stages"][0]["id"]
        for field in (
            {
                "field_type": "NUMBER",
                "translations": tr("Сумма", "Summa", "Amount"),
            },
            {
                "field_type": "PHOTO",
                "translations": tr("Фото", "Surat", "Photo"),
                "max_files": 2,
            },
            {
                "field_type": "STRING",
                "translations": tr("Комментарий", "Izoh", "Comment"),
                "is_required": False,
            },
        ):
            r = c.post(
                f"/api/v1/fund/products/{product_id}/stages/{stage_id}/fields",
                headers=headers,
                json=field,
            )
            assert r.status_code == 201, r.text
        if publish:
            r = c.post(f"/api/v1/fund/products/{product_id}/publish", headers=headers)
            assert r.status_code == 200, r.text
        return data(r)

    def cleanup(self) -> None:
        async def run(session):
            if self.application_ids:
                await session.execute(
                    text("DELETE FROM applications WHERE id = ANY(:ids)"),
                    {"ids": self.application_ids},
                )
            if self.product_ids:
                await session.execute(
                    text("DELETE FROM applications WHERE product_id = ANY(:ids)"),
                    {"ids": self.product_ids},
                )
                await session.execute(
                    text("DELETE FROM products WHERE id = ANY(:ids)"), {"ids": self.product_ids}
                )
            if self.category_ids:
                await session.execute(
                    text("DELETE FROM products WHERE category_id = ANY(:ids)"),
                    {"ids": self.category_ids},
                )
                await session.execute(
                    text("DELETE FROM product_categories WHERE id = ANY(:ids)"),
                    {"ids": self.category_ids},
                )
            if self.user_ids:
                await session.execute(delete(UserORM).where(UserORM.id.in_(self.user_ids)))

        db_run(run)
        for application_id in self.application_ids:
            folder = Path(settings.MEDIA_PATH) / "applications" / str(application_id)
            if folder.is_dir():
                shutil.rmtree(folder)


@pytest.fixture
def api(client, superadmin) -> Iterator[Api]:
    helper = Api(client, superadmin)
    try:
        yield helper
    finally:
        helper.cleanup()


@pytest.fixture
def photo_upload():
    return lambda name="photo.png": {"file": (name, io.BytesIO(png_bytes()), "image/png")}


@pytest.fixture
def applicant(api):
    login, _ = api.sso_login(full_name="TEST Applicant")
    headers = login["headers"]
    r = api.client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "phone": "+998901234567",
            "passport_number": "AA" + "".join(random.choices("0123456789", k=7)),
            "inn": "".join(random.choices("0123456789", k=9)),
            "email": "test@example.com",
            "gender": "MALE",
            "date_of_birth": "1995-05-05",
        },
    )
    assert r.status_code == 200 and data(r)["profile_complete"], r.text
    return headers
