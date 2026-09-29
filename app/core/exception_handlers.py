import logging
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import BaseAppException
from app.core.responses import ApiResponse

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """Handles custom domain application exceptions."""
    logger.warning(f"Application Exception [{exc.error_code}] on {request.url.path}: {exc.message}")
    response = ApiResponse.fail(
        code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic payload validation errors."""
    logger.warning(f"Validation Error on {request.url.path}: {exc.errors()}")
    errors_dict = {"errors": exc.errors()}
    response = ApiResponse.fail(
        code="VALIDATION_ERROR",
        message="Request payload validation failed",
        details=errors_dict,
    )
    return JSONResponse(status_code=422, content=response.model_dump())


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles Starlette HTTP exceptions (e.g. 404 router misses, 405 Method Not Allowed)."""
    response = ApiResponse.fail(
        code="HTTP_ERROR",
        message=str(exc.detail),
        details={"status_code": exc.status_code},
    )
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled internal server exceptions."""
    logger.error(f"Unhandled Server Error on {request.url.path}: {str(exc)}", exc_info=True)
    response = ApiResponse.fail(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred",
        details=None,
    )
    return JSONResponse(status_code=500, content=response.model_dump())
