"""Управление администраторами из консоли.

    python -m src.account.cli create-superuser      # роль SUPER_ADMIN + пользователь settings.SUPERUSER
    python -m src.account.cli create-superuser --if-missing   # ничего не менять, если пользователь уже есть
    python -m src.account.cli set-password <username>

Пароль спрашивается интерактивно либо берётся из переменной окружения
ADMIN_PASSWORD (для неинтерактивного запуска).
"""

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import delete, select

import src.models  # noqa: F401  (регистрирует все ORM-модели)
from src.account.models.user_model import UserORM, UserStatus
from src.auth.models.refresh_token_model import RefreshTokenORM
from src.auth.services.password_service import hash_password
from src.config import settings
from src.database import async_session_maker_null_pool
from src.rbac.models.role_model import RoleORM
from src.rbac.permissions import ROLE_PRESETS, RoleCode

MIN_PASSWORD_LENGTH = 8


def read_password() -> str:
    password = os.environ.get("ADMIN_PASSWORD")

    if password is None:
        password = getpass.getpass("Пароль: ")
        if password != getpass.getpass("Повторите пароль: "):
            sys.exit("Пароли не совпадают.")

    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.")

    return password


async def create_superuser(password: str, *, if_missing: bool = False) -> None:
    async with async_session_maker_null_pool() as session:
        if if_missing:
            exists = await session.scalar(
                select(UserORM.id).where(UserORM.username == settings.SUPERUSER)
            )
            if exists is not None:
                print(f"Суперпользователь {settings.SUPERUSER} уже существует, пропускаем.")
                return

        role = await session.scalar(select(RoleORM).where(RoleORM.code == RoleCode.SUPER_ADMIN))

        if role is None:
            name, description, _, _ = ROLE_PRESETS[RoleCode.SUPER_ADMIN]
            role = RoleORM(
                name=name,
                code=RoleCode.SUPER_ADMIN,
                description=description,
                is_superuser=True,
                is_system=True,
            )
            session.add(role)
            await session.flush()
        elif not role.is_superuser:
            sys.exit(f"Роль {RoleCode.SUPER_ADMIN} существует, но is_superuser=False.")

        user = await session.scalar(select(UserORM).where(UserORM.username == settings.SUPERUSER))

        if user is None:
            user = UserORM(username=settings.SUPERUSER, full_name="Super Admin")
            session.add(user)

        user.role_id = role.id
        user.status = UserStatus.ACTIVE
        user.hashed_password = hash_password(password)

        await session.flush()
        await session.execute(delete(RefreshTokenORM).where(RefreshTokenORM.user_id == user.id))
        await session.commit()

    print(f"Суперпользователь {settings.SUPERUSER} готов.")


async def set_password(username: str, password: str) -> None:
    async with async_session_maker_null_pool() as session:
        user = await session.scalar(select(UserORM).where(UserORM.username == username))

        if user is None:
            sys.exit(f"Пользователь {username} не найден.")

        user.hashed_password = hash_password(password)
        await session.execute(delete(RefreshTokenORM).where(RefreshTokenORM.user_id == user.id))
        await session.commit()

    print(f"Пароль пользователя {username} обновлён.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m src.account.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    create_parser = commands.add_parser("create-superuser")
    create_parser.add_argument(
        "--if-missing",
        action="store_true",
        help="не трогать существующего пользователя (для идемпотентного запуска в Docker)",
    )

    set_password_parser = commands.add_parser("set-password")
    set_password_parser.add_argument("username")

    args = parser.parse_args()
    password = read_password()

    if args.command == "create-superuser":
        asyncio.run(create_superuser(password, if_missing=args.if_missing))
    else:
        asyncio.run(set_password(args.username, password))


if __name__ == "__main__":
    main()
