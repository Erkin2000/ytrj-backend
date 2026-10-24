"""Примеры ответов для документации (Scalar / OpenAPI)."""


def success_example(data, message: str = "Success", description: str = "Success") -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "example": {"success": True, "message": message, "data": data},
            }
        },
    }


def paginated_example(item: dict, message: str = "Data retrieved successfully.") -> dict:
    return success_example(
        {
            "items": [item],
            "pagination": {"page": 1, "per_page": 10, "total": 57, "pages": 6},
        },
        message=message,
    )


def _error(description: str, message: str, code: str = "bad_request") -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "example": {"success": False, "message": message, "code": code, "errors": None},
            }
        },
    }


_STATUS_TEXT = {400: "Bad Request", 403: "Forbidden", 404: "Not Found", 409: "Conflict"}


def error_examples(*exceptions, description: str | None = None) -> dict:
    """Ответ с ошибкой для конкретной ручки: по одному примеру на каждое
    возможное исключение (``code`` + ``message`` + ``errors``). Статус берётся
    из первого исключения; все переданные должны иметь один status_code."""
    status = exceptions[0].status_code
    assert all(e.status_code == status for e in exceptions), "mixed status codes"

    examples = {}
    for exc_cls in exceptions:
        example_missing = getattr(exc_cls, "example_missing", None)
        # Исключения со списком незаполненных полей — показываем реалистичный список.
        instance = exc_cls(missing=example_missing) if example_missing else exc_cls()
        examples[exc_cls.code] = {
            "summary": exc_cls.code,
            "value": {
                "success": False,
                "message": instance.message,
                "code": exc_cls.code,
                "errors": instance.to_errors(),
            },
        }

    return {
        "description": description
        or f"{_STATUS_TEXT.get(status, 'Error')} — codes: {', '.join(examples)}",
        "content": {"application/json": {"examples": examples}},
    }


SUCCESS = success_example({})
BAD_REQUEST = _error("Bad Request", "Bad request")
UNAUTHORIZED = _error("Unauthorized", "Not authenticated", "not_authenticated")
FORBIDDEN = _error(
    "Forbidden", "You do not have permission to perform this action", "permission_denied"
)
NOT_FOUND = _error("Not Found", "Not found", "not_found")
CONFLICT = _error("Conflict", "Conflict", "conflict")
INTERNAL_SERVER_ERROR = _error("Internal Server Error", "Internal server error", "internal_error")

VALIDATION_ERROR = {
    "description": "Validation Error",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Ошибка валидации.",
                "code": "validation_error",
                "errors": [{"field": "username", "message": "Обязательное поле."}],
            }
        }
    },
}

COMMON_ERRORS = {
    400: BAD_REQUEST,
    401: UNAUTHORIZED,
    403: FORBIDDEN,
    404: NOT_FOUND,
    422: VALIDATION_ERROR,
    500: INTERNAL_SERVER_ERROR,
}

# Для GET-ручек: 400 они не возвращают.
READ_ERRORS = {status: body for status, body in COMMON_ERRORS.items() if status != 400}
