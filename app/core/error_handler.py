from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logger import logger


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
        request_id=request_id,
    )

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "detail": exc.errors(),
                "body": exc.body,
            }
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):

    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "unhandled_exception",
        path=request.url.path,
        exc_info=True,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "request_id": request_id,
        },
    )
