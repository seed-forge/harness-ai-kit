from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# Known Dify provider type enum values
PROVIDER_TYPES: frozenset[str] = frozenset({
    "openai",
    "azure_openai",
    "openai-api-compatible",
    "anthropic",
    "google",
    "cohere",
    "huggingface_hub",
    "replicate",
    "xinference",
    "ollama",
    "localai",
    "tongyi",
    "wenxin",
    "moonshot",
    "minimax",
    "spark",
    "zhipuai",
    "baichuan",
})

_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


@dataclass(frozen=True)
class ProviderModel:
    model: str
    max_tokens: int | None = None


@dataclass(frozen=True)
class ProviderCredentials:
    api_base: str
    api_key: str


@dataclass(frozen=True)
class ProviderYamlPayload:
    provider: str
    name: str
    credentials: ProviderCredentials
    models: list[ProviderModel] = field(default_factory=list)
    options: dict[str, object] = field(default_factory=dict)
    dify_provider_id: str | None = None


def resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with os.environ['VAR_NAME'].

    Warns via stderr if a variable cannot be resolved. Returns the original
    placeholder as a fallback so the caller can decide how to handle it.
    """

    def _resolve(match: re.Match[str]) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name, "")
        if not env_value:
            import sys

            print(
                f"[warn] Environment variable '{var_name}' is not set — placeholder unresolved",
                file=sys.stderr,
            )
        return env_value

    return _ENV_VAR_RE.sub(_resolve, value)


def validate_provider_type(type_str: str) -> bool:
    """Check whether *type_str* is a known Dify provider type."""
    return type_str.strip().lower() in PROVIDER_TYPES


def load_provider_yaml(path: Path) -> ProviderYamlPayload:
    """Load and validate a provider YAML file.

    Resolves ${ENV_VAR} references in credentials fields.
    Raises ValueError for schema violations.
    """
    if not path.exists():
        raise ValueError(f"Provider YAML file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Provider YAML must contain a top-level mapping")

    provider_block = raw.get("provider")
    if not isinstance(provider_block, dict):
        raise ValueError("Provider YAML must contain a 'provider' key with a mapping")

    provider_type = str(provider_block.get("type", "")).strip()
    if not provider_type:
        raise ValueError("provider.type is required")
    if not validate_provider_type(provider_type):
        raise ValueError(
            f"Unknown provider type '{provider_type}'. Known types: {', '.join(sorted(PROVIDER_TYPES))}"
        )

    name = str(provider_block.get("name", "")).strip()
    if not name:
        raise ValueError("provider.name is required")

    creds_block = provider_block.get("credentials")
    if not isinstance(creds_block, dict):
        raise ValueError("provider.credentials must be a mapping with api_base and api_key")

    api_base = str(creds_block.get("api_base", "")).strip()
    if not api_base:
        raise ValueError("provider.credentials.api_base is required")

    api_key_raw = str(creds_block.get("api_key", "")).strip()
    if not api_key_raw:
        raise ValueError("provider.credentials.api_key is required")

    api_key = resolve_env_vars(api_key_raw)

    models: list[ProviderModel] = []
    raw_models = provider_block.get("models")
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, dict):
                model_name = str(item.get("model", "")).strip()
                if model_name:
                    max_tokens_val = item.get("max_tokens")
                    max_tokens = int(max_tokens_val) if max_tokens_val is not None else None
                    models.append(ProviderModel(model=model_name, max_tokens=max_tokens))
    if not models:
        raise ValueError("provider.models must be a non-empty list of model definitions")

    options: dict[str, object] = {}
    raw_options = provider_block.get("options")
    if isinstance(raw_options, dict):
        options = {str(k): v for k, v in raw_options.items()}

    dify_provider_id = None
    raw_id = provider_block.get("dify_provider_id")
    if raw_id is not None:
        dify_provider_id = str(raw_id).strip() or None

    return ProviderYamlPayload(
        provider=provider_type,
        name=name,
        credentials=ProviderCredentials(api_base=api_base, api_key=api_key),
        models=models,
        options=options,
        dify_provider_id=dify_provider_id,
    )


def load_manifest_yaml(path: Path) -> list[ProviderYamlPayload]:
    """Load a batch manifest YAML containing multiple provider definitions.

    The manifest MUST have a top-level 'providers' key containing a list
    of provider blocks following the same schema as individual provider YAML.
    """
    if not path.exists():
        raise ValueError(f"Manifest YAML file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Manifest YAML must contain a top-level mapping")

    providers_list = raw.get("providers")
    if not isinstance(providers_list, list):
        raise ValueError("Manifest YAML must contain a 'providers' list")

    result: list[ProviderYamlPayload] = []
    for entry in providers_list:
        if not isinstance(entry, dict):
            continue
        # Reuse load_provider_yaml logic by wrapping in a temporary structure
        wrapped = {"provider": entry}
        # We need to parse directly since load_provider_yaml expects a file
        provider_type = str(entry.get("type", "")).strip()
        if not provider_type:
            raise ValueError("Each manifest entry must have a 'type' field")
        if not validate_provider_type(provider_type):
            raise ValueError(f"Unknown provider type '{provider_type}'")

        name = str(entry.get("name", "")).strip()
        if not name:
            raise ValueError("Each manifest entry must have a 'name' field")

        creds_block = entry.get("credentials")
        if not isinstance(creds_block, dict):
            raise ValueError("Each manifest entry must have 'credentials' with api_base and api_key")

        api_base = str(creds_block.get("api_base", "")).strip()
        api_key_raw = str(creds_block.get("api_key", "")).strip()
        api_key = resolve_env_vars(api_key_raw)

        models: list[ProviderModel] = []
        raw_models = entry.get("models", [])
        if isinstance(raw_models, list):
            for item in raw_models:
                if isinstance(item, dict):
                    model_name = str(item.get("model", "")).strip()
                    if model_name:
                        max_tokens_val = item.get("max_tokens")
                        max_tokens = int(max_tokens_val) if max_tokens_val is not None else None
                        models.append(ProviderModel(model=model_name, max_tokens=max_tokens))

        options: dict[str, object] = {}
        raw_options = entry.get("options")
        if isinstance(raw_options, dict):
            options = {str(k): v for k, v in raw_options.items()}

        result.append(
            ProviderYamlPayload(
                provider=provider_type,
                name=name,
                credentials=ProviderCredentials(api_base=api_base, api_key=api_key),
                models=models,
                options=options,
            )
        )

    return result


def build_add_payload(p: ProviderYamlPayload) -> dict[str, object]:
    """Build the JSON payload for Dify's POST /model-providers from a ProviderYamlPayload."""
    models_payload: list[dict[str, object]] = []
    for m in p.models:
        entry: dict[str, object] = {"model": m.model}
        if m.max_tokens is not None:
            entry["max_tokens"] = m.max_tokens
        models_payload.append(entry)

    return {
        "provider": p.provider,
        "name": p.name,
        "credentials": {
            "api_base": p.credentials.api_base,
            "api_key": p.credentials.api_key,
        },
        "models": models_payload,
        "options": p.options,
    }


def write_back_provider_id(yaml_path: Path, provider_id: str) -> None:
    """Write the Dify-assigned provider ID back to the YAML file."""
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "provider" in raw and isinstance(raw["provider"], dict):
        raw["provider"]["dify_provider_id"] = provider_id
        yaml_path.write_text(yaml.dump(raw, allow_unicode=True, default_flow_style=False), encoding="utf-8")
