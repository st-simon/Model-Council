from __future__ import annotations

import re
from collections.abc import Callable

from model_council.configuration import ProviderConfig
from model_council.models import PromptEnvelope


class EgressDenied(RuntimeError):
    pass


class EgressGuard:
    _secret_patterns = (
        re.compile(r"(?i)api[_-]?key\s*[:=]"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"(?i)(password|token|secret)\s*[:=]\s*['\"][^'\"]+"),
    )
    _pii_patterns = (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),)
    _injection_patterns = (
        re.compile(r"(?i)ignore (all |the )?previous instructions"),
        re.compile(r"(?i)system prompt"),
    )

    def __init__(
        self, scanners: tuple[Callable[[str], str | None], ...] | None = None
    ) -> None:
        self.scanners = scanners or (
            self._scan_secrets,
            self._scan_pii,
            self._scan_injection,
        )

    def authorize(
        self,
        envelope: PromptEnvelope,
        provider: str,
        policy: ProviderConfig,
    ) -> PromptEnvelope:
        if not policy.network_enabled:
            raise EgressDenied("NETWORK_DISABLED")
        if envelope.policy_metadata.data_class not in policy.allowed_data_classes:
            raise EgressDenied("DATA_CLASS_DENIED")
        if not provider:
            raise EgressDenied("PROVIDER_UNRESOLVED")

        content = "\n".join(
            [
                envelope.static_prefix,
                *envelope.project_context.values(),
                envelope.dynamic_payload,
            ]
        )
        for scanner in self.scanners:
            try:
                reason = scanner(content)
            except Exception as error:
                raise EgressDenied("SCANNER_ERROR") from error
            if reason is not None:
                raise EgressDenied(reason)
        return envelope

    @classmethod
    def _scan_secrets(cls, content: str) -> str | None:
        return cls._match(content, cls._secret_patterns, "SECRET_DETECTED")

    @classmethod
    def _scan_pii(cls, content: str) -> str | None:
        return cls._match(content, cls._pii_patterns, "PII_DETECTED")

    @classmethod
    def _scan_injection(cls, content: str) -> str | None:
        return cls._match(content, cls._injection_patterns, "PROMPT_INJECTION_DETECTED")

    @staticmethod
    def _match(
        content: str, patterns: tuple[re.Pattern[str], ...], reason: str
    ) -> str | None:
        return reason if any(pattern.search(content) for pattern in patterns) else None
