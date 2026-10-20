from fastapi import APIRouter, Request

from src.auth.schemas.auth_schema import (
    ChangePasswordDTO,
    LoginDTO,
    OneIDCallbackDTO,
    OneIDMockLoginDTO,
    RefreshTokenRequestDTO,
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


@router.get(
    "/me",
    summary="Текущий пользователь: профиль, роль, права, scope",
    responses={
        200: success_example(
            {
                "id": 1,
                "username": "admin",
                "full_name": "Администратор",
                "status": "ACTIVE",
                "role": {
                    "id": 1,
                    "code": "SUPER_ADMIN",
                    "name": "Super Admin",
                    "is_superuser": True,
                },
                "bank": None,
                "is_superuser": True,
                "permissions": ["users.read", "users.update"],
            },
            message="Profile retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def me(db: DBDep, user: CurrentUserDep):
    profile = await AuthService(db).get_profile(user)
    return ResponseBuilder.success(data=profile, message="Profile retrieved.")


@router.post(
    "/change-password",
    summary="Смена собственного пароля (закрывает прежние сессии)",
    responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
)
async def change_password(data: ChangePasswordDTO, db: DBDep, user: CurrentUserDep):
    tokens = await AuthService(db).change_password(user.id, data)
    return ResponseBuilder.success(data=tokens, message="Password changed.")


# ---------- OneID ----------


@router.get(
    "/oneid/authorize",
    summary="OneID: ссылка для перехода на страницу входа",
    responses={
        200: success_example(
            {"authorize_url": "https://sso.egov.uz/sso/oauth/Authorization.do?...", "state": "abc"},
            message="Authorize URL generated.",
        ),
        **COMMON_ERRORS,
    },
)
async def oneid_authorize(db: DBDep):
    data = AuthService(db).oneid_authorize()
    return ResponseBuilder.success(data=data, message="Authorize URL generated.")


@router.post(
    "/oneid/callback",
    summary="OneID (только заявители): обмен code на токены, профиль определяется или создаётся",
    responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
)
async def oneid_callback(data: OneIDCallbackDTO, db: DBDep, request: Request):
    tokens = await AuthService(db).oneid_callback(data.code, *_client_meta(request))
    return ResponseBuilder.success(data=tokens, message="Logged in via OneID.")


if settings.ONEID_MOCK:

    @router.post(
        "/oneid/mock-login",
        summary="OneID (тест, только заявители): вход с ручными данными профиля — при ONEID_MOCK=True",
        responses={200: TOKENS_EXAMPLE, **COMMON_ERRORS},
    )
    async def oneid_mock_login(data: OneIDMockLoginDTO, db: DBDep, request: Request):
        tokens = await AuthService(db).oneid_mock_login(data, *_client_meta(request))
        return ResponseBuilder.success(data=tokens, message="Logged in via mock OneID.")
