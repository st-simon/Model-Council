from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from model_council.cli import (
    _gate_c_claim_authorization,
    _gate_c_evidence_home_preflight,
    _gate_c_proxy_preflight,
)
from model_council.gate_c import GateCStopped

PROXY_ENV = {
    "HTTP_PROXY": "http://127.0.0.1:7897",
    "HTTPS_PROXY": "http://127.0.0.1:7897",
    "http_proxy": "http://127.0.0.1:7897",
    "https_proxy": "http://127.0.0.1:7897",
    "ALL_PROXY": "socks5://127.0.0.1:7897",
    "all_proxy": "socks5://127.0.0.1:7897",
}


class _Socket:
    closed = False

    def close(self) -> None:
        self.closed = True


def test_proxy_preflight_requires_exact_clash_listener_and_shell_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in PROXY_ENV.items():
        monkeypatch.setenv(name, value)
    observed: dict[str, object] = {}
    connection = _Socket()

    def connect(address: tuple[str, int], timeout: float) -> _Socket:
        observed["address"] = address
        observed["timeout"] = timeout
        return connection

    monkeypatch.setattr("model_council.cli.socket.create_connection", connect)

    _gate_c_proxy_preflight()

    assert observed == {"address": ("127.0.0.1", 7897), "timeout": 1.0}
    assert connection.closed is True


def test_proxy_preflight_fails_closed_on_route_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in PROXY_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")

    with pytest.raises(GateCStopped, match="PROXY_ENVIRONMENT_CHANGED"):
        _gate_c_proxy_preflight()


def test_evidence_home_must_be_new(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()

    with pytest.raises(GateCStopped, match="EVIDENCE_HOME_ALREADY_EXISTS"):
        _gate_c_evidence_home_preflight(existing)

    _gate_c_evidence_home_preflight(tmp_path / "new")


def test_authorization_is_claimed_once_before_any_live_operation(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)

    marker = _gate_c_claim_authorization(tmp_path, now)

    assert marker.exists()
    contents = marker.read_text(encoding="utf-8")
    assert '"status": "TOKEN_MINT_STARTED"' in contents
    assert "API_KEY" not in contents
    with pytest.raises(GateCStopped, match="AUTHORIZATION_ALREADY_CONSUMED"):
        _gate_c_claim_authorization(tmp_path, now)
