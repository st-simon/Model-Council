from __future__ import annotations

import re
from typing import Any

import httpx

from model_council.models import CallErrorKind

SAFE_PROVIDER_ERROR_CODES = frozenset(
    {
        "AccessDenied",
        "AccessDenied.Unpurchased",
        "Arrearage",
        "InternalError",
        "InvalidApiKey",
        "InvalidParameter",
        "ModelNotFound",
        "ModelServingError",
        "NOT AUTHORIZED",
        "Throttling",
        "invalid_api_key",
        "model_not_found",
    }
)
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")


def classify_http_error(status: int) -> CallErrorKind:
    if status in {401, 403}:
        return CallErrorKind.AUTHENTICATION
    if status == 429:
        return CallErrorKind.THROTTLED
    if status in {408, 409, 425} or status >= 500:
        return CallErrorKind.TRANSIENT
    if 400 <= status < 500:
        return CallErrorKind.INVALID_REQUEST
    return CallErrorKind.PERMANENT


def sanitized_error_evidence(
    response: httpx.Response,
) -> tuple[str | None, str | None]:
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    provider_error_code = body.get("code") if isinstance(body, dict) else None
    if provider_error_code not in SAFE_PROVIDER_ERROR_CODES:
        provider_error_code = None
    request_id = response.headers.get("x-request-id")
    if request_id is None and isinstance(body, dict):
        request_id = body.get("request_id") or body.get("requestId")
    if not isinstance(request_id, str) or not _safe_request_id(request_id):
        request_id = None
    return provider_error_code, request_id


def _safe_request_id(value: str) -> bool:
    return SAFE_REQUEST_ID.fullmatch(value) is not None
