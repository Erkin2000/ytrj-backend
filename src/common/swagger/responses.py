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


def _error(description: str, message: str) -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "example": {"success": False, "message": message, "errors": None},
            }
        },
    }


SUCCESS = success_example({})
BAD_REQUEST = _error("Bad Request", "Bad request")
UNAUTHORIZED = _error("Unauthorized", "Not authenticated")
FORBIDDEN = _error("Forbidden", "You do not have permission to perform this action")
NOT_FOUND = _error("Not Found", "Not found")
CONFLICT = _error("Conflict", "Conflict")
INTERNAL_SERVER_ERROR = _error("Internal Server Error", "Internal server error")

VALIDATION_ERROR = {
    "description": "Validation Error",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Ошибка валидации.",
                "data": None,
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
