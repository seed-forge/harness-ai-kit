from __future__ import annotations

from pathlib import Path
import shutil
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

import argparse
import json

from difyctl.cli import _discover_project_secrets, _resolve_effective_remote_config
from difyctl.config import AppConfig, merge_config, normalize_base_url
from difyctl.resource_ops import capture_dsl, ensure_resource, scan_resources, summarize_dsl, workspace_root
from difyctl.studio_browser import (
    _app_id_from_url,
    _click_first,
    _fill_first,
    _mode_label_for_create,
    StudioAutomationError,
)
from difyctl.workflow_create import default_spec_payload, scaffold_dsl_from_spec


TEST_WORK_ROOT = Path(__file__).resolve().parent / ".tmp-runtime"
TEST_WORK_ROOT.mkdir(parents=True, exist_ok=True)


def _make_case_dir(prefix: str) -> Path:
    path = TEST_WORK_ROOT / f"{prefix}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def test_merge_config_overrides_selected_fields() -> None:
    saved = AppConfig(base_url="https://old", app_api_key="old", workspace_dir="C:/tmp", timeout_seconds=10)
    merged = merge_config(saved, base_url="https://new", timeout_seconds=30)
    assert merged.base_url == "https://new"
    assert merged.app_api_key == "old"
    assert merged.timeout_seconds == 30


def test_normalize_base_url_strips_trailing_v1() -> None:
    assert normalize_base_url("https://dify.example.com/v1") == "https://dify.example.com"
    assert normalize_base_url("https://dify.example.com/") == "https://dify.example.com"


def test_discover_project_secrets_reads_parent_env() -> None:
    tmp_path = _make_case_dir("env-discovery")
    try:
        project_root = tmp_path / "project"
        workspace = project_root / "dify-workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        env_path = project_root / ".env"
        env_path.write_text(
            'DIFY_BASE_URL="https://dify.example.com/v1"\nDIFY_API_KEY="app-123"\n',
            encoding="utf-8",
        )
        base_url, api_key, source_path, api_key_name = _discover_project_secrets(str(workspace))
        assert base_url == "https://dify.example.com"
        assert api_key == "app-123"
        assert source_path == str(env_path)
        assert api_key_name == "DIFY_API_KEY"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_resolve_effective_remote_config_prefers_env_base_and_project_api_key() -> None:
    tmp_path = _make_case_dir("remote-config")
    old_env = os.environ.get("DIFY_BASE_URL")
    try:
        os.environ["DIFY_BASE_URL"] = "https://env.example.com/v1"
        project_root = tmp_path / "project"
        workspace = project_root / "dify-workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        (project_root / ".env").write_text('DIFY_API_KEY="app-xyz"\n', encoding="utf-8")
        config = AppConfig(workspace_dir=str(workspace))
        base_url, api_key, source = _resolve_effective_remote_config(config)
        assert base_url == "https://env.example.com"
        assert api_key == "app-xyz"
        assert source["base_url"] == "env:DIFY_BASE_URL"
        assert source["app_api_key"] == "project-env:DIFY_API_KEY"
    finally:
        if old_env is None:
            os.environ.pop("DIFY_BASE_URL", None)
        else:
            os.environ["DIFY_BASE_URL"] = old_env
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_browser_doctor_uses_effective_base_url_resolution() -> None:
    tmp_path = _make_case_dir("browser-doctor")
    old_env = os.environ.get("DIFY_BASE_URL")
    try:
        os.environ["DIFY_BASE_URL"] = "https://env.example.com/v1"
        project_root = tmp_path / "project"
        workspace = project_root / "dify-workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        config = AppConfig(workspace_dir=str(workspace))
        base_url, _, source = _resolve_effective_remote_config(config)
        assert base_url == "https://env.example.com"
        assert source["base_url"] == "env:DIFY_BASE_URL"
    finally:
        if old_env is None:
            os.environ.pop("DIFY_BASE_URL", None)
        else:
            os.environ["DIFY_BASE_URL"] = old_env
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_resource_init_and_capture() -> None:
    tmp_path = _make_case_dir("resource")
    try:
        root = workspace_root(str(tmp_path / "workspace"))
        dsl_path = tmp_path / "demo.yml"
        dsl_path.write_text(
            "app:\n  name: Demo\nworkflow:\n  graph:\n    nodes:\n      - id: start\n    edges: []\n",
            encoding="utf-8",
        )

        record = ensure_resource(
            root,
            resource_id="demo-workflow",
            mode="workflow",
            title="Demo Workflow",
            app_id="",
            app_name="",
            tags=["demo"],
        )
        assert record.resource_id == "demo-workflow"

        captured = capture_dsl(root, "demo-workflow", dsl_path, label="initial")
        assert Path(captured["snapshot_path"]).exists()
        assert Path(captured["current_path"]).exists()

        records = scan_resources(root)
        assert len(records) == 1
        assert records[0].resource_id == "demo-workflow"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_summarize_dsl_counts_graph_nodes() -> None:
    tmp_path = _make_case_dir("dsl")
    try:
        dsl_path = tmp_path / "sample.yml"
        dsl_path.write_text(
            "app:\n  name: Sample App\nworkflow:\n  graph:\n    nodes:\n      - id: start\n      - id: llm\n    edges:\n      - source: start\n        target: llm\n",
            encoding="utf-8",
        )
        summary = summarize_dsl(dsl_path)
        assert summary["name"] == "Sample App"
        assert summary["node_count"] == 2
        assert summary["edge_count"] == 1
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_workflow_scaffold_defaults_llm_model_to_deepseek_v4_flash() -> None:
    spec = default_spec_payload(
        name="Daily Report",
        mode="workflow",
        goal="Generate a daily report",
        inputs=["snapshot_json"],
        outputs=["final_report"],
        steps=["Generate report"],
    )
    dsl = scaffold_dsl_from_spec(spec)
    nodes = dsl["workflow"]["graph"]["nodes"]
    llm_node = next(node for node in nodes if node["data"]["type"] == "llm")
    data = llm_node["data"]

    assert data["model"]["provider"] == "langgenius/deepseek/deepseek"
    assert data["model"]["name"] == "deepseek-v4-flash"
    assert data["model"]["mode"] == "chat"
    assert data["model"]["completion_params"]["temperature"] == 0.1
    assert data["context"] == {"enabled": False, "variable_selector": []}
    assert data["vision"] == {"enabled": False}


def test_workflow_scaffold_produces_import_ready_top_level() -> None:
    spec = default_spec_payload(
        name="Sales Intake",
        mode="workflow",
        goal="Triage leads",
        inputs=["lead_text"],
        outputs=["final_reply"],
        steps=["Classify", "Reply"],
    )
    dsl = scaffold_dsl_from_spec(spec)
    assert dsl["kind"] == "app"
    assert dsl["version"] == "0.6.0"
    assert dsl["app"]["mode"] == "workflow"
    assert "features" in dsl["workflow"]
    nodes = dsl["workflow"]["graph"]["nodes"]
    edges = dsl["workflow"]["graph"]["edges"]
    # start + 2 steps + end = 4 nodes, 3 edges
    assert len(nodes) == 4
    assert len(edges) == 3
    assert nodes[0]["data"]["type"] == "start"
    assert nodes[-1]["data"]["type"] == "end"
    # node ids are unique quoted timestamp strings
    ids = [node["id"] for node in nodes]
    assert len(set(ids)) == len(ids)
    assert all(isinstance(i, str) and i.isdigit() for i in ids)


class _FakeLocator:
    def __init__(self, present: bool) -> None:
        self.present = present
        self.filled: list[str] = []
        self.clicked = 0
        self.first = self

    def count(self) -> int:
        return 1 if self.present else 0

    def fill(self, value: str) -> None:
        self.filled.append(value)

    def click(self) -> None:
        self.clicked += 1


class _FakePage:
    def __init__(self, mapping: dict[str, bool]) -> None:
        self.mapping = mapping
        self.locators: dict[str, _FakeLocator] = {}

    def locator(self, selector: str) -> _FakeLocator:
        if selector not in self.locators:
            self.locators[selector] = _FakeLocator(self.mapping.get(selector, False))
        return self.locators[selector]


def test_fill_first_uses_first_available_selector() -> None:
    page = _FakePage({"missing": False, "email": True})
    _fill_first(page, ["missing", "email"], "demo@example.com")
    assert page.locators["email"].filled == ["demo@example.com"]


def test_click_first_uses_first_available_selector() -> None:
    page = _FakePage({"missing": False, "submit": True})
    _click_first(page, ["missing", "submit"])
    assert page.locators["submit"].clicked == 1


def test_fill_first_raises_when_nothing_matches() -> None:
    page = _FakePage({})
    try:
        _fill_first(page, ["missing"], "value")
    except StudioAutomationError as exc:
        assert "matching input selectors" in str(exc)
    else:
        raise AssertionError("expected StudioAutomationError")


def test_app_id_from_url_extracts_uuid() -> None:
    assert _app_id_from_url("http://example.com/app/abc-123/workflow") == "abc-123"
    assert _app_id_from_url("http://example.com/apps") == ""


def test_mode_label_for_create_limits_supported_modes() -> None:
    assert _mode_label_for_create("workflow") == "工作流"
    assert _mode_label_for_create("chatflow") == "Chatflow"
    try:
        _mode_label_for_create("agent")
    except StudioAutomationError as exc:
        assert "workflow/chatflow only" in str(exc)
    else:
        raise AssertionError("expected StudioAutomationError")


# ── plugin（tool 插件授权配置管理）──

from difyctl.cli import _cmd_plugin, _mask_credentials
from difyctl.api_client import ApiResult


def test_mask_credentials_masks_secret_keys_and_known_prefixes() -> None:
    masked = _mask_credentials({
        "api_key": "g2a_abcdefghijklmnopqrstuvwxyz",
        "note": "plain text",
        "servers_config": "{\"s\":{\"headers\":{\"X-Grok-Api-Key\":\"g2a_abcdefghijklmnopqrstuvwxyz\"}}}",
        "nested": [{"password": "hunter2"}],
    })
    assert masked["api_key"] == "****"
    assert masked["note"] == "plain text"
    assert "g2a_abcdefghijklmnopqrstuvwxyz" not in masked["servers_config"]
    assert "g2a_****" in masked["servers_config"]
    assert masked["nested"][0]["password"] == "****"


def test_mask_credentials_leaves_non_secret_structures() -> None:
    src = {"url": "http://grok-search-rs:8080/mcp", "timeout": 120, "flags": [True, 3]}
    assert _mask_credentials(src) == src


class _FakePluginClient:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status
        self.calls = []

    def tool_providers_list(self, provider_type="builtin"):
        self.calls.append(("list", provider_type))
        return ApiResult(status_code=self._status, payload=self._payload, text="")

    def tool_builtin_tools(self, provider):
        self.calls.append(("tools", provider))
        return ApiResult(status_code=self._status, payload=self._payload, text="")

    def tool_builtin_credentials(self, provider):
        self.calls.append(("creds", provider))
        return ApiResult(status_code=self._status, payload=self._payload, text="")

    def tool_builtin_credential_add(self, provider, credentials, *, name="", credential_type="api-key"):
        self.calls.append(("add", provider, credentials, name, credential_type))
        return ApiResult(status_code=self._status, payload=self._payload, text="")

    def tool_builtin_credential_update(self, provider, credential_id, *, credentials=None, name=""):
        self.calls.append(("update", provider, credential_id, credentials, name))
        return ApiResult(status_code=self._status, payload=self._payload, text="")

    def tool_builtin_credential_delete(self, provider, credential_id):
        self.calls.append(("delete", provider, credential_id))
        return ApiResult(status_code=self._status, payload=self._payload, text="")


def _plugin_args(**kw):
    base = {
        "plugin_command": "list", "type": "builtin", "provider": "junjiem/mcp_sse/mcp_sse",
        "credentials": "", "credentials_file": "", "name": "", "credential_id": "",
        "dry_run": False, "console_key": "", "no_auto_refresh": True, "profile": None,
    }
    base.update(kw)
    return argparse.Namespace(**base)


def test_plugin_list_outputs_providers(monkeypatch, capsys) -> None:
    import argparse  # noqa
    client = _FakePluginClient([{"provider": "junjiem/mcp_sse/mcp_sse", "name": "mcp_sse", "is_team_authorization": True}])
    monkeypatch.setattr("difyctl.cli._console_client", lambda a, c: client)
    rc = _cmd_plugin(_plugin_args(), None)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["ok"] and out["count"] == 1
    assert out["providers"][0]["provider"] == "junjiem/mcp_sse/mcp_sse"


def test_plugin_auth_info_masks_credentials(monkeypatch, capsys) -> None:
    client = _FakePluginClient([{"id": "c1", "name": "API KEY 1", "credential_type": "api-key", "is_default": True,
                                 "credentials": {"servers_config": "{\"s\":{\"headers\":{\"X-Grok-Api-Key\":\"g2a_secretvalue123\"}}}"}}])  # noqa
    monkeypatch.setattr("difyctl.cli._console_client", lambda a, c: client)
    rc = _cmd_plugin(_plugin_args(plugin_command="auth-info"), None)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    rendered = json.dumps(out)
    assert "g2a_secretvalue123" not in rendered


def test_plugin_auth_set_add_calls_add(monkeypatch, capsys) -> None:
    monkeypatch.setenv("HARNESS_AI_KIT_ROLE", "contributor")
    client = _FakePluginClient({"result": "success"})
    monkeypatch.setattr("difyctl.cli._console_client", lambda a, c: client)
    creds = {"servers_config": "{\"groksearch\":{\"url\":\"http://x/mcp\"}}"}
    rc = _cmd_plugin(_plugin_args(plugin_command="auth-set", credentials=json.dumps(creds), name="n1"), None)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["ok"] and out["action"] == "add"
    assert client.calls[0][0] == "add" and client.calls[0][2] == creds and client.calls[0][3] == "n1"


def test_plugin_auth_set_with_credential_id_calls_update(monkeypatch, capsys) -> None:
    monkeypatch.setenv("HARNESS_AI_KIT_ROLE", "contributor")
    client = _FakePluginClient({"result": "success"})
    monkeypatch.setattr("difyctl.cli._console_client", lambda a, c: client)
    creds = {"servers_config": "{}"}
    rc = _cmd_plugin(_plugin_args(plugin_command="auth-set", credentials=json.dumps(creds), credential_id="cid-1"), None)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["action"] == "update"
    assert client.calls[0][0] == "update" and client.calls[0][2] == "cid-1"


def test_plugin_auth_set_dry_run_masks_and_skips_api(monkeypatch, capsys) -> None:
    client = _FakePluginClient({})
    monkeypatch.setattr("difyctl.cli._console_client", lambda a, c: client)
    creds = {"api_key": "g2a_secretvalue123"}
    rc = _cmd_plugin(_plugin_args(plugin_command="auth-set", credentials=json.dumps(creds), dry_run=True), None)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["_dry_run"] is True
    assert "g2a_secretvalue123" not in json.dumps(out)
    assert client.calls == []


def test_plugin_auth_remove_calls_delete(monkeypatch, capsys) -> None:
    monkeypatch.setenv("HARNESS_AI_KIT_ROLE", "maintainer")
    client = _FakePluginClient({"result": "success"})
    monkeypatch.setattr("difyctl.cli._console_client", lambda a, c: client)
    rc = _cmd_plugin(_plugin_args(plugin_command="auth-remove", credential_id="cid-9"), None)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["ok"]
    assert client.calls[0] == ("delete", "junjiem/mcp_sse/mcp_sse", "cid-9")
