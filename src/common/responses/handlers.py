import logging
import traceback

from fastapi import FastAPI, Request

from src.common.responses.exceptions import ApiException, ApplicationValidationException
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
    errors = None

    if isinstance(exc, ApplicationValidationException) and exc.missing:
        errors = [{"field": field, "message": "Required"} for field in exc.missing]

    return ResponseBuilder.error(
        message=exc.message,
        status_code=exc.status_code,
        errors=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    # Трейс всегда пишем в лог сервера — наружу он не уходит.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)

    if settings.DEBUG_ERRORS:
        response = ResponseBuilder.error(
            message=f"{type(exc).__name__}: {exc}",
            status_code=500,
            errors=traceback.format_exception(type(exc), exc, exc.__traceback__),
        )
    else:
        response = ResponseBuilder.error(
            message="Internal server error",
            status_code=500,
        )

    return _add_cors_headers(request, response)


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(ApiException, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
