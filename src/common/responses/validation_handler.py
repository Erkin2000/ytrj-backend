from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PATTERN_MESSAGES = {
    "phone": "Номер телефона должен быть в формате +998901234567.",
    "pinfl": "ПИНФЛ должен состоять из 14 цифр.",
}

TYPE_MESSAGES = {
    "string_too_short": "Значение слишком короткое.",
    "string_too_long": "Превышена максимальная длина.",
    "greater_than": "Значение должно быть больше нуля.",
    "missing": "Обязательное поле.",
    "enum": "Недопустимое значение.",
}


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []

    for error in exc.errors():
        field = ".".join(str(i) for i in error["loc"] if i != "body")
        error_type = error["type"]
        message = error["msg"]

        if error_type == "string_pattern_mismatch":
            message = PATTERN_MESSAGES.get(field.split(".")[-1], "Неверный формат.")
        elif error_type in TYPE_MESSAGES:
            message = TYPE_MESSAGES[error_type]
        elif "valid date" in message.lower():
            message = "Некорректная дата. Используйте формат YYYY-MM-DD."
        else:
            message = message.replace("Value error, ", "")

        errors.append({"field": field, "message": message})

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Ошибка валидации.",
            "code": "validation_error",
            "errors": errors,
        },
    )
