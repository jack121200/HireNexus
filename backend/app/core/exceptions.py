from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.logging import get_logger


logger = get_logger(__name__)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    return str(value)


def _normalize_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for err in errors:
        normalized.append({key: _json_safe(val) for key, val in err.items()})
    return normalized


class APIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        detail: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.data = data or {}
        super().__init__(detail)


def _error_payload(code: str, detail: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "detail": detail,
            "data": data or {},
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError) -> JSONResponse:
        logger.warning("api_error", code=exc.code, detail=exc.detail, data=exc.data)
        return JSONResponse(status_code=exc.status_code, content=_error_payload(exc.code, exc.detail, exc.data))

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        code = "http_error"
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        logger.info("http_exception", status_code=exc.status_code, detail=detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code, detail, {"status_code": exc.status_code}),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = _normalize_errors(exc.errors())
        logger.info("request_validation_error", errors=errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload("validation_error", "Invalid request", {"errors": errors}),
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError) -> JSONResponse:
        errors = _normalize_errors(exc.errors())
        logger.info("validation_error", errors=errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload("validation_error", "Invalid data", {"errors": errors}),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload("internal_error", "Something went wrong"),
        )
