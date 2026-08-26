from __future__ import annotations

from types import SimpleNamespace

import pytest

from woodpeckerctl import api
from woodpeckerctl import config
from woodpeckerctl import cli


def test_get_build_logs_uses_runtime_log_route(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[tuple[str, dict[str, str]]] = []

    monkeypatch.setattr(api, "resolve_repo_id", lambda *_args: 42)
    monkeypatch.setattr(api, "_api_base", lambda _args: "https://woodpecker.example/api")
    monkeypatch.setattr(api, "_headers", lambda _args: {"Accept": "application/json"})
    monkeypatch.setattr(
        api,
        "_get",
        lambda url, headers: requested.append((url, headers)) or [{"out": "build output"}],
    )

    result = api.get_build_logs(SimpleNamespace(), "team", "service", 17, 23)

    assert result == [{"out": "build output"}]
    assert requested == [
        (
            "https://woodpecker.example/api/repos/42/logs/17/23",
            {"Accept": "application/json"},
        )
    ]


class _HtmlResponse:
    def __enter__(self) -> "_HtmlResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return b"<!doctype html><html><body>Woodpecker</body></html>"


def test_get_rejects_spa_html_response(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(api.urllib.request, "urlopen", lambda *_args, **_kwargs: _HtmlResponse())

    with pytest.raises(SystemExit) as error:
        api._get("https://woodpecker.example/api/stale-route", {})

    assert error.value.code == 1
    assert "possible SPA fallback" in capsys.readouterr().err


def test_resolve_config_uses_unified_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "load_config",
        lambda overrides: {
            "woodpecker_url": overrides["woodpecker_url"],
            "woodpecker_token": "config-token",
        },
    )

    resolved = config.resolve_config(SimpleNamespace(server="https://wp.example/", token=None))

    assert resolved == {"server": "https://wp.example", "token": "config-token"}


def test_gitea_config_prefers_global_config_over_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    config_file = tmp_path / ".harness-ai-kit" / "config.yaml"
    config_file.parent.mkdir()
    config_file.write_text(
        "assets:\n  giteactl:\n    gitea_url: https://file.example\n    token: file-token\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("GITEA_URL", "https://env.example")
    monkeypatch.setenv("GITEA_TOKEN", "env-token")

    assert cli._gitea_config() == {
        "gitea_url": "https://file.example",
        "token": "file-token",
    }


def test_load_config_requires_unified_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "get_config", lambda _overrides=None: {"woodpecker_token": "token"})

    with pytest.raises(ValueError, match="assets.woodpeckerctl"):
        config.load_config()


def test_cli_reports_missing_config_without_traceback(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(config, "get_config", lambda _overrides=None: {})

    assert cli.main(["config", "show"]) == 2
    assert "配置错误" in capsys.readouterr().err
