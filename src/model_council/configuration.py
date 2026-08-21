from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RoleConfig(BaseModel):
    model_alias: str
    prompt_version: str
    context_budget: int = Field(gt=0)


class ModelAliasConfig(BaseModel):
    provider: str
    model: str
    required_capabilities: dict[str, bool] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    network_enabled: bool = False
    allowed_data_classes: list[str] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    roles: dict[str, RoleConfig]
    models: dict[str, ModelAliasConfig]
    providers: dict[str, ProviderConfig]

    def resolve_role(self, role: str) -> RoleConfig:
        return self.roles[role]

    def resolve_model(self, alias: str) -> ModelAliasConfig:
        return self.models[alias]

    def resolve_provider(self, provider: str) -> ProviderConfig:
        return self.providers[provider]


def _load_yaml(path: Path, root_key: str) -> dict[str, object]:
    payload: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get(root_key), dict):
        raise ValueError(f"{path} must contain a {root_key} mapping")
    section = payload[root_key]
    return {str(key): value for key, value in section.items()}


def load_runtime_config(config_dir: Path) -> RuntimeConfig:
    return RuntimeConfig.model_validate(
        {
            "roles": _load_yaml(config_dir / "roles.yaml", "roles"),
            "models": _load_yaml(config_dir / "models.yaml", "models"),
            "providers": _load_yaml(config_dir / "providers.yaml", "providers"),
        }
    )
