from __future__ import annotations

import os
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from difyctl.console_api import (
    CONSOLE_ENDPOINTS,
    ConsoleApiClient,
    ConsoleAuth,
    should_fallback,
)
from difyctl.config import (
    AppConfig,
    ProfileConfig,
    merge_config,
    resolve_active_profile,
    resolve_console_key,
    resolve_providers_dir,
)
from difyctl.provider_config import (
    PROVIDER_TYPES,
    ProviderCredentials,
    ProviderModel,
    ProviderYamlPayload,
    build_add_payload,
    load_manifest_yaml,
    load_provider_yaml,
    resolve_env_vars,
    validate_provider_type,
    write_back_provider_id,
)

TEST_WORK_ROOT = Path(__file__).resolve().parent / ".tmp-runtime"
TEST_WORK_ROOT.mkdir(parents=True, exist_ok=True)


def _make_case_dir(prefix: str) -> Path:
    path = TEST_WORK_ROOT / f"{prefix}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


# ── ConsoleAuth tests ──


def test_console_auth_detect_bearer() -> None:
    auth = ConsoleAuth.detect("sk-test-123")
    assert auth.type == "bearer"
    assert auth.value == "sk-test-123"


def test_console_auth_detect_cookie() -> None:
    auth = ConsoleAuth.detect("session=abc123def")
    assert auth.type == "cookie"
    assert auth.value == "session=abc123def"


def test_console_auth_detect_cookie_case_insensitive() -> None:
    auth = ConsoleAuth.detect("SESSION=ABC")
    assert auth.type == "cookie"


def test_console_auth_detect_empty_raises() -> None:
    try:
        ConsoleAuth.detect("")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_console_auth_detect_whitespace_raises() -> None:
    try:
        ConsoleAuth.detect("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


# ── should_fallback tests ──


def test_should_fallback_true_for_5xx() -> None:
    assert should_fallback(500) is True
    assert should_fallback(502) is True
    assert should_fallback(503) is True


def test_should_fallback_true_for_429() -> None:
    assert should_fallback(429) is True


def test_should_fallback_false_for_auth_errors() -> None:
    assert should_fallback(401) is False
    assert should_fallback(403) is False


def test_should_fallback_false_for_not_found() -> None:
    assert should_fallback(404) is False


def test_should_fallback_false_for_conflict() -> None:
    assert should_fallback(409) is False


def test_should_fallback_false_for_validation() -> None:
    assert should_fallback(422) is False


# ── Config profile tests ──


def test_merge_config_passes_profile() -> None:
    saved = AppConfig(active_profile="old")
    merged = merge_config(saved, profile="组织内部集群")
    assert merged.active_profile == "组织内部集群"


def test_resolve_active_profile_none_when_unset() -> None:
    config = AppConfig()
    assert resolve_active_profile(config) is None


def test_resolve_active_profile_returns_profile() -> None:
    config = AppConfig(
        active_profile="组织内部集群",
        profiles={"组织内部集群": ProfileConfig(base_url="http://dify.test")},
    )
    profile = resolve_active_profile(config)
    assert profile is not None
    assert profile.base_url == "http://dify.test"


def test_resolve_console_key_from_env() -> None:
    old = os.environ.get("TEST_CONSOLE_KEY")
    try:
        os.environ["TEST_CONSOLE_KEY"] = "sk-secret"
        config = AppConfig(
            active_profile="test",
            profiles={"test": ProfileConfig(console_key="${TEST_CONSOLE_KEY}")},
        )
        key = resolve_console_key(config)
        assert key == "sk-secret"
    finally:
        if old is None:
            os.environ.pop("TEST_CONSOLE_KEY", None)
        else:
            os.environ["TEST_CONSOLE_KEY"] = old


def test_resolve_console_key_plain_value() -> None:
    config = AppConfig(
        active_profile="test",
        profiles={"test": ProfileConfig(console_key="sk-plain")},
    )
    assert resolve_console_key(config) == "sk-plain"


def test_resolve_providers_dir_defaults() -> None:
    config = AppConfig(
        active_profile="组织内部集群",
        profiles={"组织内部集群": ProfileConfig()},
    )
    providers_dir = resolve_providers_dir(config)
    assert providers_dir.name == "组织内部集群"
    assert ".difyctl" in str(providers_dir)


def test_resolve_providers_dir_custom() -> None:
    custom = Path("/custom/providers").expanduser().resolve()
    config = AppConfig(
        active_profile="test",
        profiles={"test": ProfileConfig(providers_dir=str(custom))},
    )
    providers_dir = resolve_providers_dir(config)
    assert str(providers_dir) == str(custom)


# ── Provider YAML tests ──


def test_load_provider_yaml_valid() -> None:
    tmp_path = _make_case_dir("provider-yaml")
    try:
        old = os.environ.get("TEST_KEY")
        os.environ["TEST_KEY"] = "sk-test-key"
        yaml_path = tmp_path / "provider.yaml"
        yaml_path.write_text(
            """provider:
  type: openai-api-compatible
  name: Test Provider
  credentials:
    api_base: https://api.test.com/v1
    api_key: ${TEST_KEY}
  models:
    - model: gpt-4o
      max_tokens: 128000
  options:
    load_balancing: true
""",
            encoding="utf-8",
        )
        payload = load_provider_yaml(yaml_path)
        assert payload.provider == "openai-api-compatible"
        assert payload.name == "Test Provider"
        assert payload.credentials.api_base == "https://api.test.com/v1"
        assert payload.credentials.api_key == "sk-test-key"
        assert len(payload.models) == 1
        assert payload.models[0].model == "gpt-4o"
        assert payload.models[0].max_tokens == 128000
    finally:
        if old is None:
            os.environ.pop("TEST_KEY", None)
        else:
            os.environ["TEST_KEY"] = old
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_load_provider_yaml_missing_type_raises() -> None:
    tmp_path = _make_case_dir("bad-yaml")
    try:
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text("provider:\n  name: NoType\n  credentials:\n    api_base: x\n    api_key: y\n  models:\n    - model: m\n", encoding="utf-8")
        try:
            load_provider_yaml(yaml_path)
        except ValueError as exc:
            assert "type" in str(exc).lower()
        else:
            raise AssertionError("expected ValueError")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_load_provider_yaml_unknown_type_raises() -> None:
    tmp_path = _make_case_dir("bad-type")
    try:
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text("provider:\n  type: bogus-ai\n  name: Bogus\n  credentials:\n    api_base: x\n    api_key: y\n  models:\n    - model: m\n", encoding="utf-8")
        try:
            load_provider_yaml(yaml_path)
        except ValueError as exc:
            assert "Unknown provider type" in str(exc)
        else:
            raise AssertionError("expected ValueError")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_load_provider_yaml_no_models_raises() -> None:
    tmp_path = _make_case_dir("no-models")
    try:
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text("provider:\n  type: openai\n  name: NoModels\n  credentials:\n    api_base: x\n    api_key: y\n", encoding="utf-8")
        try:
            load_provider_yaml(yaml_path)
        except ValueError as exc:
            assert "models" in str(exc).lower()
        else:
            raise AssertionError("expected ValueError")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_validate_provider_type() -> None:
    assert validate_provider_type("openai") is True
    assert validate_provider_type("openai-api-compatible") is True
    assert validate_provider_type("bogus") is False


def test_resolve_env_vars_replaces_all() -> None:
    old = os.environ.get("A"), os.environ.get("B")
    try:
        os.environ["A"] = "hello"
        os.environ["B"] = "world"
        result = resolve_env_vars("${A} ${B}")
        assert result == "hello world"
    finally:
        for key, val in zip(("A", "B"), old):
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


def test_build_add_payload() -> None:
    p = ProviderYamlPayload(
        provider="openai-api-compatible",
        name="Test",
        credentials=ProviderCredentials(api_base="https://api.test.com/v1", api_key="sk-test"),
        models=[ProviderModel(model="gpt-4o", max_tokens=128000)],
        options={"load_balancing": True},
    )
    payload = build_add_payload(p)
    assert payload["provider"] == "openai-api-compatible"
    assert payload["name"] == "Test"
    assert payload["credentials"]["api_base"] == "https://api.test.com/v1"
    assert payload["credentials"]["api_key"] == "sk-test"
    assert len(payload["models"]) == 1
    assert payload["models"][0]["model"] == "gpt-4o"
    assert payload["models"][0]["max_tokens"] == 128000


def test_write_back_provider_id() -> None:
    tmp_path = _make_case_dir("writeback")
    try:
        yaml_path = tmp_path / "provider.yaml"
        yaml_path.write_text("provider:\n  type: openai-api-compatible\n  name: Test\n  credentials:\n    api_base: x\n    api_key: y\n  models:\n    - model: m\n", encoding="utf-8")
        write_back_provider_id(yaml_path, "provider-abc-123")
        payload = load_provider_yaml(yaml_path)
        assert payload.dify_provider_id == "provider-abc-123"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


# ── Manifest YAML tests ──


def test_load_manifest_yaml() -> None:
    tmp_path = _make_case_dir("manifest")
    try:
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(
            """providers:
  - type: openai-api-compatible
    name: Provider A
    credentials:
      api_base: https://a.test.com/v1
      api_key: sk-a
    models:
      - model: gpt-4o
  - type: openai
    name: Provider B
    credentials:
      api_base: https://b.test.com/v1
      api_key: sk-b
    models:
      - model: gpt-4o-mini
""",
            encoding="utf-8",
        )
        providers = load_manifest_yaml(manifest_path)
        assert len(providers) == 2
        assert providers[0].name == "Provider A"
        assert providers[1].name == "Provider B"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


# ── ConsoleApiClient tests ──


def test_console_api_client_resolve_path() -> None:
    auth = ConsoleAuth.detect("sk-test")
    client = ConsoleApiClient("http://dify.test", auth)
    path = client.resolve_path("provider", provider="my-provider")
    assert "/my-provider" in path


def test_console_endpoints_defined() -> None:
    assert "providers" in CONSOLE_ENDPOINTS
    assert "model_credentials" in CONSOLE_ENDPOINTS
    assert "models_list" in CONSOLE_ENDPOINTS


def test_post_forwards_path_and_body() -> None:
    """Regression: ConsoleApiClient.post() must forward the path to _request.

    A prior bug called ``self._request("POST", body or {})`` (dropping the path
    argument), which broke provider_add_model / provider_validate_model.
    """
    auth = ConsoleAuth.detect("sk-test")
    client = ConsoleApiClient("http://dify.test", auth)
    captured: dict[str, object] = {}

    def fake_request(method, path, body=None):  # type: ignore[no-untyped-def]
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return None

    client._request = fake_request  # type: ignore[assignment]
    client.post("/console/api/some/path", {"k": "v"})
    assert captured["method"] == "POST"
    assert captured["path"] == "/console/api/some/path"
    assert captured["body"] == {"k": "v"}


def test_provider_add_model_hits_credentials_endpoint() -> None:
    """provider_add_model should POST to the model_credentials endpoint with a full payload."""
    auth = ConsoleAuth.detect("sk-test")
    client = ConsoleApiClient("http://dify.test", auth)
    captured: dict[str, object] = {}

    def fake_request(method, path, body=None):  # type: ignore[no-untyped-def]
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return None

    client._request = fake_request  # type: ignore[assignment]
    client.provider_add_model(
        provider="langgenius/openai_api_compatible/openai_api_compatible",
        model_name="mimo-v2.5-pro",
        api_key="sk-x",
        endpoint_url="http://newapi.test/v1",
    )
    assert captured["method"] == "POST"
    assert "/models/credentials" in str(captured["path"])
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "mimo-v2.5-pro"
    assert body["credentials"]["endpoint_url"] == "http://newapi.test/v1"
    assert body["credentials"]["api_key"] == "sk-x"
