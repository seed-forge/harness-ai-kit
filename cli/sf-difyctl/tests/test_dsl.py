from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from difyctl.console_api import ConsoleApiClient, ConsoleAuth, CONSOLE_ENDPOINTS, should_fallback
from difyctl.dsl_authoring import (
    build_app_dsl,
    build_edge,
    build_end_node,
    build_llm_node,
    build_start_node,
)
from difyctl.dsl_validate import validate_dsl
from difyctl.workflow_create import default_spec_payload, scaffold_dsl_from_spec, validate_spec_payload


# ── DSL authoring / validate round-trip ──────────────────────────────────


def _valid_workflow_dsl() -> dict:
    ids = ["1700000000001", "1700000000002", "1700000000003"]
    start = build_start_node(ids[0], [{"variable": "lead_text", "label": "Lead", "type": "text-input"}], col=0)
    llm = build_llm_node(ids[1], title="Classify", system_prompt="Classify {{#" + ids[0] + ".lead_text#}}", col=1)
    end = build_end_node(ids[2], [{"variable": "reply", "value_selector": [ids[1], "text"]}], col=2)
    edges = [
        build_edge(ids[0], ids[1], source_type="start", target_type="llm"),
        build_edge(ids[1], ids[2], source_type="llm", target_type="end"),
    ]
    return build_app_dsl(
        name="Lead Triage",
        mode="workflow",
        description="triage",
        nodes=[start, llm, end],
        edges=edges,
    )


def test_authored_dsl_passes_validation() -> None:
    report = validate_dsl(_valid_workflow_dsl(), target_version="0.6.0")
    assert report.ok, report.errors


def test_validate_rejects_unquoted_version() -> None:
    dsl = _valid_workflow_dsl()
    dsl["version"] = 0.6  # not a string
    report = validate_dsl(dsl)
    assert not report.ok
    assert any("quoted string" in e for e in report.errors)


def test_validate_detects_unreachable_node() -> None:
    dsl = _valid_workflow_dsl()
    # Drop the edge from start->llm so llm and end become unreachable.
    dsl["workflow"]["graph"]["edges"] = dsl["workflow"]["graph"]["edges"][1:]
    report = validate_dsl(dsl)
    assert not report.ok
    assert any("unreachable" in e for e in report.errors)


def test_validate_detects_cycle() -> None:
    dsl = _valid_workflow_dsl()
    nodes = dsl["workflow"]["graph"]["nodes"]
    llm_id = nodes[1]["id"]
    start_id = nodes[0]["id"]
    dsl["workflow"]["graph"]["edges"].append(
        build_edge(llm_id, start_id, source_type="llm", target_type="start")
    )
    report = validate_dsl(dsl)
    assert not report.ok
    assert any("cycle" in e for e in report.errors)


def test_validate_requires_llm_context() -> None:
    dsl = _valid_workflow_dsl()
    del dsl["workflow"]["graph"]["nodes"][1]["data"]["context"]
    report = validate_dsl(dsl)
    assert not report.ok
    assert any("context" in e for e in report.errors)


def test_validate_flags_unknown_variable_ref() -> None:
    dsl = _valid_workflow_dsl()
    dsl["workflow"]["graph"]["nodes"][1]["data"]["prompt_template"][0]["text"] = "{{#ghost_node.text#}}"
    report = validate_dsl(dsl)
    assert not report.ok
    assert any("unknown node" in e for e in report.errors)


def test_scaffold_output_is_valid() -> None:
    spec = default_spec_payload(
        name="Report",
        mode="workflow",
        goal="daily report",
        inputs=["snapshot_json"],
        outputs=["final_report"],
        steps=["Summarize", "Format"],
    )
    dsl = scaffold_dsl_from_spec(spec)
    report = validate_dsl(dsl, target_version="0.6.0")
    assert report.ok, report.errors


def test_spec_v2_code_step_requires_outputs() -> None:
    spec = {
        "version": 2,
        "workflow": {
            "name": "X",
            "mode": "workflow",
            "steps": [{"id": "s1", "name": "Parse", "type": "code"}],
        },
    }
    errors = validate_spec_payload(spec)
    assert any("outputs" in e for e in errors)


def test_spec_v2_rejects_reserved_error_output() -> None:
    spec = {
        "version": 2,
        "workflow": {
            "name": "X",
            "mode": "workflow",
            "steps": [{"id": "s1", "name": "Parse", "type": "code", "outputs": {"error": {"type": "string"}}}],
        },
    }
    errors = validate_spec_payload(spec)
    assert any("reserved output name" in e for e in errors)


def test_spec_v1_still_accepted() -> None:
    spec = {
        "version": 1,
        "workflow": {
            "name": "Legacy",
            "mode": "workflow",
            "steps": [{"id": "step_1", "name": "Do", "type": "llm"}],
        },
    }
    assert validate_spec_payload(spec) == []


# ── Console API DSL import/export (mocked) ────────────────────────────────


class _FakeResult:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self.payload = payload
        self.text = str(payload)


def test_console_endpoints_include_dsl_import_export() -> None:
    assert CONSOLE_ENDPOINTS["apps_imports"] == "/console/api/apps/imports"
    assert "{app_id}" in CONSOLE_ENDPOINTS["app_export"]


def test_app_import_dsl_builds_yaml_content_body(monkeypatch) -> None:
    auth = ConsoleAuth.detect("access_token=abc; csrf_token=xyz")
    client = ConsoleApiClient("https://dify.example.com", auth, 10)
    captured = {}

    def fake_post(path, body=None):
        captured["path"] = path
        captured["body"] = body
        return _FakeResult(200, {"id": "imp1", "status": "completed", "app_id": "app-99"})

    monkeypatch.setattr(client, "post", fake_post)
    result = client.app_import_dsl("version: \"0.6.0\"\n")
    assert captured["path"] == "/console/api/apps/imports"
    assert captured["body"]["mode"] == "yaml-content"
    assert result.payload["app_id"] == "app-99"


def test_should_fallback_triggers_on_5xx_not_4xx() -> None:
    assert should_fallback(502) is True
    assert should_fallback(503) is True
    assert should_fallback(400) is False
    assert should_fallback(404) is False


# ── Dual-track import decision logic (AC2) ────────────────────────────────

import types

from difyctl import cli
from difyctl.config import AppConfig


class _Args:
    via = "auto"
    console_key = "access_token=x; csrf_token=y"


def _cfg():
    return AppConfig(base_url="https://dify.example.com", timeout_seconds=5)


def test_import_api_success_builds_app_url(monkeypatch) -> None:
    monkeypatch.setattr(
        ConsoleApiClient,
        "app_import_dsl",
        lambda self, y, app_id="": types.SimpleNamespace(
            status_code=200,
            payload={"id": "imp1", "status": "completed", "app_id": "app-1", "imported_dsl_version": "0.6.0"},
            text="ok",
        ),
    )
    handled, payload = cli._dsl_import_via_api(_Args(), _cfg(), "version: \"0.6.0\"")
    assert handled is True
    assert payload["ok"] is True
    assert payload["app_url"] == "https://dify.example.com/app/app-1/workflow"


def test_import_api_502_under_auto_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(
        ConsoleApiClient,
        "app_import_dsl",
        lambda self, y, app_id="": types.SimpleNamespace(status_code=502, payload=None, text="bad gateway"),
    )
    handled, _ = cli._dsl_import_via_api(_Args(), _cfg(), "x")
    assert handled is False  # signals browser fallback


def test_import_api_400_under_auto_reports_error_no_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        ConsoleApiClient,
        "app_import_dsl",
        lambda self, y, app_id="": types.SimpleNamespace(status_code=400, payload={"message": "bad dsl"}, text="bad"),
    )
    handled, payload = cli._dsl_import_via_api(_Args(), _cfg(), "x")
    assert handled is True
    assert payload["ok"] is False


def test_import_api_pending_auto_confirms(monkeypatch) -> None:
    monkeypatch.setattr(
        ConsoleApiClient,
        "app_import_dsl",
        lambda self, y, app_id="": types.SimpleNamespace(status_code=200, payload={"id": "imp9", "status": "pending"}, text="p"),
    )
    monkeypatch.setattr(
        ConsoleApiClient,
        "app_import_confirm",
        lambda self, iid: types.SimpleNamespace(status_code=200, payload={"status": "completed", "app_id": "app-9"}, text="c"),
    )
    handled, payload = cli._dsl_import_via_api(_Args(), _cfg(), "x")
    assert handled is True
    assert payload["ok"] is True
    assert payload["app_id"] == "app-9"


# ── DSL version detection (adaptive to real Dify version) ─────────────────

from difyctl.dsl_detect_version import detect_dsl_version, PRODUCT_TO_DSL_MAP, _detect_by_product_version
from difyctl.dsl_authoring import DEFAULT_DSL_VERSION
from difyctl.workflow_create import scaffold_dsl_from_spec, default_spec_payload


def _spec():
    return default_spec_payload(name="V", mode="workflow", goal="g", inputs=["a"], outputs=["b"], steps=["S"])


def test_detect_via_export_reads_authoritative_version(monkeypatch):
    """Priority 1: exporting a real app reads its true DSL version."""
    import yaml as _yaml
    dsl = scaffold_dsl_from_spec(_spec(), dsl_version="0.5.0")
    monkeypatch.setattr(
        ConsoleApiClient, "app_export_dsl",
        lambda self, aid: types.SimpleNamespace(status_code=200, payload={"data": _yaml.safe_dump(dsl)}, text="ok"),
    )
    client = ConsoleApiClient("https://dify.example.com", ConsoleAuth.detect("access_token=x; csrf_token=y"), 5)
    version, source = detect_dsl_version(client, app_id="app-1")
    assert version == "0.5.0"
    assert source == "export:app-1"


def test_detect_via_product_version_1_13(monkeypatch):
    """Fallback: /console/api/version maps 1.13.x product to approximate DSL."""
    monkeypatch.setattr(
        ConsoleApiClient, "get",
        lambda self, path: types.SimpleNamespace(status_code=200, payload={"version": "1.13.2"}, text="ok"),
    )
    client = ConsoleApiClient("https://dify.example.com", ConsoleAuth.detect("access_token=x; csrf_token=y"), 5)
    version, source = _detect_by_product_version(client)
    # 1.13 maps to 0.5.x (approx) → returns safe default with approx marker
    assert "1.13" in source
    assert version == DEFAULT_DSL_VERSION  # safe default for uncertain .x


def test_detect_via_product_version_1_16_exact(monkeypatch):
    monkeypatch.setattr(
        ConsoleApiClient, "get",
        lambda self, path: types.SimpleNamespace(status_code=200, payload={"version": "1.16.0"}, text="ok"),
    )
    client = ConsoleApiClient("https://dify.example.com", ConsoleAuth.detect("access_token=x; csrf_token=y"), 5)
    version, source = _detect_by_product_version(client)
    assert version == "0.7.0"
    assert source == "version-api:1.16"


def test_scaffold_respects_explicit_dsl_version():
    dsl = scaffold_dsl_from_spec(_spec(), dsl_version="0.7.0")
    assert dsl["version"] == "0.7.0"


def test_scaffold_defaults_when_no_version():
    dsl = scaffold_dsl_from_spec(_spec())
    assert dsl["version"] == DEFAULT_DSL_VERSION


def test_build_app_dsl_rejects_malformed_version():
    import pytest
    with pytest.raises(ValueError):
        build_app_dsl(name="x", mode="workflow", description="d", nodes=[], edges=[], dsl_version="garbage")


def test_validate_warns_unknown_but_valid_version():
    """Unknown-but-semver version warns (not hard-fails) so detected versions pass."""
    from difyctl.dsl_validate import validate_dsl
    dsl = scaffold_dsl_from_spec(_spec(), dsl_version="0.5.0")
    report = validate_dsl(dsl)
    # 0.5.0 is outside KNOWN_VERSIONS but valid → warning, not error
    assert report.ok, report.errors
    assert any("0.5.0" in w for w in report.warnings)


def test_cmd_dsl_detect_version_prints_without_error(monkeypatch, capsys):
    """Regression: _cmd_dsl_detect_version must not raise NameError (json import).

    The 0.5.2 shipped version crashed here because it used json.dumps without
    importing json; the handler now uses print_json.
    """
    from difyctl import cli
    from difyctl.config import AppConfig

    monkeypatch.setattr(cli, "detect_dsl_version", lambda client, app_id=None, fallback_mode="auto": ("0.6.0", "export:app-x"))

    class _A:
        console_key = "access_token=x; csrf_token=y"
        app_id = "app-x"
        fallback_mode = "auto"

    cfg = AppConfig(base_url="https://dify.example.com", timeout_seconds=5)
    rc = cli._cmd_dsl_detect_version(_A(), cfg)
    assert rc == 0
    out = capsys.readouterr().out
    assert "0.6.0" in out
    assert "export:app-x" in out


def test_console_key_read_from_config_yaml(monkeypatch):
    """console_key must be read from assets.difyctl (config.yaml source of truth),
    not only from --console-key flag or profile (harness-ai-kit config governance)."""
    from difyctl import cli
    from difyctl.config import AppConfig

    # Simulate get_config() returning config.yaml assets.difyctl values
    monkeypatch.setattr(cli, "get_config", lambda: {"console_key": "access_token=cfg; csrf_token=cfg", "base_url": "https://dify.example.com"})

    class _A:
        console_key = None  # no CLI override
        base_url = None

    cfg = AppConfig(base_url="https://dify.example.com", timeout_seconds=5)
    base_url, console_key = cli._resolve_console_credential(_A(), cfg)
    assert console_key == "access_token=cfg; csrf_token=cfg", "console_key not read from config.yaml"


def test_console_key_cli_arg_overrides_config(monkeypatch):
    """CLI --console-key must win over config.yaml value."""
    from difyctl import cli
    from difyctl.config import AppConfig

    monkeypatch.setattr(cli, "get_config", lambda: {"console_key": "access_token=cfg; csrf_token=cfg"})

    class _A:
        console_key = "access_token=cli; csrf_token=cli"
        base_url = None

    cfg = AppConfig(base_url="https://dify.example.com", timeout_seconds=5)
    _, console_key = cli._resolve_console_credential(_A(), cfg)
    assert console_key == "access_token=cli; csrf_token=cli", "CLI arg should override config.yaml"


def _jwt_with_exp(exp_offset: int) -> str:
    import base64, json, time
    payload = {"exp": int(time.time()) + exp_offset}
    seg = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"access_token=h.{seg}.s; csrf_token=x"


def test_expired_console_key_auto_refreshes_and_writes_back(monkeypatch):
    """Expired config cookie triggers re-login, writeback to config.yaml, fresh key returned."""
    from difyctl import cli
    from difyctl.config import AppConfig

    expired = _jwt_with_exp(-100)
    fresh = _jwt_with_exp(+9999)
    monkeypatch.setattr(cli, "get_config", lambda: {"console_key": expired, "studio_username": "u@x.com", "studio_password": "p"})
    monkeypatch.setattr(cli, "capture_console_cookie", lambda **kw: {"full_cookie_header": fresh})
    saved = {}
    monkeypatch.setattr(cli, "write_unified_config_value", lambda k, v, **kw: saved.update({k: v}) or "cfg-path")

    class _A:
        console_key = None
        no_auto_refresh = False

    cfg = AppConfig(base_url="https://dify.example.com", timeout_seconds=5)
    _, key = cli._resolve_console_credential(_A(), cfg)
    assert key == fresh, "expired key should be auto-refreshed"
    assert saved.get("console_key") == fresh, "fresh cookie must be written back to config.yaml"


def test_fresh_console_key_not_refreshed(monkeypatch):
    """Non-expired cookie must NOT trigger a re-login (no browser launch)."""
    from difyctl import cli
    from difyctl.config import AppConfig

    fresh = _jwt_with_exp(+9999)
    monkeypatch.setattr(cli, "get_config", lambda: {"console_key": fresh})

    def _boom(**kw):
        raise AssertionError("capture_console_cookie must not be called for a fresh cookie")

    monkeypatch.setattr(cli, "capture_console_cookie", _boom)

    class _A:
        console_key = None
        no_auto_refresh = False

    cfg = AppConfig(base_url="https://dify.example.com", timeout_seconds=5)
    _, key = cli._resolve_console_credential(_A(), cfg)
    assert key == fresh


def test_no_auto_refresh_flag_skips_relogin(monkeypatch):
    """--no-auto-refresh keeps the expired key (no re-login)."""
    from difyctl import cli
    from difyctl.config import AppConfig

    expired = _jwt_with_exp(-100)
    monkeypatch.setattr(cli, "get_config", lambda: {"console_key": expired, "studio_username": "u", "studio_password": "p"})

    def _boom(**kw):
        raise AssertionError("must not re-login when --no-auto-refresh is set")

    monkeypatch.setattr(cli, "capture_console_cookie", _boom)

    class _A:
        console_key = None
        no_auto_refresh = True

    cfg = AppConfig(base_url="https://dify.example.com", timeout_seconds=5)
    _, key = cli._resolve_console_credential(_A(), cfg)
    assert key == expired


def test_linux_launch_prefers_chromium_and_no_sandbox(monkeypatch):
    """On Linux, bundled chromium is tried first and --no-sandbox is passed."""
    from difyctl import studio_browser as sb

    monkeypatch.setattr(sb.sys, "platform", "linux")
    candidates = sb._known_browser_candidates()
    assert candidates[0] == ("default", "chromium"), "Linux should try bundled chromium first"
    args = sb._browser_launch_args()
    assert "--no-sandbox" in args and "--disable-dev-shm-usage" in args


def test_windows_launch_keeps_channel_first_no_extra_args(monkeypatch):
    """On Windows, system channels are tried first and no sandbox args are added."""
    from difyctl import studio_browser as sb

    monkeypatch.setattr(sb.sys, "platform", "win32")
    candidates = sb._known_browser_candidates()
    assert candidates[0] == ("channel", "msedge")
    assert sb._browser_launch_args() == []


def test_launch_browser_passes_headless_and_args(monkeypatch):
    """_launch_browser honors headless and forwards Linux sandbox args to launch()."""
    from difyctl import studio_browser as sb

    monkeypatch.setattr(sb.sys, "platform", "linux")
    captured = {}

    class _Chromium:
        def launch(self, **kw):
            captured.update(kw)
            return "browser"

    class _PW:
        chromium = _Chromium()

    result = sb._launch_browser(_PW(), headless=True)
    assert result == "browser"
    assert captured.get("headless") is True
    assert "--no-sandbox" in captured.get("args", [])


# ── C3: resource_id naming validation ──

def test_validate_resource_id_accepts_valid():
    from difyctl.resource_ops import validate_resource_id
    for rid in ["sales-intake", "defi-protocol-advisor", "reddit-editorial-brain", "a1b", "novel-pre-2"]:
        assert validate_resource_id(rid) == rid


def test_validate_resource_id_rejects_invalid():
    import pytest
    from difyctl.resource_ops import validate_resource_id
    for bad in [
        "",                # empty
        "ab",              # too short (<3)
        "a" * 51,          # too long (>50)
        "Sales-Intake",    # uppercase
        "sales_intake",    # underscore
        "1sales",          # leading digit
        "-sales",          # leading hyphen
        "sales-",          # trailing hyphen
        "sales--intake",   # double hyphen
        "sales intake",    # space
        "defi/advisor",    # slash
    ]:
        with pytest.raises(ValueError):
            validate_resource_id(bad)


def test_derive_resource_id_slugifies():
    from difyctl.resource_ops import derive_resource_id, validate_resource_id
    assert derive_resource_id("DeFi Protocol Advisor!") == "defi-protocol-advisor"
    assert derive_resource_id("Sales  Intake") == "sales-intake"
    # derived value should be spec-valid for normal names
    assert validate_resource_id(derive_resource_id("Reddit Editorial Brain")) == "reddit-editorial-brain"


# ── O1: ledger.yaml single source of truth ──

def test_ledger_upsert_preserves_top_level_metadata(tmp_path):
    """Writing an entry must not drop version/ledger_type/runtime_system/maintainer."""
    import yaml
    from difyctl import registry_ops as r
    (tmp_path / "ledger.yaml").write_text(
        yaml.safe_dump({
            "version": 2, "ledger_type": "dify-resource",
            "runtime_system": "dify (x)", "maintainer": "example", "resources": [],
        }, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    r.upsert_registry_resource(tmp_path, {"resource_id": "sales-intake", "mode": "workflow"})
    data = yaml.safe_load((tmp_path / "ledger.yaml").read_text(encoding="utf-8"))
    assert data["runtime_system"] == "dify (x)"
    assert data["maintainer"] == "example"
    assert data["ledger_type"] == "dify-resource"
    assert data["resources"][0]["resource_id"] == "sales-intake"
    # v2 defaults filled
    assert data["resources"][0]["status"] == "development"
    assert data["resources"][0]["updated_at"]


def test_ledger_upsert_merges_not_replaces(tmp_path):
    """Second upsert with fewer fields must preserve existing dsl_version/status."""
    from difyctl import registry_ops as r
    r.upsert_registry_resource(tmp_path, {"resource_id": "x-app", "mode": "workflow", "dsl_version": "0.6.0", "status": "production"})
    r.upsert_registry_resource(tmp_path, {"resource_id": "x-app", "app_id": "abc-123"})
    entry = r.get_registry_resource(tmp_path, "x-app")
    assert entry["app_id"] == "abc-123"       # new field applied
    assert entry["dsl_version"] == "0.6.0"    # preserved (merge, not replace)
    assert entry["status"] == "production"    # preserved


def test_init_registry_idempotent_and_writes_ledger(tmp_path):
    from difyctl import registry_ops as r
    p1 = r.init_registry(tmp_path)
    assert p1.name == "ledger.yaml"
    r.upsert_registry_resource(tmp_path, {"resource_id": "keep-me", "mode": "workflow"})
    # second init must NOT wipe existing resources
    r.init_registry(tmp_path)
    assert r.get_registry_resource(tmp_path, "keep-me") is not None


def test_legacy_resources_yml_read_fallback(tmp_path):
    """When only resources.yml exists it is read; first write migrates to ledger.yaml."""
    import yaml
    from difyctl import registry_ops as r
    (tmp_path / "resources.yml").write_text(
        yaml.safe_dump({"version": 1, "resources": [{"resource_id": "old-app", "mode": "workflow"}]}, allow_unicode=True),
        encoding="utf-8",
    )
    assert r.registry_is_legacy_only(tmp_path) is True
    assert r.get_registry_resource(tmp_path, "old-app") is not None  # read from legacy
    r.upsert_registry_resource(tmp_path, {"resource_id": "new-app", "mode": "workflow"})
    assert (tmp_path / "ledger.yaml").exists()                       # migrated to ledger
    assert r.get_registry_resource(tmp_path, "old-app") is not None  # legacy data carried over
    assert r.get_registry_resource(tmp_path, "new-app") is not None


def test_canonical_dsl_path_is_file_form():
    from difyctl.registry_ops import canonical_dsl_path
    assert canonical_dsl_path("sales-intake") == "resources/sales-intake/dsl/current.yml"


# ── U5: import → ledger closed loop ──

def test_import_success_auto_registers_and_archives(tmp_path, monkeypatch):
    """A successful import archives the DSL to current.yml and upserts the ledger."""
    from difyctl import cli, registry_ops
    from difyctl.config import AppConfig

    dsl_file = tmp_path / "my-test-app.dify.yml"
    dsl_file.write_text("app:\n  name: My Test App\n  mode: workflow\nkind: app\nversion: \"0.6.0\"\n", encoding="utf-8")

    monkeypatch.setattr(
        cli, "_dsl_import_via_api",
        lambda a, c, y: (True, {"ok": True, "track": "api", "app_id": "test-app-123", "app_url": "http://x/app/test-app-123/workflow"}),
    )

    class _A:
        dsl = str(dsl_file)
        via = "api"
        skip_validate = True
        resource_id = None
        no_register = False

    cfg = AppConfig(base_url="http://x", workspace_dir=str(tmp_path), timeout_seconds=5)
    rc = cli._cmd_dsl_import(_A(), cfg)
    assert rc == 0
    # DSL archived under derived resource_id
    assert (tmp_path / "resources" / "my-test-app" / "dsl" / "current.yml").exists()
    # ledger upserted
    entry = registry_ops.get_registry_resource(tmp_path, "my-test-app")
    assert entry is not None
    assert entry["app_id"] == "test-app-123"
    assert entry["dsl_version"] == "0.6.0"
    assert entry["dsl_path"] == "resources/my-test-app/dsl/current.yml"


def test_import_no_register_flag_skips_ledger(tmp_path, monkeypatch):
    from difyctl import cli, registry_ops
    from difyctl.config import AppConfig

    dsl_file = tmp_path / "x.dify.yml"
    dsl_file.write_text("app:\n  name: Skip Me\n  mode: workflow\nkind: app\nversion: \"0.6.0\"\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_dsl_import_via_api", lambda a, c, y: (True, {"ok": True, "app_id": "z"}))

    class _A:
        dsl = str(dsl_file)
        via = "api"
        skip_validate = True
        resource_id = None
        no_register = True

    cfg = AppConfig(base_url="http://x", workspace_dir=str(tmp_path), timeout_seconds=5)
    rc = cli._cmd_dsl_import(_A(), cfg)
    assert rc == 0
    assert not (tmp_path / "ledger.yaml").exists()
    assert registry_ops.get_registry_resource(tmp_path, "skip-me") is None


# ── P1: app service-key + lifecycle client methods ──

def _key_client():
    auth = ConsoleAuth.detect("access_token=abc; csrf_token=xyz")
    return ConsoleApiClient("https://dify.example.com", auth, 10)


def test_app_key_endpoints_resolve():
    assert CONSOLE_ENDPOINTS["app_api_keys"] == "/console/api/apps/{app_id}/api-keys"
    assert "{api_key_id}" in CONSOLE_ENDPOINTS["app_api_key_delete"]
    assert CONSOLE_ENDPOINTS["app_detail"] == "/console/api/apps/{app_id}"


def test_app_keys_list_create_delete_paths(monkeypatch):
    client = _key_client()
    calls = {}
    monkeypatch.setattr(client, "get", lambda p: calls.setdefault("get", p) or _FakeResult(200, {"data": []}))
    monkeypatch.setattr(client, "post", lambda p, b=None: calls.setdefault("post", p) or _FakeResult(201, {"token": "app-xxx", "id": "k1"}))
    monkeypatch.setattr(client, "delete", lambda p: calls.setdefault("delete", p) or _FakeResult(204, {}))
    client.app_keys_list("app-1")
    client.app_key_create("app-1")
    client.app_key_delete("app-1", "k1")
    assert calls["get"] == "/console/api/apps/app-1/api-keys"
    assert calls["post"] == "/console/api/apps/app-1/api-keys"
    assert calls["delete"] == "/console/api/apps/app-1/api-keys/k1"


def test_app_update_uses_put(monkeypatch):
    client = _key_client()
    captured = {}

    def fake_request(method, path, body=None):
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return _FakeResult(200, {"id": "app-1", "name": "New"})

    monkeypatch.setattr(client, "_request", fake_request)
    client.app_update("app-1", {"name": "New", "description": "d"})
    assert captured["method"] == "PUT"
    assert captured["path"] == "/console/api/apps/app-1"
    assert captured["body"]["name"] == "New"


def test_app_delete_uses_delete_verb(monkeypatch):
    client = _key_client()
    captured = {}
    monkeypatch.setattr(client, "delete", lambda p: captured.setdefault("path", p) or _FakeResult(204, {}))
    client.app_delete("app-1")
    assert captured["path"] == "/console/api/apps/app-1"


def test_app_workflow_publish_path(monkeypatch):
    client = _key_client()
    captured = {}
    monkeypatch.setattr(client, "post", lambda p, b=None: captured.setdefault("path", p) or _FakeResult(200, {"result": "success"}))
    client.app_workflow_publish("app-1")
    assert captured["path"] == "/console/api/apps/app-1/workflows/publish"
    assert CONSOLE_ENDPOINTS["app_workflow_publish"] == "/console/api/apps/{app_id}/workflows/publish"


# ── P2: config app_keys map read/write ──

def test_write_app_key_multi_app_and_merge_preserve(tmp_path):
    import yaml
    from difyctl import config as cfgmod
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump({
        "role": "maintainer",
        "assets": {"difyctl": {"base_url": "http://x"}, "other": {"k": "v"}},
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    cfgmod.write_unified_app_key("app-1", "app-tok1", config_path=p)
    cfgmod.write_unified_app_key("app-2", "app-tok2", config_path=p)
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    # both keys present, not overwriting each other
    assert d["assets"]["difyctl"]["app_keys"] == {"app-1": "app-tok1", "app-2": "app-tok2"}
    # merge-preserve: top-level + other asset + existing difyctl field intact
    assert d["role"] == "maintainer"
    assert d["assets"]["other"] == {"k": "v"}
    assert d["assets"]["difyctl"]["base_url"] == "http://x"


def test_forget_app_key_removes_only_target(tmp_path):
    import yaml
    from difyctl import config as cfgmod
    p = tmp_path / "config.yaml"
    cfgmod.write_unified_app_key("app-1", "t1", config_path=p)
    cfgmod.write_unified_app_key("app-2", "t2", config_path=p)
    cfgmod.forget_unified_app_key("app-1", config_path=p)
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert d["assets"]["difyctl"]["app_keys"] == {"app-2": "t2"}


def test_resolve_app_key_priority(monkeypatch):
    from difyctl import config as cfgmod
    monkeypatch.setattr(cfgmod, "get_config", lambda: {"app_keys": {"app-1": "per-app-tok"}, "app_api_key": "fallback-tok"})
    assert cfgmod.resolve_app_key("app-1") == "per-app-tok"       # per-app wins
    assert cfgmod.resolve_app_key("unknown") == "fallback-tok"    # falls back to app_api_key
    monkeypatch.setattr(cfgmod, "get_config", lambda: {"app_api_key": "only-fallback"})
    assert cfgmod.resolve_app_key("app-x") == "only-fallback"


# ── P3: app keys create CLI (masking + config writeback) ──

def test_cmd_app_keys_create_saves_token_and_masks_ledger(monkeypatch, capsys):
    from difyctl import cli
    from difyctl.config import AppConfig
    import types as _t

    fake_client = _t.SimpleNamespace(
        app_key_create=lambda app_id: _FakeResult(201, {"token": "app-SECRETVALUE123", "id": "key-1", "created_at": 111}),
    )
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)
    saved = {}
    monkeypatch.setattr(cli, "write_unified_app_key", lambda app_id, token: saved.update({"app_id": app_id, "token": token}))
    monkeypatch.setattr(cli, "_ledger_entry_by_app_id", lambda c, aid: (None, ""))  # no ledger

    class _A:
        keys_command = "create"
        app_id = "app-1"

    rc = cli._cmd_app_keys(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0
    assert saved["token"] == "app-SECRETVALUE123"      # full token stored to config
    out = capsys.readouterr().out
    assert "app-SECRETVALUE123" in out                 # create prints full token once (by design)


def test_mask_token_hides_body():
    from difyctl.cli import _mask_token
    assert _mask_token("app-SECRETVALUE123") == "app-SECRE****"
    assert _mask_token("short") == "****"


# ── P4: app run mode-aware endpoint routing ──

def _run_args(**kw):
    class _A:
        app_id = "app-1"
        app_key = "app-tok"
        mode = ""
        inputs = ""
        query = ""
        user = "smoke"
        response_mode = "blocking"
        conversation_id = ""
    a = _A()
    for k, v in kw.items():
        setattr(a, k, v)
    return a


def test_app_run_timeout_override(monkeypatch):
    """`app run --timeout N` overrides config.timeout_seconds; 0 falls back to config."""
    from difyctl import cli
    from difyctl.config import AppConfig
    monkeypatch.setattr(cli, "resolve_app_key", lambda app_id: "app-tok")
    captured = {}

    def fake_core(base, key, mode, inputs, query, user, conv, timeout, force_stream=False, on_chunk=None):
        captured["timeout"] = timeout
        return {"ok": True, "mode": mode, "result": {}}

    monkeypatch.setattr(cli, "_run_app_core", fake_core)
    cfg = AppConfig(base_url="http://x", timeout_seconds=20)
    assert cli._cmd_app_run(_run_args(mode="workflow", timeout=150), cfg) == 0
    assert captured["timeout"] == 150
    assert cli._cmd_app_run(_run_args(mode="workflow", timeout=0), cfg) == 0
    assert captured["timeout"] == 20


def test_build_tool_node_schema():
    from difyctl.dsl_authoring import build_tool_node
    n = build_tool_node(
        "n1", title="搜索", provider_id="langgenius/searxng/searxng", tool_name="searxng_search",
        tool_parameters={"query": {"type": "mixed", "value": "{{#start.query#}}"}},
        tool_configurations={"search_type": "general"}, col=1,
    )
    d = n["data"]
    assert d["type"] == "tool" and n["type"] == "custom"
    assert d["provider_id"] == d["provider_name"] == "langgenius/searxng/searxng"
    assert d["provider_type"] == "builtin" and d["tool_name"] == "searxng_search"
    assert d["tool_configurations"] == {"search_type": "general"}  # raw, unwrapped
    assert d["tool_parameters"]["query"]["type"] == "mixed"
    assert d["retry_config"]["retry_enabled"] is True


def test_scaffold_tool_steps_and_reference_remap():
    """Two-stage tool spec scaffolds with correct topology + stable-id -> node-id remap."""
    from difyctl.workflow_create import scaffold_dsl_from_spec, validate_spec_payload
    spec = {
        "version": 2,
        "workflow": {
            "name": "DR", "mode": "workflow", "goal": "g",
            "inputs": [{"name": "query", "type": "text-input", "required": True}],
            "steps": [
                {"id": "sx", "name": "SearXNG", "type": "tool", "provider_id": "langgenius/searxng/searxng",
                 "tool_name": "searxng_search", "tool_configurations": {"search_type": "general"},
                 "tool_parameters": {"query": {"type": "mixed", "value": "{{#start.query#}}"}}},
                {"id": "pick", "name": "URL", "type": "template-transform",
                 "template": "{{ arg1[0]['url'] }}", "variables": [{"variable": "arg1", "value_selector": ["sx", "json"]}]},
                {"id": "fc", "name": "Firecrawl", "type": "tool", "provider_id": "langgenius/firecrawl/firecrawl",
                 "tool_name": "scrape", "tool_parameters": {"url": {"type": "mixed", "value": "{{#pick.output#}}"}}},
                {"id": "ans", "name": "LLM", "type": "llm", "instruction": "sys",
                 "user_prompt": "{{#fc.text#}} {{#start.query#}}"},
            ],
            "outputs": [{"name": "text", "value_selector": ["ans", "text"]},
                        {"name": "url", "value_selector": ["pick", "output"]}],
        },
    }
    assert validate_spec_payload(spec) == []
    dsl = scaffold_dsl_from_spec(spec)
    nodes = dsl["workflow"]["graph"]["nodes"]
    assert [n["data"]["type"] for n in nodes] == ["start", "tool", "template-transform", "tool", "llm", "end"]
    import yaml as _yaml
    blob = _yaml.safe_dump(dsl, allow_unicode=True)
    # no stable spec-ids leak into references
    for stale in ("#start.", "#sx.", "#pick.", "#fc.", "#ans."):
        assert stale not in blob, f"unremapped ref {stale}"
    # tool provider preserved; searxng query points at the generated start id
    start_id = nodes[0]["id"]
    sx = nodes[1]["data"]
    assert sx["provider_id"] == "langgenius/searxng/searxng"
    assert sx["tool_parameters"]["query"]["value"] == f"{{{{#{start_id}.query#}}}}"
    # template var_selector head remapped to searxng node id
    assert nodes[2]["data"]["variables"][0]["value_selector"][0] == nodes[1]["id"]


def test_app_run_routes_workflow_chat_completion(monkeypatch):
    from difyctl import cli
    from difyctl.config import AppConfig
    calls = []
    sse_calls = []
    monkeypatch.setattr(cli, "resolve_app_key", lambda app_id: "app-tok")
    monkeypatch.setattr(cli, "post_json", lambda base, key, ep, body, t: calls.append((ep, body)) or _FakeResult(200, {"data": {"outputs": {}}}))
    monkeypatch.setattr(cli, "post_sse", lambda base, key, ep, body, t, on_chunk=None: sse_calls.append((ep, body)) or _FakeResult(200, {"answer": "hi", "events": 3}))
    cfg = AppConfig(base_url="http://x", timeout_seconds=5)

    assert cli._cmd_app_run(_run_args(mode="workflow", inputs='{"text":"hi"}'), cfg) == 0
    assert calls[-1][0] == "/v1/workflows/run"

    assert cli._cmd_app_run(_run_args(mode="chat", query="hello"), cfg) == 0
    assert calls[-1][0] == "/v1/chat-messages"
    assert calls[-1][1]["query"] == "hello"
    assert calls[-1][1]["response_mode"] == "blocking"

    # agent-chat must stream (blocking is rejected by Dify) -> post_sse
    assert cli._cmd_app_run(_run_args(mode="agent-chat", query="hey"), cfg) == 0
    assert sse_calls[-1][0] == "/v1/chat-messages"

    assert cli._cmd_app_run(_run_args(mode="completion", query="q"), cfg) == 0
    assert calls[-1][0] == "/v1/completion-messages"
    assert calls[-1][1]["inputs"]["query"] == "q"


def test_app_run_chat_requires_query(monkeypatch):
    from difyctl import cli
    from difyctl.config import AppConfig
    monkeypatch.setattr(cli, "resolve_app_key", lambda app_id: "app-tok")
    rc = cli._cmd_app_run(_run_args(mode="chat"), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 1  # chat without --query fails


def test_post_sse_aggregates_answer(monkeypatch):
    """post_sse concatenates streamed answer chunks into one result."""
    from difyctl import api_client
    import io

    sse = (
        'data: {"event":"agent_message","answer":"Hello","conversation_id":"c1","message_id":"m1"}\n\n'
        'data: {"event":"agent_message","answer":" world","conversation_id":"c1"}\n\n'
        'data: {"event":"message_end","conversation_id":"c1"}\n\n'
    )

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __iter__(self): return iter(io.BytesIO(sse.encode("utf-8")))

    monkeypatch.setattr(api_client.request, "urlopen", lambda req, timeout=None: _Resp())
    r = api_client.post_sse("http://x", "app-tok", "/v1/chat-messages", {"query": "hi"}, 5)
    assert r.status_code == 200
    assert r.payload["answer"] == "Hello world"
    assert r.payload["conversation_id"] == "c1"
    assert r.payload["events"] == 3


# ── P5: import --create-key/--smoke closed loop ──

def test_import_create_key_and_smoke(tmp_path, monkeypatch):
    from difyctl import cli
    from difyctl.config import AppConfig
    import types as _t

    dsl_file = tmp_path / "loop-app.dify.yml"
    dsl_file.write_text("app:\n  name: Loop App\n  mode: workflow\nkind: app\nversion: \"0.6.0\"\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_dsl_import_via_api", lambda a, c, y: (True, {"ok": True, "app_id": "app-77"}))
    # fake console client for key creation
    fake_client = _t.SimpleNamespace(
        app_key_create=lambda app_id: _FakeResult(201, {"token": "app-LOOPTOKEN999", "id": "k9", "created_at": 1}),
        app_workflow_publish=lambda app_id: _FakeResult(200, {"result": "success"}),
    )
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)
    stored = {}
    monkeypatch.setattr(cli, "write_unified_app_key", lambda app_id, token: stored.update({app_id: token}))
    # fake the /v1 run
    runs = []
    monkeypatch.setattr(cli, "post_json", lambda base, key, ep, body, t: runs.append((ep, key)) or _FakeResult(200, {"data": {"outputs": {"ok": 1}}}))

    class _A:
        dsl = str(dsl_file)
        via = "api"
        skip_validate = True
        resource_id = "loop-app"
        no_register = False
        create_key = True
        smoke = True
        smoke_inputs = '{"text":"hi"}'
        smoke_query = ""

    cfg = AppConfig(base_url="http://x", workspace_dir=str(tmp_path), timeout_seconds=5)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli._cmd_dsl_import(_A(), cfg)
    assert rc == 0
    out = buf.getvalue()
    # service key stored (full token) but only masked prefix in the JSON payload
    assert stored.get("app-77") == "app-LOOPTOKEN999"
    assert "app-LOOPT****" in out            # masked prefix present
    assert "app-LOOPTOKEN999" not in out    # SECURITY: full token never in import output
    # smoke ran against workflow endpoint
    assert runs and runs[-1][0] == "/v1/workflows/run"


# ── P6: registry audit (live vs ledger diff) ──

def test_audit_against_live_classifies_three_ways():
    from difyctl.registry_ops import audit_against_live
    ledger = [
        {"resource_id": "keep", "app_id": "a1", "app_name": "Keep"},          # matches live, no drift
        {"resource_id": "zombie", "app_id": "gone", "app_name": "Gone"},      # not in live -> zombie
        {"resource_id": "renamed", "app_id": "a3", "app_name": "Old Name"},   # drift
        {"resource_id": "nolink", "app_id": "", "app_name": "No App"},        # no app_id -> ignored
    ]
    live = [
        {"id": "a1", "name": "Keep"},
        {"id": "a3", "name": "New Name"},     # drift vs ledger "Old Name"
        {"id": "a9", "name": "Unregistered"}, # in live not ledger
    ]
    report = audit_against_live(ledger, live)
    assert [z["resource_id"] for z in report["zombies"]] == ["zombie"]
    assert [u["app_id"] for u in report["unregistered"]] == ["a9"]
    assert [d["resource_id"] for d in report["drift"]] == ["renamed"]
    assert report["counts"] == {"ledger": 3, "live": 3, "zombies": 1, "unregistered": 1, "drift": 1, "duplicate_names": 0}


def test_audit_detects_duplicate_live_names():
    from difyctl.registry_ops import audit_against_live, find_live_apps_by_name
    live = [
        {"id": "a1", "name": "novel-pre"},
        {"id": "a2", "name": "novel-pre"},
        {"id": "a3", "name": "novel-pre"},
        {"id": "a4", "name": "Unique"},
    ]
    report = audit_against_live([], live)
    dn = report["duplicate_names"]
    assert len(dn) == 1 and dn[0]["name"] == "novel-pre" and dn[0]["count"] == 3
    assert set(dn[0]["app_ids"]) == {"a1", "a2", "a3"}
    assert report["counts"]["duplicate_names"] == 1
    # find_live_apps_by_name exact match
    assert set(find_live_apps_by_name(live, "novel-pre")) == {"a1", "a2", "a3"}
    assert find_live_apps_by_name(live, "Unique") == ["a4"]
    assert find_live_apps_by_name(live, "missing") == []


def test_import_dedup_blocks_same_name(monkeypatch, tmp_path):
    """Pre-flight dedup blocks import when a live app with the same name exists."""
    from difyctl import cli
    from difyctl.config import AppConfig
    import types as _t

    dsl_file = tmp_path / "dup.dify.yml"
    dsl_file.write_text("app:\n  name: Existing App\n  mode: workflow\nkind: app\nversion: \"0.6.0\"\n", encoding="utf-8")
    fake_client = _t.SimpleNamespace(apps_list=lambda p, l: _FakeResult(200, {"data": [{"id": "live-1", "name": "Existing App"}]}))
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)
    # import must NOT be attempted when blocked
    monkeypatch.setattr(cli, "_dsl_import_via_api", lambda a, c, y: (_ for _ in ()).throw(AssertionError("import should be blocked")))

    class _A:
        dsl = str(dsl_file)
        via = "api"
        skip_validate = True
        allow_duplicate = False

    rc = cli._cmd_dsl_import(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 1  # blocked


def test_import_allow_duplicate_bypasses_guard(monkeypatch, tmp_path):
    from difyctl import cli
    from difyctl.config import AppConfig

    dsl_file = tmp_path / "dup.dify.yml"
    dsl_file.write_text("app:\n  name: Existing App\n  mode: workflow\nkind: app\nversion: \"0.6.0\"\n", encoding="utf-8")
    # _console_client must not even be called when --allow-duplicate
    monkeypatch.setattr(cli, "_console_client", lambda a, c: (_ for _ in ()).throw(AssertionError("dedup check should be skipped")))
    monkeypatch.setattr(cli, "_dsl_import_via_api", lambda a, c, y: (True, {"ok": True, "app_id": "new-1"}))
    monkeypatch.setattr(cli, "_maybe_register_import", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_maybe_create_key_and_smoke", lambda *a, **k: None)

    class _A:
        dsl = str(dsl_file)
        via = "api"
        skip_validate = True
        allow_duplicate = True
        no_register = True

    rc = cli._cmd_dsl_import(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0  # allowed through


def test_app_lifecycle_rename_syncs_ledger(tmp_path, monkeypatch):
    from difyctl import cli, registry_ops
    from difyctl.config import AppConfig
    import types as _t
    # seed a ledger entry for app-1
    registry_ops.upsert_registry_resource(tmp_path, {"resource_id": "my-app", "mode": "workflow", "app_id": "app-1", "app_name": "Old", "title": "Old"})
    fake_client = _t.SimpleNamespace(
        app_get=lambda app_id: _FakeResult(200, {"icon": "🤖", "icon_type": "emoji", "description": "d"}),
        app_update=lambda app_id, fields: _FakeResult(200, {"id": app_id, "name": fields.get("name")}),
    )
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)

    class _A:
        app_command = "rename"
        app_id = "app-1"
        name = "New Name"
        description = None

    rc = cli._cmd_app_lifecycle(_A(), AppConfig(base_url="http://x", workspace_dir=str(tmp_path), timeout_seconds=5))
    assert rc == 0
    entry = registry_ops.get_registry_resource(tmp_path, "my-app")
    assert entry["title"] == "New Name" and entry["app_name"] == "New Name"


def test_app_lifecycle_delete_marks_deprecated(tmp_path, monkeypatch):
    from difyctl import cli, registry_ops
    from difyctl.config import AppConfig
    import types as _t
    registry_ops.upsert_registry_resource(tmp_path, {"resource_id": "dead-app", "mode": "workflow", "app_id": "app-2", "status": "production"})
    fake_client = _t.SimpleNamespace(app_delete=lambda app_id: _FakeResult(204, {}))
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)
    monkeypatch.setattr(cli, "forget_unified_app_key", lambda app_id: None)

    class _A:
        app_command = "delete"
        app_id = "app-2"
        yes = True

    rc = cli._cmd_app_lifecycle(_A(), AppConfig(base_url="http://x", workspace_dir=str(tmp_path), timeout_seconds=5))
    assert rc == 0
    assert registry_ops.get_registry_resource(tmp_path, "dead-app")["status"] == "deprecated"


def test_app_delete_requires_yes(tmp_path, monkeypatch):
    from difyctl import cli
    from difyctl.config import AppConfig
    import types as _t
    deleted = []
    fake_client = _t.SimpleNamespace(app_delete=lambda app_id: deleted.append(app_id) or _FakeResult(204, {}))
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)

    class _A:
        app_command = "delete"
        app_id = "app-9"
        yes = False
    rc = cli._cmd_app_lifecycle(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 1 and deleted == []  # blocked without --yes


# ── V1 runtime coverage: app runtime subcommands routing ──

def _runtime_cfg():
    from difyctl.config import AppConfig
    return AppConfig(base_url="http://x", timeout_seconds=10)


def _rt_args(**kw):
    class _A:
        app_command = ""
        app_id = "app-1"
        app_key = "app-tok"
    a = _A()
    for k, v in kw.items():
        setattr(a, k, v)
    return a


def test_runtime_commands_route_correct_method_and_path(monkeypatch):
    from difyctl import cli
    monkeypatch.setattr(cli, "resolve_app_key", lambda app_id: "app-tok")
    calls = []
    monkeypatch.setattr(cli, "request_v1", lambda method, base, key, path, body=None, timeout_seconds=30: calls.append((method, path, body)) or _FakeResult(200, {"ok": 1}))

    # run-status -> GET /v1/workflows/run/{id}
    assert cli._cmd_app_runtime(_rt_args(app_command="run-status", run_id="run-9"), _runtime_cfg()) == 0
    assert calls[-1][0] == "GET" and calls[-1][1] == "/v1/workflows/run/run-9"

    # stop -> POST /v1/workflows/tasks/{id}/stop with user
    assert cli._cmd_app_runtime(_rt_args(app_command="stop", task_id="t-1", user="u"), _runtime_cfg()) == 0
    assert calls[-1][0] == "POST" and calls[-1][1] == "/v1/workflows/tasks/t-1/stop" and calls[-1][2] == {"user": "u"}

    # logs -> GET /v1/workflows/logs?...
    assert cli._cmd_app_runtime(_rt_args(app_command="logs", page="1", limit="20", keyword=""), _runtime_cfg()) == 0
    assert calls[-1][0] == "GET" and calls[-1][1].startswith("/v1/workflows/logs?")

    # conversations / messages -> GET
    assert cli._cmd_app_runtime(_rt_args(app_command="conversations", user="u", limit="20"), _runtime_cfg()) == 0
    assert calls[-1][1].startswith("/v1/conversations?")
    assert cli._cmd_app_runtime(_rt_args(app_command="messages", conversation_id="c1", user="u", limit="20"), _runtime_cfg()) == 0
    assert calls[-1][1].startswith("/v1/messages?") and "conversation_id=c1" in calls[-1][1]

    # conversation-delete -> DELETE
    assert cli._cmd_app_runtime(_rt_args(app_command="conversation-delete", conversation_id="c1", user="u"), _runtime_cfg()) == 0
    assert calls[-1][0] == "DELETE" and calls[-1][1] == "/v1/conversations/c1"

    # conversation-rename -> POST /name
    assert cli._cmd_app_runtime(_rt_args(app_command="conversation-rename", conversation_id="c1", name="New", auto_generate=False, user="u"), _runtime_cfg()) == 0
    assert calls[-1][0] == "POST" and calls[-1][1] == "/v1/conversations/c1/name" and calls[-1][2]["name"] == "New"

    # feedback -> POST /feedbacks; rating null -> None
    assert cli._cmd_app_runtime(_rt_args(app_command="feedback", message_id="m1", rating="null", content="", user="u"), _runtime_cfg()) == 0
    assert calls[-1][1] == "/v1/messages/m1/feedbacks" and calls[-1][2]["rating"] is None

    # suggested -> GET
    assert cli._cmd_app_runtime(_rt_args(app_command="suggested", message_id="m1", user="u"), _runtime_cfg()) == 0
    assert calls[-1][1].startswith("/v1/messages/m1/suggested?")


def test_runtime_upload_and_audio_use_multipart(monkeypatch, tmp_path):
    from difyctl import cli
    monkeypatch.setattr(cli, "resolve_app_key", lambda app_id: "app-tok")
    f = tmp_path / "x.txt"
    f.write_text("hi", encoding="utf-8")
    mp = []
    monkeypatch.setattr(cli, "post_multipart", lambda base, key, path, file_path, fields=None, file_field="file", timeout_seconds=120: mp.append((path, file_path)) or _FakeResult(201, {"id": "file-1"}))

    assert cli._cmd_app_runtime(_rt_args(app_command="upload", file=str(f), user="u"), _runtime_cfg()) == 0
    assert mp[-1][0] == "/v1/files/upload"
    assert cli._cmd_app_runtime(_rt_args(app_command="audio-to-text", file=str(f), user="u"), _runtime_cfg()) == 0
    assert mp[-1][0] == "/v1/audio-to-text"


def test_runtime_text_to_audio_uses_binary(monkeypatch, tmp_path):
    from difyctl import cli
    monkeypatch.setattr(cli, "resolve_app_key", lambda app_id: "app-tok")
    out = str(tmp_path / "out.mp3")
    calls = []
    monkeypatch.setattr(cli, "post_binary", lambda base, key, path, body, out_path, timeout_seconds=120: calls.append((path, body, out_path)) or _FakeResult(200, {"out_path": out_path, "bytes": 10}))
    assert cli._cmd_app_runtime(_rt_args(app_command="text-to-audio", text="hi", message_id="", output=out, user="u"), _runtime_cfg()) == 0
    assert calls[-1][0] == "/v1/text-to-audio" and calls[-1][1]["text"] == "hi" and calls[-1][2] == out


def test_run_stream_flag_forces_sse_for_chat(monkeypatch):
    from difyctl import cli
    monkeypatch.setattr(cli, "resolve_app_key", lambda app_id: "app-tok")
    sse = []
    monkeypatch.setattr(cli, "post_sse", lambda base, key, ep, body, t, on_chunk=None: sse.append(ep) or _FakeResult(200, {"answer": "hi"}))
    monkeypatch.setattr(cli, "post_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not use blocking when --stream")))
    rc = cli._cmd_app_run(_run_args(mode="chat", query="hello", stream=True), _runtime_cfg())
    assert rc == 0 and sse[-1] == "/v1/chat-messages"


def test_encode_multipart_structure():
    from difyctl.api_client import _encode_multipart
    import tempfile, os
    fd, p = tempfile.mkstemp(suffix=".txt")
    os.write(fd, b"hello"); os.close(fd)
    try:
        ct, body = _encode_multipart({"user": "u"}, "file", p)
        assert ct.startswith("multipart/form-data; boundary=")
        assert b'name="user"' in body and b'filename=' in body and b"hello" in body
    finally:
        os.remove(p)


# ── 0.9.0: update-in-place + diff + registry sync/prune ──

def test_app_import_dsl_passes_app_id_for_update():
    """console_api includes app_id in the imports payload only when set (update mode)."""
    from difyctl.console_api import ConsoleApiClient, ConsoleAuth
    captured = {}

    client = ConsoleApiClient("http://x", ConsoleAuth("cookie", "k"), 10)
    client.post = lambda path, body: captured.update(path=path, body=body) or _FakeResult(200, {"status": "completed", "app_id": body.get("app_id", "new")})
    client.app_import_dsl("yaml", app_id="app-42")
    assert captured["body"]["app_id"] == "app-42" and captured["body"]["mode"] == "yaml-content"
    client.app_import_dsl("yaml")
    assert "app_id" not in captured["body"]  # create mode omits app_id


def test_preflight_dedup_app_id_bypasses_and_update_if_exists(monkeypatch):
    from difyctl import cli
    from difyctl.config import AppConfig
    cfg = AppConfig(base_url="http://x", timeout_seconds=5)

    # explicit --app-id -> proceed as update, no live lookup
    class _A1:
        app_id = "app-9"
        allow_duplicate = False
        update_if_exists = False
    proceed, info = cli._preflight_dedup_check(_A1(), cfg, "app:\n  name: X\n")
    assert proceed and info["dedup"] == "update-in-place"

    # --update-if-exists with exactly one same-name app -> sets args.app_id
    fake_client = type("C", (), {"apps_list": lambda self, p, l: _FakeResult(200, {"data": [{"id": "live-7", "name": "Solo"}]})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)

    class _A2:
        app_id = ""
        allow_duplicate = False
        update_if_exists = True
    a2 = _A2()
    proceed, info = cli._preflight_dedup_check(a2, cfg, "app:\n  name: Solo\n")
    assert proceed and a2.app_id == "live-7" and info["dedup"].startswith("update-if-exists")


def test_preflight_update_if_exists_ambiguous_blocks(monkeypatch):
    from difyctl import cli
    from difyctl.config import AppConfig
    fake_client = type("C", (), {"apps_list": lambda self, p, l: _FakeResult(200, {"data": [{"id": "a1", "name": "Dup"}, {"id": "a2", "name": "Dup"}]})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake_client)

    class _A:
        app_id = ""
        allow_duplicate = False
        update_if_exists = True
    proceed, info = cli._preflight_dedup_check(_A(), AppConfig(base_url="http://x", timeout_seconds=5), "app:\n  name: Dup\n")
    assert not proceed and info["dedup"] == "ambiguous" and len(info["existing_app_ids"]) == 2


def test_dsl_diff_reports_identical_and_changes(monkeypatch, tmp_path):
    from difyctl import cli
    from difyctl.config import AppConfig
    dsl_file = tmp_path / "a.yml"
    dsl_file.write_text("app:\n  name: A\n  mode: workflow\n", encoding="utf-8")
    # identical live
    fake = type("C", (), {"app_export_dsl": lambda self, aid: _FakeResult(200, {"data": "app:\n  name: A\n  mode: workflow\n"})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)

    class _A:
        app_id = "x"
        dsl = str(dsl_file)
    rc = cli._cmd_dsl_diff(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0
    # changed live
    fake2 = type("C", (), {"app_export_dsl": lambda self, aid: _FakeResult(200, {"data": "app:\n  name: A\n  mode: chat\n"})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake2)
    rc = cli._cmd_dsl_diff(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0


def test_registry_sync_backfills_untracked(monkeypatch, tmp_path):
    from difyctl import cli
    from difyctl.config import AppConfig
    from difyctl import registry_ops
    registry_ops.init_registry(tmp_path)
    registry_ops.upsert_registry_resource(tmp_path, {"resource_id": "tracked-one", "app_id": "known-1", "mode": "workflow", "title": "T"})
    fake = type("C", (), {"apps_list": lambda self, p, l: _FakeResult(200, {"data": [
        {"id": "known-1", "name": "Tracked"}, {"id": "new-1", "name": "Fresh App"}, {"id": "new-2", "name": "Fresh App"}]})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)
    monkeypatch.setattr(cli, "_require_workspace", lambda c: tmp_path)

    class _A:
        status = "untracked"
        dry_run = False
    rc = cli._cmd_registry_sync(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0
    ids = {str(e.get("app_id")) for e in registry_ops.list_registry_resources(tmp_path)}
    assert {"known-1", "new-1", "new-2"} <= ids  # both untracked backfilled (resource_id collision handled)


def test_registry_prune_duplicates_dry_run_plans(monkeypatch, tmp_path):
    from difyctl import cli
    from difyctl.config import AppConfig
    fake = type("C", (), {"apps_list": lambda self, p, l: _FakeResult(200, {"data": [
        {"id": "old", "name": "Dup", "created_at": "2024-01-01"},
        {"id": "new", "name": "Dup", "created_at": "2024-06-01"},
        {"id": "solo", "name": "Solo", "created_at": "2024-01-01"}]})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)
    monkeypatch.setattr(cli, "_require_workspace", lambda c: tmp_path)
    deleted = []
    fake.app_delete = lambda aid: deleted.append(aid)

    class _A:
        keep = "newest"
        apply = False
    rc = cli._cmd_registry_prune_duplicates(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0 and deleted == []  # dry-run deletes nothing


# ── 0.10.0: knowledge bases + export --all + output hygiene ──

def test_console_parse_error_tolerates_non_json():
    """_parse_error / _safe_json must not crash on HTML/non-JSON error bodies."""
    from difyctl.console_api import _safe_json
    assert _safe_json("<!doctype html><html>404</html>") is None
    assert _safe_json("") is None
    assert _safe_json('{"a": 1}') == {"a": 1}


def test_dataset_list_paginates_and_reports(monkeypatch, capsys):
    from difyctl import cli
    from difyctl.config import AppConfig
    fake = type("C", (), {"datasets_list": lambda self, p, l: _FakeResult(200, {"data": [
        {"id": "d1", "name": "KB1", "document_count": 3, "indexing_technique": "high_quality", "permission": "only_me"}],
        "has_more": False, "total": 1})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)

    class _A:
        dataset_command = "list"
        limit = "30"
    rc = cli._cmd_dataset(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    out = capsys.readouterr().out
    assert rc == 0 and '"KB1"' in out and '"total": 1' in out


def test_dataset_delete_requires_yes(monkeypatch, capsys):
    from difyctl import cli
    from difyctl.config import AppConfig
    deleted = []
    fake = type("C", (), {"dataset_delete": lambda self, did: deleted.append(did) or _FakeResult(204, None)})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)

    class _NoYes:
        dataset_command = "delete"
        dataset_id = "d1"
        yes = False
        limit = "30"
    rc = cli._cmd_dataset(_NoYes(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 1 and deleted == []  # blocked without --yes

    class _Yes:
        dataset_command = "delete"
        dataset_id = "d1"
        yes = True
        limit = "30"
    rc = cli._cmd_dataset(_Yes(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0 and deleted == ["d1"]


def test_dataset_create(monkeypatch, capsys):
    from difyctl import cli
    from difyctl.config import AppConfig
    fake = type("C", (), {"dataset_create": lambda self, n, i, p, d="": _FakeResult(201, {"id": "new-ds", "name": n, "indexing_technique": i})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)

    class _A:
        dataset_command = "create"
        name = "MyKB"
        indexing_technique = "economy"
        permission = "only_me"
        description = ""
        limit = "30"
    rc = cli._cmd_dataset(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    out = capsys.readouterr().out
    assert rc == 0 and '"new-ds"' in out


def test_dsl_export_all_backs_up_every_app(monkeypatch, tmp_path):
    from difyctl import cli
    from difyctl.config import AppConfig
    monkeypatch.setattr(cli, "_resolve_console_credential", lambda a, c: ("http://x", "sk"))
    monkeypatch.setattr(cli, "ConsoleAuth", type("CA", (), {"detect": staticmethod(lambda k: object())}))

    class _Client:
        def app_export_dsl(self, app_id):
            return _FakeResult(200, {"data": f"app:\n  name: {app_id}\n"})
    monkeypatch.setattr(cli, "ConsoleApiClient", lambda b, a, t: _Client())
    monkeypatch.setattr(cli, "_list_all_apps", lambda client: [{"id": "a1"}, {"id": "a2"}])

    class _A:
        all = True
        output_dir = str(tmp_path / "backup")
        app_id = ""
        output = ""
    rc = cli._cmd_dsl_export(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0
    assert (tmp_path / "backup" / "a1.dify.yml").exists()
    assert (tmp_path / "backup" / "a2.dify.yml").exists()


# ── 0.11.0 Phase 2: lint + retarget + retry ──

def test_lint_flags_hardcoded_secret_and_dangling_ref():
    from difyctl.dsl_lint import lint_dsl
    doc = {
        "app": {"name": "X", "mode": "workflow"},
        "workflow": {"graph": {"nodes": [
            {"id": "start", "data": {"type": "start"}},
            {"id": "llm1", "data": {"type": "llm", "model": {"name": "gpt-4o"},
                                     "prompt": "use {{#missing_node.text#}} and {{#start.q#}}"}},
            {"id": "tool1", "data": {"type": "tool", "tool_configurations": {"api_key": "sk-abcdef1234567890"}}},
        ]}},
    }
    report = lint_dsl(doc)
    assert report["ok"] is False  # secret -> error
    assert report["findings"]["secrets"]  # found the api_key
    assert "missing_node" in report["findings"]["dangling_refs"]
    assert "start" not in report["findings"]["dangling_refs"]  # valid ref


def test_lint_clean_dsl_passes():
    from difyctl.dsl_lint import lint_dsl
    doc = {"app": {"name": "Clean"}, "workflow": {"graph": {"nodes": [
        {"id": "llm1", "data": {"type": "llm", "model": {"name": "gpt-4o"}}}]}}}
    report = lint_dsl(doc)
    assert report["ok"] is True and not report["errors"]


def test_lint_ignores_variable_placeholders_as_secrets():
    from difyctl.dsl_lint import lint_dsl
    doc = {"nodes_cfg": {"api_key": "{{#env.OPENAI_KEY#}}"}, "workflow": {"graph": {"nodes": []}}}
    assert lint_dsl(doc)["findings"]["secrets"] == []  # variable ref not a secret


def test_retarget_rewrites_llm_and_model_config():
    from difyctl.dsl_lint import retarget_dsl
    doc = {
        "model_config": {"model": {"provider": "old", "name": "old-model", "mode": "chat"}},
        "workflow": {"graph": {"nodes": [
            {"id": "llm1", "data": {"type": "llm", "model": {"provider": "old", "name": "old-model"}}},
            {"id": "llm2", "data": {"type": "llm", "model": {"provider": "old", "name": "old-model"}}},
            {"id": "code1", "data": {"type": "code"}},  # no model -> untouched
        ]}},
    }
    doc, changed = retarget_dsl(doc, "langgenius/ollama/ollama", "qwen2.5:7b", mode="chat")
    assert changed == 3  # 2 llm nodes + model_config
    assert doc["workflow"]["graph"]["nodes"][0]["data"]["model"]["name"] == "qwen2.5:7b"
    assert doc["model_config"]["model"]["provider"] == "langgenius/ollama/ollama"


def test_console_should_retry_is_safe():
    from difyctl.console_api import ConsoleApiClient
    # server load-shedding: retry any method
    assert ConsoleApiClient._should_retry("POST", 429) is True
    assert ConsoleApiClient._should_retry("DELETE", 503) is True
    # GET idempotent: retry transient
    assert ConsoleApiClient._should_retry("GET", 500) is True
    assert ConsoleApiClient._should_retry("GET", 0) is True
    # ambiguous 5xx on writes: NOT retried (avoid double create)
    assert ConsoleApiClient._should_retry("POST", 500) is False
    assert ConsoleApiClient._should_retry("POST", 0) is False
    # success never retried
    assert ConsoleApiClient._should_retry("GET", 200) is False


def test_dsl_apply_creates_updates_and_skips(monkeypatch, tmp_path):
    from difyctl import cli
    from difyctl.config import AppConfig
    d = tmp_path / "dsls"
    d.mkdir()
    (d / "new.dify.yml").write_text("app:\n  name: BrandNew\n  mode: workflow\n", encoding="utf-8")
    (d / "existing.dify.yml").write_text("app:\n  name: Existing\n  mode: workflow\n", encoding="utf-8")
    (d / "dup.dify.yml").write_text("app:\n  name: Dup\n  mode: workflow\n", encoding="utf-8")
    live = [{"id": "e1", "name": "Existing"}, {"id": "d1", "name": "Dup"}, {"id": "d2", "name": "Dup"}]
    calls = []

    class _Client:
        def app_import_dsl(self, text, app_id=""):
            calls.append(app_id)
            return _FakeResult(200, {"status": "completed", "app_id": app_id or "created-new"})
    monkeypatch.setattr(cli, "_console_client", lambda a, c: _Client())
    monkeypatch.setattr(cli, "_list_all_apps", lambda client: live)

    class _A:
        dir = str(d)
        publish = False
        dry_run = False
    rc = cli._cmd_dsl_apply(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    # BrandNew -> create (app_id=""), Existing -> update (app_id="e1"), Dup -> skip (ambiguous)
    assert "" in calls and "e1" in calls
    assert not any(c in ("d1", "d2") for c in calls)  # ambiguous never imported
    assert rc == 0


def test_dsl_apply_dry_run_plans_without_calling(monkeypatch, tmp_path):
    from difyctl import cli
    from difyctl.config import AppConfig
    d = tmp_path / "dsls"
    d.mkdir()
    (d / "x.dify.yml").write_text("app:\n  name: Existing\n  mode: workflow\n", encoding="utf-8")

    class _Client:
        def app_import_dsl(self, text, app_id=""):
            raise AssertionError("dry-run must not import")
    monkeypatch.setattr(cli, "_console_client", lambda a, c: _Client())
    monkeypatch.setattr(cli, "_list_all_apps", lambda client: [{"id": "e1", "name": "Existing"}])

    class _A:
        dir = str(d)
        publish = False
        dry_run = True
    rc = cli._cmd_dsl_apply(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    assert rc == 0


# ── 0.12.0 Phase 3: annotations + add-doc + quiet + streaming + integration ──

def test_app_annotations_list(monkeypatch, capsys):
    from difyctl import cli
    from difyctl.config import AppConfig
    fake = type("C", (), {"app_annotations": lambda self, a, p, l: _FakeResult(200, {"data": [
        {"id": "an1", "question": "q?", "answer": "a", "hit_count": 2}], "total": 1})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)

    class _A:
        app_command = "annotations"
        app_id = "app-1"
        limit = "20"
    rc = cli._cmd_app_annotations(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    out = capsys.readouterr().out
    assert rc == 0 and '"an1"' in out and '"total": 1' in out


def test_dataset_add_doc_resolves_key_and_posts(monkeypatch, capsys):
    from difyctl import cli
    from difyctl.config import AppConfig
    fake = type("C", (), {"dataset_api_keys": lambda self: _FakeResult(200, {"data": [{"token": "dataset-XYZ"}]})})()
    monkeypatch.setattr(cli, "_console_client", lambda a, c: fake)
    posted = {}
    monkeypatch.setattr(cli, "post_json", lambda base, key, path, body, t: posted.update(key=key, path=path, body=body) or _FakeResult(200, {"document": {"id": "doc-1"}, "batch": "b1"}))

    class _A:
        dataset_command = "add-doc"
        dataset_id = "ds-1"
        name = "d"
        text = "hello content"
        file = ""
        indexing_technique = "economy"
        dataset_key = ""
        limit = "30"
    rc = cli._cmd_dataset(_A(), AppConfig(base_url="http://x", timeout_seconds=5))
    out = capsys.readouterr().out
    assert rc == 0 and posted["key"] == "dataset-XYZ"
    assert posted["path"] == "/v1/datasets/ds-1/document/create-by-text"
    assert '"doc-1"' in out


def test_quiet_suppresses_eprint(monkeypatch, capsys):
    from difyctl import cli
    cli._QUIET = True
    try:
        cli.eprint("should not appear")
        err = capsys.readouterr().err
        assert "should not appear" not in err
    finally:
        cli._QUIET = False
    cli.eprint("should appear")
    assert "should appear" in capsys.readouterr().err


def test_post_sse_on_chunk_callback(monkeypatch):
    """post_sse invokes on_chunk per answer chunk and still aggregates."""
    from difyctl import api_client

    class _Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __iter__(self):
            for line in [b'data: {"event":"message","answer":"He"}',
                         b'data: {"event":"message","answer":"llo"}',
                         b'data: {"event":"message_end"}']:
                yield line
    monkeypatch.setattr(api_client.request, "urlopen", lambda req, timeout=0: _Resp())
    chunks = []
    res = api_client.post_sse("http://x", "app-k", "/v1/chat-messages", {"query": "hi", "user": "u"}, 5, on_chunk=chunks.append)
    assert res.status_code == 200
    assert chunks == ["He", "llo"] and res.payload["answer"] == "Hello"


def test_integration_console_client_over_real_http():
    """Integration: ConsoleApiClient talks real HTTP to a localhost mock (parse + status)."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from difyctl.console_api import ConsoleApiClient, ConsoleAuth

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass
        def do_GET(self):
            if self.path.startswith("/console/api/datasets"):
                body = b'{"data":[{"id":"d1","name":"KB"}],"has_more":false,"total":1}'
                self.send_response(200)
            else:
                body = b'<!doctype html>not found'
                self.send_response(404)
            self.send_header("Content-Type", "application/json" if self.path.startswith("/console") else "text/html")
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        client = ConsoleApiClient(f"http://127.0.0.1:{port}", ConsoleAuth("cookie", "k"), 5, retries=0)
        ok = client.datasets_list(1, 30)
        assert ok.status_code == 200 and ok.payload["data"][0]["id"] == "d1"
        # non-JSON 404 must not crash (safe parse)
        miss = client.get("/nope")
        assert miss.status_code == 404 and miss.payload is None
    finally:
        srv.shutdown()





