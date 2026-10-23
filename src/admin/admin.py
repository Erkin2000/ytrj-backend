"""Админ-панель на SQLAdmin (Tabler UI): вход только для роли с is_superuser.

Интерфейс двуязычный (ru/uz): системные строки SQLAdmin и наши подписи
переводятся через Babel, язык выбирается переключателем в верхней панели
(`?lang=`, сохраняется в cookie).
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend, login_required
from sqladmin.i18n import I18nConfig
from sqlalchemy import func, select
from starlette.requests import Request
from starlette.responses import Response

from src.account.models.user_model import UserORM, UserStatus
from src.admin.i18n import (
    ADMIN_LOCALES,
    DEFAULT_ADMIN_LOCALE,
    TASHKENT_TZ,
    _,
    fmt_dt,
    fmt_money,
    fmt_size,
    register_locales,
)
from src.admin.labels import (
    DECISION_LABELS,
    DEMAND_STATUS_LABELS,
    PIPELINE_GROUPS,
    SCORING_RESULT_LABELS,
    STATUS_LABELS,
    event_label,
    labeled_badge,
    role_badge,
    status_badge,
    status_label,
    subject_label,
)
from src.admin.views import ALL_VIEWS
from src.application.enums import REJECTED_STATUSES, ApplicationStatus
from src.application.models.application_model import ApplicationORM
from src.application.models.bank_model import BankORM
from src.application.workflow import build_progress
from src.auth.services.password_service import verify_password
from src.config import settings
from src.database import async_session_maker, engine
from src.utils.db_manager import DBManager

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class AdminAuth(AuthenticationBackend):
    """Логин/пароль платформы; в админку пускается только суперпользователь."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))

        async with DBManager(session_factory=async_session_maker) as db:
            user = await db.user.get_orm_by_username(username)
            is_valid = await asyncio.to_thread(
                verify_password, password, user.hashed_password if user else None
            )

            if (
                user is None
                or not is_valid
                or user.status != UserStatus.ACTIVE
                or user.role is None
                or not user.role.is_superuser
            ):
                return False

            await db.user.touch_last_login(user.id)
            await db.commit()

        request.session.update({"user_id": user.id, "username": user.username})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")
        if not user_id:
            return False

        async with DBManager(session_factory=async_session_maker) as db:
            access = await db.user.get_access(int(user_id))

        if access is None or not access.is_active or not access.is_superuser:
            request.session.clear()
            return False

        request.state.admin_user = access
        return True


class JamgarmaAdmin(Admin):
    """Admin с дашбордом на главной странице."""

    @login_required
    async def index(self, request: Request) -> Response:
        now = datetime.now(TASHKENT_TZ)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=6)

        async with async_session_maker() as session:
            by_status = dict(
                (
                    await session.execute(
                        select(ApplicationORM.status, func.count()).group_by(ApplicationORM.status)
                    )
                ).all()
            )
            counts = {status.value: by_status.get(status, 0) for status in ApplicationStatus}

            new_today = (
                await session.scalar(
                    select(func.count())
                    .select_from(ApplicationORM)
                    .where(ApplicationORM.created_at >= today_start)
                )
                or 0
            )
            new_week = (
                await session.scalar(
                    select(func.count())
                    .select_from(ApplicationORM)
                    .where(ApplicationORM.created_at >= week_start)
                )
                or 0
            )
            scoring_retry = (
                await session.scalar(
                    select(func.count())
                    .select_from(ApplicationORM)
                    .where(ApplicationORM.scoring_retry_required.is_(True))
                )
                or 0
            )

            users_total = await session.scalar(select(func.count()).select_from(UserORM)) or 0
            users_active = (
                await session.scalar(
                    select(func.count())
                    .select_from(UserORM)
                    .where(UserORM.status == UserStatus.ACTIVE)
                )
                or 0
            )
            banks_active = (
                await session.scalar(
                    select(func.count()).select_from(BankORM).where(BankORM.is_active.is_(True))
                )
                or 0
            )

            recent = (
                await session.scalars(
                    select(ApplicationORM).order_by(ApplicationORM.updated_at.desc()).limit(8)
                )
            ).all()
            recent_logins = (
                await session.scalars(
                    select(UserORM)
                    .where(UserORM.last_login_at.is_not(None))
                    .order_by(UserORM.last_login_at.desc())
                    .limit(6)
                )
            ).all()

        total_apps = sum(counts.values())
        completed = counts[ApplicationStatus.COMPLETED.value]
        rejected = sum(counts[s.value] for s in REJECTED_STATUSES)
        in_progress = total_apps - completed - rejected - counts[ApplicationStatus.DRAFT.value]

        pipeline = [
            {
                "title": _(title),
                "count": sum(counts[s] for s in statuses),
                "statuses": [
                    (s, status_label(s), STATUS_LABELS[s][1], counts[s]) for s in statuses
                ],
            }
            for title, statuses in PIPELINE_GROUPS
        ]
        needs_attention = {
            "scoring_retry": scoring_retry,
            "to_council": counts["BANK_APPROVED"],
            "to_allocate": counts["DEMAND_DOCUMENT_CREATED"],
            "new_for_bank": counts["SENT_TO_BANK"],
        }

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/index.html",
            {
                "total_apps": total_apps,
                "new_today": new_today,
                "new_week": new_week,
                "in_progress": in_progress,
                "completed": completed,
                "rejected": rejected,
                "users_total": users_total,
                "users_active": users_active,
                "banks_active": banks_active,
                "pipeline": pipeline,
                "needs_attention": needs_attention,
                "recent": recent,
                "recent_logins": recent_logins,
            },
        )


def _application_progress(application: ApplicationORM) -> list[dict]:
    """Шаги индикатора прогресса (как в API) с переведёнными названиями."""
    steps = build_progress(application.status, application.scoring_retry_required)
    return [{"key": s.key, "title": _(s.title), "state": s.state} for s in steps]


def setup_admin(app: FastAPI) -> Admin:
    register_locales()

    admin = JamgarmaAdmin(
        app,
        engine,
        title="Jamg'arma · Admin",
        base_url="/admin",
        templates_dir=str(TEMPLATES_DIR),
        authentication_backend=AdminAuth(secret_key=settings.ADMIN_SESSION_SECRET),
        i18n_config=I18nConfig(
            default_locale=DEFAULT_ADMIN_LOCALE,
            language_switcher=ADMIN_LOCALES,
        ),
    )

    # Хелперы для наших шаблонов (дашборд, карточка заявки, верхняя панель).
    admin.templates.env.globals.update(
        {
            "admin_env": {"scoring_mode": settings.SCORING_MODE, "sso_mock": settings.SSO_MOCK},
            "app_version": settings.APP_VERSION,
            "status_badge": status_badge,
            "status_label": status_label,
            "subject_label": subject_label,
            "role_badge": role_badge,
            "event_label": event_label,
            "decision_badge": lambda v: labeled_badge(DECISION_LABELS, v),
            "scoring_badge": lambda v: labeled_badge(SCORING_RESULT_LABELS, v),
            "demand_badge": lambda v: labeled_badge(DEMAND_STATUS_LABELS, v),
            "fmt_dt": fmt_dt,
            "fmt_money": fmt_money,
            "fmt_size": fmt_size,
            "application_progress": _application_progress,
        }
    )

    for view in ALL_VIEWS:
        admin.add_view(view)

    return admin
