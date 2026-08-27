from __future__ import annotations

from typing import Any, Literal

from packaging.specifiers import SpecifierSet
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer, model_validator

from harness_ai_kit.domain.versions import PINNED_VERSION_PATTERN, is_compatible_specifier, is_latest_specifier, is_pinned_specifier


class _PrivateFieldsAllowed(BaseModel):
    """Base model that permits `_`-prefixed private fields in JSON input.

    JSON keys starting with `_` (e.g. `_comment_extends`, `_note`,
    `_comment_recommended_tools`) are conventionally used as inline
    documentation. They are stripped from the validation input and stashed
    in the declared `private` field, then automatically restored to model_dump() output.
    """

    private: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _extract_private_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        private = {k: v for k, v in data.items() if isinstance(k, str) and k.startswith("_")}
        if private:
            data = {k: v for k, v in data.items() if not (isinstance(k, str) and k.startswith("_"))}
            data["private"] = private
        return data

    @model_serializer(mode="wrap")
    def serialize_model(self, serializer, info):
        # Serialize normally first
        result = serializer(self)
        # The internal `private` field is a storage bucket, not a real output
        # key. Never emit it literally: downstream models (e.g. lockfile
        # companion_docs: dict[str, str | bool]) reject a nested dict value and
        # fail with `private.str/private.bool` union errors. Only merge back the
        # `_`-prefixed private keys so they round-trip as top-level keys.
        if isinstance(result, dict):
            result.pop("private", None)
            if self.private:
                result.update(self.private)
        return result

    @model_validator(mode="after")
    def _restore_private_to_extra(self) -> "_PrivateFieldsAllowed":
        # Expose private fields on the instance via __pydantic_extra__ so that
        # model_dump(exclude_defaults=False) / model_dump_json() round-trips them.
        if self.private:
            try:
                object.__setattr__(self, "__pydantic_extra__", dict(self.private))
            except (AttributeError, TypeError):
                # Fallback: keep them in `private` only; model_dump(exclude_defaults=False)
                # will still include them via the declared field.
                pass
        return self


class DependencySpec(_PrivateFieldsAllowed):
    model_config = ConfigDict(extra="forbid")

    type: Literal["skill", "plugin", "hook", "subagent", "cli", "mcp"]
    namespace: str | None = None
    id: str
    version: str
    scope: Literal["required", "optional"] = "required"
    feature: str | None = None
    source_url: str | None = None
    source_ref: str | None = None
    subpath: str | None = None

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if "/" in value:
            raise ValueError("Dependency namespace must be a single segment.")
        return value

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Dependency id cannot be empty.")
        if "/" in value:
            raise ValueError("Dependency id must not contain '/'. Use the namespace field instead.")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if is_latest_specifier(value):
            return value.strip().lower()
        try:
            SpecifierSet(value)
        except Exception as exc:
            raise ValueError(f"Invalid dependency version specifier: {value}") from exc
        return value

    @model_validator(mode="after")
    def validate_optional_feature(self) -> "DependencySpec":
        # CLI distributions are global package names. Older skill manifests
        # incorrectly carried their enclosing skill namespace; normalize them
        # at the shared parsing boundary so registry locks remain resolvable.
        if self.type == "cli":
            self.namespace = None
        if self.scope == "optional" and not self.feature:
            raise ValueError("Optional dependencies must declare a feature name.")
        return self


class IntegrationSpec(_PrivateFieldsAllowed):
    """Declares an outbound/inbound interaction contract with an external asset.

    Complements DependencySpec: `dependencies` says "what I need co-installed",
    while `integrations` says "whom I interact with and how". The target is an
    external asset (another skill / CLI / MCP server / loop), never an internal
    reference or script path (those belong to the README.md Asset Router).
    """

    model_config = ConfigDict(extra="forbid")

    target: str
    type: Literal["skill", "cli", "mcp", "loop"]
    direction: Literal["inbound", "outbound"] = "outbound"
    contract: str = ""

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Integration target cannot be empty.")
        return value

    @field_validator("contract")
    @classmethod
    def validate_contract(cls, value: str) -> str:
        return value.strip()


class ExtendsSpec(_PrivateFieldsAllowed):
    """Declares a content-inheritance relationship for layered skill architecture.

    Distinct from DependencySpec: extends controls SKILL.md content merge rather
    than runtime co-installation.  The base skill is automatically installed
    by default (auto_install=True) but hidden from IDE listings (visible=False).
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["extends"] = "extends"
    namespace: str | None = None
    id: str
    version: str
    merge_strategy: Literal["prepend", "append", "replace"] = "prepend"
    merge_sections: list[str] | None = None
    auto_install: bool = True
    visible: bool = False

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if "/" in value:
            raise ValueError("Extends namespace must be a single segment.")
        return value

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Extends id cannot be empty.")
        if "/" in value:
            raise ValueError("Extends id must not contain '/'. Use the namespace field instead.")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        try:
            SpecifierSet(value)
        except Exception as exc:
            raise ValueError(f"Invalid extends version specifier: {value}") from exc
        if not is_compatible_specifier(value):
            raise ValueError(
                f"Extends versions must be ==x.y.z or >=x.y.z. Got {value}."
            )
        return value

    @model_validator(mode="after")
    def validate_merge_sections(self) -> "ExtendsSpec":
        if self.merge_strategy == "replace" and self.merge_sections:
            raise ValueError(
                "merge_sections is not valid when merge_strategy='replace'. "
                "The replace strategy applies to the entire content."
            )
        return self
