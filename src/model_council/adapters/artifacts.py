from __future__ import annotations

import json
from pathlib import Path

import orjson

from model_council.models import (
    CallLogEvent,
    GatewayRequest,
    ReviewInput,
    RunState,
    StoredCall,
)


class LocalArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _call_dir(self, project_id: str, run_id: str, role: str) -> Path:
        path = self.root / "runs" / project_id / run_id / "calls" / role
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_call_input(self, request: GatewayRequest) -> None:
        call_dir = self._call_dir(request.project_id, request.run_id, request.role)
        (call_dir / "prompt.txt").write_text(request.prompt, encoding="utf-8")
        (call_dir / "context.json").write_text(
            json.dumps(request.context, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if request.envelope is not None:
            envelope_payload = request.envelope.model_dump(mode="json")
            envelope_payload["section_hashes"] = request.envelope.section_hashes
            envelope_payload["envelope_hash"] = request.envelope.envelope_hash
            (call_dir / "prompt-envelope.json").write_text(
                json.dumps(envelope_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    def write_raw_output(
        self,
        project_id: str,
        run_id: str,
        role: str,
        attempt: int,
        raw_output: str,
    ) -> None:
        path = self._call_dir(project_id, run_id, role)
        (path / f"raw-response-{attempt}.json").write_text(
            raw_output + "\n", encoding="utf-8"
        )

    def write_call_log(self, event: CallLogEvent) -> None:
        log_path = self.root / "logs" / "council.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("ab") as stream:
            stream.write(orjson.dumps(event.model_dump(mode="json")))
            stream.write(b"\n")

    def write_report(
        self, request: ReviewInput, state: RunState, calls: list[StoredCall]
    ) -> Path:
        report = (
            self.root
            / "runs"
            / request.project_id
            / request.run_id
            / "COUNCIL_REPORT.md"
        )
        report.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Council Report — {request.run_id}",
            "",
            f"State: `{state.value}`",
            "",
        ]
        for call in calls:
            lines.extend([f"## {call.role}", "", f"Status: `{call.status.value}`"])
            if call.output is not None:
                lines.extend(["", call.output.summary])
            lines.append("")
        report.write_text("\n".join(lines), encoding="utf-8")
        return report
