from fastapi import APIRouter, Request

from src.account.schemas.user_schema import UserProfileUpdateDTO
from src.auth.schemas.auth_schema import (
    ChangePasswordDTO,
    LoginDTO,
    RefreshTokenRequestDTO,
    SSOCallbackDTO,
    SSOMockLoginDTO,
)
from src.auth.services.auth_service import AuthService
from src.common.dependencies import CurrentUserDep, DBDep
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, success_example
from src.config import settings

router = APIRouter(prefix="/auth", tags=["Авторизация и аутентификация"])

TOKENS_EXAMPLE = success_example(
    {
        "access_token": "eyJhbGciOi...",
        "refresh_token": "eyJhbGciOi...",
        "token_type": "bearer",
        "expires_in": 3600,
    },
    message="Logged in successfully.",
)


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    return request.headers.get("user-agent"), request.client.host if request.client else None


@router.post(
    "/login",
    summary="Вход по логину и паролю — только внутренние роли (Super Admin, Фонд, банк, Совет)",
    responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
)
async def login(data: LoginDTO, db: DBDep, request: Request):
    tokens = await AuthService(db).login(data, *_client_meta(request))
    return ResponseBuilder.success(data=tokens, message="Logged in successfully.")


@router.post(
    "/refresh",
    summary="Обновление пары токенов (ротация refresh-токена)",
    responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
)
async def refresh(data: RefreshTokenRequestDTO, db: DBDep, request: Request):
    tokens = await AuthService(db).refresh_tokens(data.refresh_token, *_client_meta(request))
    return ResponseBuilder.success(data=tokens, message="Tokens refreshed.")


@router.post(
    "/logout",
    summary="Выход (отзыв refresh-токена)",
    responses={200: success_example(None, "Logged out."), **COMMON_ERRORS},
)
async def logout(data: RefreshTokenRequestDTO, db: DBDep):
    await AuthService(db).logout(data.refresh_token)
    return ResponseBuilder.success(message="Logged out.")


@router.post(
    "/logout-all",
    summary="Завершить все сессии текущего пользователя",
    responses={200: success_example(None, "All sessions closed."), **COMMON_ERRORS},
)
async def logout_all(db: DBDep, user: CurrentUserDep):
    await AuthService(db).logout_everywhere(user.id)
    return ResponseBuilder.success(message="All sessions closed.")


PROFILE_EXAMPLE = {
    "id": 7,
    "username": "30101900000011",
    "full_name": "Алиев Али Алиевич",
    "pinfl": "30101900000011",
    "phone": "+998901234567",
    "passport_number": "AA1234567",
    "inn": "123456789",
    "email": "aliev@example.com",
    "gender": "MALE",
    "date_of_birth": "1998-05-20",
    "status": "ACTIVE",
    "role": {"id": 5, "code": "APPLICANT", "name": "Заявитель", "is_superuser": False},
    "bank": None,
    "is_superuser": False,
    "permissions": ["applications.create", "applications.read"],
    "profile_complete": True,
    "missing_fields": [],
}


@router.get(
    "/me",
    summary="Текущий пользователь: профиль, роль, права, scope",
    description=(
        "`profile_complete` / `missing_fields` показывают, какие данные заявителю нужно "
        "дополнить через `PATCH /auth/me`, прежде чем создавать заявку."
    ),
    responses={
        200: success_example(PROFILE_EXAMPLE, message="Profile retrieved."),
        **COMMON_ERRORS,
    },
)
async def me(db: DBDep, user: CurrentUserDep):
    profile = await AuthService(db).get_profile(user)
    return ResponseBuilder.success(data=profile, message="Profile retrieved.")


@router.patch(
    "/me",
    summary="Дополнить свой профиль: телефон, паспорт, ИНН, email, пол, дата рождения",
    description=(
        "YIA Portal передаёт только Ф.И.О. и ПИНФЛ — эти поля обновляются при входе "
        "и здесь не принимаются (ответ 422). Передавать можно любое подмножество полей; "
        "`null` очищает поле. Пока профиль не заполнен полностью, создать заявку нельзя."
    ),
    responses={
        200: success_example(PROFILE_EXAMPLE, message="Profile updated."),
        **COMMON_ERRORS,
    },
)
async def update_me(data: UserProfileUpdateDTO, db: DBDep, user: CurrentUserDep):
    profile = await AuthService(db).update_profile(user, data)
    return ResponseBuilder.success(data=profile, message="Profile updated.")


@router.post(
    "/change-password",
    summary="Смена собственного пароля (закрывает прежние сессии)",
    responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
)
async def change_password(data: ChangePasswordDTO, db: DBDep, user: CurrentUserDep):
    tokens = await AuthService(db).change_password(user.id, data)
    return ResponseBuilder.success(data=tokens, message="Password changed.")


# ---------- YIA Portal SSO ----------


@router.get(
    "/sso/authorize",
    summary="YIA SSO: ссылка на страницу входа портала и подписанный state",
    description=(
        "Фронтенд сохраняет `state` (sessionStorage) и перенаправляет браузер на "
        "`authorize_url`. Портал вернёт пользователя на `SSO_REDIRECT_URI` с `code` и `state`."
    ),
    responses={
        200: success_example(
            {
                "authorize_url": (
                    "https://api.e-yoshlar.uz/api/v1/users/auth/sso/authorize/"
                    "?client_id=...&redirect_uri=...&state=..."
                ),
                "state": "ImFiYyI.aBcD...",
            },
            message="Authorize URL generated.",
        ),
        **COMMON_ERRORS,
    },
)
async def sso_authorize(db: DBDep):
    data = AuthService(db).sso_authorize()
    return ResponseBuilder.success(data=data, message="Authorize URL generated.")


@router.post(
    "/sso/callback",
    summary="YIA SSO (только заявители): обмен code на токены, профиль определяется или создаётся",
    description=(
        "Фронтенд передаёт сюда `code`, `state` и `error` из query-параметров redirect_uri. "
        "`code` одноразовый и живёт 60 секунд — вызывать сразу после редиректа."
    ),
    responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
)
async def sso_callback(data: SSOCallbackDTO, db: DBDep, request: Request):
    tokens = await AuthService(db).sso_callback(data, *_client_meta(request))
    return ResponseBuilder.success(data=tokens, message="Logged in via YIA Portal.")


if settings.SSO_MOCK:

    @router.post(
        "/sso/mock-login",
        summary="YIA SSO (тест, только заявители): вход с ручными данными — при SSO_MOCK=True",
        responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
    )
    async def sso_mock_login(data: SSOMockLoginDTO, db: DBDep, request: Request):
        tokens = await AuthService(db).sso_mock_login(data, *_client_meta(request))
        return ResponseBuilder.success(data=tokens, message="Logged in via mock YIA SSO.")
