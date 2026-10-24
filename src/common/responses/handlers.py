import logging
import traceback

from fastapi import FastAPI, Request

from src.common.responses.exceptions import ApiException
from src.common.responses.response import ResponseBuilder
from src.config import settings

logger = logging.getLogger(__name__)


def _add_cors_headers(request: Request, response):
    """Ответ на 500 формируется во внешнем ServerErrorMiddleware выше
    CORSMiddleware, поэтому CORS-заголовки проставляем сами."""
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Vary"] = "Origin"
    return response


async def api_exception_handler(request: Request, exc: ApiException):
    # errors: незаполненные поля (заявка, профиль) либо поле, к которому
    # относится ошибка (bank_id, company, founders, file) — для подсветки на фронтенде.
    return ResponseBuilder.error(
        message=exc.message,
        status_code=exc.status_code,
        errors=exc.to_errors(),
        code=exc.code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    # Трейс всегда пишем в лог сервера — наружу он не уходит.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)

    if settings.DEBUG_ERRORS:
        response = ResponseBuilder.error(
            message=f"{type(exc).__name__}: {exc}",
            status_code=500,
            errors=traceback.format_exception(type(exc), exc, exc.__traceback__),
            code="internal_error",
        )
    else:
        response = ResponseBuilder.error(
            message="Internal server error",
            status_code=500,
            code="internal_error",
        )

    return _add_cors_headers(request, response)


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(ApiException, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
