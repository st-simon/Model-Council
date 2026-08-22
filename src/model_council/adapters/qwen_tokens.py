from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from model_council.adapters.qwen import QwenModelGateway
from model_council.adapters.qwen_errors import (
    classify_http_error,
    sanitized_error_evidence,
)
from model_council.models import CallErrorKind, ModelCallError

TOKEN_TTL_SECONDS = 900
TOKEN_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/tokens?expire_in_seconds=900"


class _TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    token: str = Field(pattern=r"^st-[A-Za-z0-9._-]+$", min_length=4, max_length=512)
    expires_at: int = Field(gt=0)


@dataclass(frozen=True, slots=True)
class MintedTemporaryKey:
    token: str = field(repr=False)
    expires_at: datetime
    fingerprint: str

    def evidence(self) -> dict[str, str]:
        return {
            "expires_at": self.expires_at.isoformat(),
            "fingerprint_sha256": self.fingerprint,
        }


class QwenTemporaryKeyIssuer:
    """Mint one bounded Qwen credential without retaining the parent key."""

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def mint(
        self, parent_api_key: str, *, now: datetime | None = None
    ) -> MintedTemporaryKey:
        if not parent_api_key:
            raise ValueError("parent API key is required")
        issued_at = now or datetime.now(UTC)
        headers = {"Authorization": f"Bearer {parent_api_key}"}
        try:
            if self._client is not None:
                response = await self._client.post(TOKEN_ENDPOINT, headers=headers)
            else:
                timeout = httpx.Timeout(15.0, connect=5.0, write=5.0, pool=5.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(TOKEN_ENDPOINT, headers=headers)
        except httpx.TimeoutException:
            raise ModelCallError(
                "TEMPORARY_KEY_TIMEOUT", CallErrorKind.TIMEOUT
            ) from None
        except httpx.RequestError:
            raise ModelCallError(
                "TEMPORARY_KEY_TRANSPORT_ERROR", CallErrorKind.TRANSIENT
            ) from None
        if not response.is_success:
            provider_code, request_id = sanitized_error_evidence(response)
            raise ModelCallError(
                f"TEMPORARY_KEY_HTTP_{response.status_code}",
                classify_http_error(response.status_code),
                provider_error_code=provider_code,
                provider_request_id=request_id,
            )
        try:
            body = _TokenResponse.model_validate(response.json())
            expires_at = datetime.fromtimestamp(body.expires_at, tz=UTC)
            lifetime = (expires_at - issued_at).total_seconds()
            if not 0 < lifetime <= TOKEN_TTL_SECONDS:
                raise ValueError
        except (OSError, TypeError, ValueError, ValidationError):
            raise ModelCallError(
                "TEMPORARY_KEY_INVALID_RESPONSE", CallErrorKind.INVALID_RESPONSE
            ) from None
        return MintedTemporaryKey(
            token=body.token,
            expires_at=expires_at,
            fingerprint=hashlib.sha256(body.token.encode()).hexdigest(),
        )

    async def mint_gateway(
        self,
        parent_api_key: str,
        *,
        alias_to_model: dict[str, str],
        base_url: str,
        region: str,
        now: datetime | None = None,
    ) -> tuple[QwenModelGateway, MintedTemporaryKey]:
        minted = await self.mint(parent_api_key, now=now)
        gateway = QwenModelGateway(
            alias_to_model=alias_to_model,
            base_url=base_url,
            api_key=minted.token,
            region=region,
        )
        return gateway, minted
