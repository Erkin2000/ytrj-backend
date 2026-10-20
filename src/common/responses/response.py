from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class ResponseBuilder:
    @staticmethod
    def success(
        data=None,
        message: str = "Success",
        status_code: int = 200,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "success": True,
                "message": message,
                "data": jsonable_encoder(data),
            },
        )

    @staticmethod
    def error(
        message: str,
        status_code: int,
        errors: list | None = None,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "message": message,
                "errors": errors,
            },
        )
