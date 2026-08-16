from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


class StudioAutomationError(RuntimeError):
    pass


@dataclass(frozen=True)
class BrowserDoctorResult:
    playwright_available: bool
    username_env: str
    password_env: str
    username_present: bool
    password_present: bool
    base_url: str


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise StudioAutomationError(
            "Playwright is not available. Install it with `pip install playwright` and run `playwright install chromium`."
        ) from exc
    return sync_playwright


def _known_browser_candidates() -> list[tuple[str, str]]:
    # On Linux servers/containers, Edge/Chrome channels are rarely installed;
    # prefer Playwright's bundled chromium first. On Windows/macOS keep the
    # system-channel-first order (msedge/chrome usually present).
    if sys.platform.startswith("linux"):
        return [
            ("default", "chromium"),
            ("channel", "chrome"),
            ("channel", "msedge"),
        ]
    return [
        ("channel", "msedge"),
        ("channel", "chrome"),
        ("default", "chromium"),
    ]


def _browser_launch_args() -> list[str]:
    # Bundled chromium fails to launch as root or inside many containers
    # without --no-sandbox; --disable-dev-shm-usage avoids /dev/shm exhaustion.
    if sys.platform.startswith("linux"):
        return ["--no-sandbox", "--disable-dev-shm-usage"]
    return []


def _launch_browser(playwright, *, headless: bool):
    last_error: Exception | None = None
    launch_args = _browser_launch_args()
    for launch_type, value in _known_browser_candidates():
        try:
            if launch_type == "channel":
                return playwright.chromium.launch(channel=value, headless=headless, args=launch_args)
            return playwright.chromium.launch(headless=headless, args=launch_args)
        except Exception as exc:  # pragma: no cover
            last_error = exc
            continue
    raise StudioAutomationError(f"Unable to launch a browser via Playwright: {last_error}")


def browser_doctor(*, base_url: str, username_env: str, password_env: str) -> BrowserDoctorResult:
    try:
        _load_playwright()
        available = True
    except StudioAutomationError:
        available = False
    return BrowserDoctorResult(
        playwright_available=available,
        username_env=username_env,
        password_env=password_env,
        username_present=bool(os.environ.get(username_env, "").strip()),
        password_present=bool(os.environ.get(password_env, "").strip()),
        base_url=base_url,
    )


def _require_secret(env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise StudioAutomationError(f"Missing required credential environment variable: {env_name}")
    return value


def _fill_first(page, selectors: list[str], value: str) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                locator.first.fill(value)
                return
        except Exception:
            continue
    raise StudioAutomationError(f"Unable to find any matching input selectors: {selectors}")


def _click_first(page, selectors: list[str]) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                locator.first.click()
                return
        except Exception:
            continue
    raise StudioAutomationError(f"Unable to find any matching clickable selectors: {selectors}")


def _maybe_login(page, *, base_url: str, username: str, password: str) -> None:
    signin_url = base_url.rstrip("/") + "/signin"
    page.goto(signin_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    username_selectors = [
        'input[placeholder="输入邮箱地址"]',
        'input[aria-label="邮箱"]',
        'input[type="email"]',
        'input[name="email"]',
        'input[placeholder*="mail" i]',
        'input[type="text"]',
    ]
    password_selectors = [
        'input[placeholder="输入密码"]',
        'input[aria-label*="密码"]',
        'input[type="password"]',
        'input[name="password"]',
        'input[placeholder*="password" i]',
    ]
    submit_selectors = [
        'button:has-text("登录")',
        'button[type="submit"]',
        'button:has-text("Sign in")',
        'button:has-text("Login")',
    ]

    login_form_visible = False
    for selector in username_selectors:
        try:
            if page.locator(selector).count() > 0:
                login_form_visible = True
                break
        except Exception:
            continue

    if not login_form_visible and "/signin" not in page.url:
        return

    _fill_first(page, username_selectors, username)
    _fill_first(page, password_selectors, password)
    _click_first(page, submit_selectors)
    page.wait_for_load_state("networkidle")
    page.wait_for_url("**/apps", wait_until="domcontentloaded")


def _open_import_modal(page) -> None:
    import_selectors = [
        'button:has-text("导入 DSL 文件")',
        'button:has-text("导入 DSL")',
        'button:has-text("Import DSL")',
        'button:has-text("Import")',
        'button:has-text("导入")',
    ]
    _click_first(page, import_selectors)
    dialog_selectors = [
        '[role="dialog"]:has-text("导入 DSL")',
        'div[role="dialog"]',
        'text="导入 DSL"',
    ]
    for selector in dialog_selectors:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=10_000)
            return
        except Exception:
            continue
    raise StudioAutomationError("Import DSL dialog did not appear")


def _upload_dsl_file(page, dsl_path: Path) -> None:
    upload_input_selectors = [
        '[role="dialog"] input[type="file"]',
        'input[type="file"]',
    ]
    for selector in upload_input_selectors:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                locator.first.set_input_files(str(dsl_path))
                return
        except Exception:
            continue

    trigger_selectors = [
        '[role="dialog"] text="拖拽文件至此，或者选择文件"',
        '[role="dialog"] text="选择文件"',
    ]
    for selector in trigger_selectors:
        try:
            with page.expect_file_chooser() as file_chooser_info:
                page.locator(selector).first.click()
            file_chooser_info.value.set_files(str(dsl_path))
            return
        except Exception:
            continue
    raise StudioAutomationError("Unable to locate a file input or chooser trigger in the Import DSL dialog")


def _submit_import(page) -> str:
    create_selectors = [
        '#headlessui-portal-root button:has-text("创建")',
        'button:has-text("创建")',
    ]
    for selector in create_selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
            if count == 0:
                continue
            page.wait_for_timeout(1_000)
            for index in range(count - 1, -1, -1):
                candidate = locator.nth(index)
                if not candidate.is_visible() or not candidate.is_enabled():
                    continue
                candidate.click()
                try:
                    page.wait_for_url("**/app/**", timeout=20_000, wait_until="domcontentloaded")
                except Exception:
                    page.wait_for_load_state("networkidle")
                return page.url
        except Exception:
            continue
    raise StudioAutomationError("Import DSL create button did not become enabled after upload")


def _app_id_from_url(url: str) -> str:
    match = re.search(r"/app/([^/]+)/", url)
    return match.group(1) if match else ""


def _open_apps_page(page, *, base_url: str, username: str, password: str) -> None:
    _maybe_login(page, base_url=base_url, username=username, password=password)
    page.goto(base_url.rstrip("/") + "/apps", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")


def _mode_label_for_create(mode: str) -> str:
    normalized = mode.strip().lower()
    mapping = {
        "workflow": "工作流",
        "chatflow": "Chatflow",
    }
    if normalized not in mapping:
        raise StudioAutomationError(
            f"Studio create-empty-run currently supports workflow/chatflow only, got: {mode}"
        )
    return mapping[normalized]


def create_empty_app(
    *,
    base_url: str,
    name: str,
    mode: str,
    description: str,
    username_env: str,
    password_env: str,
    headless: bool,
) -> dict[str, object]:
    username = _require_secret(username_env)
    password = _require_secret(password_env)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:  # pragma: no cover
        browser = _launch_browser(playwright, headless=headless)
        page = browser.new_page()
        _open_apps_page(page, base_url=base_url, username=username, password=password)

        page.locator('button:has-text("创建空白应用")').first.click()
        page.locator('#headlessui-portal-root input[placeholder="给你的应用起个名字"]').first.wait_for(
            state="visible",
            timeout=10_000,
        )
        page.locator('#headlessui-portal-root').get_by_text(_mode_label_for_create(mode)).first.click()
        page.locator('#headlessui-portal-root input[placeholder="给你的应用起个名字"]').first.fill(name)
        if description.strip():
            page.locator('#headlessui-portal-root textarea[placeholder="输入应用的描述"]').first.fill(description.strip())

        create_button = page.locator('#headlessui-portal-root button:has-text("创建")').first
        create_button.wait_for(state="visible", timeout=10_000)
        if not create_button.is_enabled():
            raise StudioAutomationError("Create button did not become enabled in the create-empty modal")
        create_button.click()
        try:
            page.wait_for_url("**/app/**", timeout=20_000, wait_until="domcontentloaded")
        except Exception:
            page.wait_for_load_state("networkidle")
        final_url = page.url
        app_id = _app_id_from_url(final_url)
        browser.close()

    return {
        "status": "created" if app_id else "submitted",
        "operation": "create-empty-run",
        "base_url": base_url,
        "name": name,
        "mode": mode,
        "description": description,
        "app_id": app_id,
        "final_url": final_url,
        "username_env": username_env,
    }


def _menu_button_for_app(page, app_name: str):
    escaped_name = app_name.replace('"', '\\"')
    title = page.locator(f'xpath=(//*[normalize-space(text())="{escaped_name}"])[1]')
    if title.count() == 0:
        raise StudioAutomationError(f'Unable to find app card for "{app_name}" on the Studio list')
    title.hover(force=True)
    page.wait_for_timeout(700)
    menu_button = page.locator(
        f'xpath=(//*[normalize-space(text())="{escaped_name}"])[1]/ancestor::div[contains(@class,"group relative")][1]//button[contains(., "更多")]'
    ).first
    if not menu_button.is_visible():
        raise StudioAutomationError(f'More menu button is not visible for app "{app_name}"')
    return menu_button


def export_dsl_from_apps(
    *,
    base_url: str,
    app_name: str,
    output_path: Path,
    username_env: str,
    password_env: str,
    headless: bool,
) -> dict[str, object]:
    username = _require_secret(username_env)
    password = _require_secret(password_env)
    sync_playwright = _load_playwright()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:  # pragma: no cover
        browser = _launch_browser(playwright, headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        _open_apps_page(page, base_url=base_url, username=username, password=password)

        menu_button = _menu_button_for_app(page, app_name)
        menu_button.click(force=True)
        with page.expect_download() as download_info:
            page.locator('text="导出 DSL"').first.click(force=True)
        download = download_info.value
        suggested_name = download.suggested_filename or f"{app_name}.yml"
        final_target = output_path
        if final_target.is_dir():
            final_target = final_target / suggested_name
        download.save_as(str(final_target))
        final_url = page.url
        context.close()
        browser.close()

    return {
        "status": "exported",
        "operation": "export-dsl-run",
        "base_url": base_url,
        "app_name": app_name,
        "output_path": str(final_target),
        "download_name": suggested_name,
        "final_url": final_url,
        "username_env": username_env,
    }


def duplicate_app_from_apps(
    *,
    base_url: str,
    source_app_name: str,
    new_name: str,
    username_env: str,
    password_env: str,
    headless: bool,
) -> dict[str, object]:
    username = _require_secret(username_env)
    password = _require_secret(password_env)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:  # pragma: no cover
        browser = _launch_browser(playwright, headless=headless)
        page = browser.new_page()
        _open_apps_page(page, base_url=base_url, username=username, password=password)

        menu_button = _menu_button_for_app(page, source_app_name)
        menu_button.click(force=True)
        page.locator('text="复制"').first.click(force=True)
        duplicate_name_input = page.locator('#headlessui-portal-root input').first
        duplicate_name_input.wait_for(state="visible", timeout=10_000)
        duplicate_name_input.fill(new_name)
        page.locator('#headlessui-portal-root button:has-text("复制")').first.click(force=True)
        try:
            page.wait_for_url("**/app/**", timeout=20_000, wait_until="domcontentloaded")
        except Exception:
            page.wait_for_load_state("networkidle")
        final_url = page.url
        app_id = _app_id_from_url(final_url)
        browser.close()

    return {
        "status": "created" if app_id else "submitted",
        "operation": "duplicate-run",
        "base_url": base_url,
        "source_app_name": source_app_name,
        "name": new_name,
        "app_id": app_id,
        "final_url": final_url,
        "username_env": username_env,
    }


def edit_app_info_from_apps(
    *,
    base_url: str,
    app_name: str,
    new_name: str,
    description: str | None,
    max_active_requests: int | None,
    username_env: str,
    password_env: str,
    headless: bool,
) -> dict[str, object]:
    username = _require_secret(username_env)
    password = _require_secret(password_env)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:  # pragma: no cover
        browser = _launch_browser(playwright, headless=headless)
        page = browser.new_page()
        _open_apps_page(page, base_url=base_url, username=username, password=password)

        menu_button = _menu_button_for_app(page, app_name)
        menu_button.click(force=True)
        page.locator('text="编辑信息"').first.click(force=True)
        name_input = page.locator('#headlessui-portal-root input[placeholder="给你的应用起个名字"]').first
        name_input.wait_for(state="visible", timeout=10_000)
        name_input.fill(new_name)
        if description is not None:
            page.locator('#headlessui-portal-root textarea[placeholder="输入应用的描述"]').first.fill(description)
        if max_active_requests is not None:
            page.locator('#headlessui-portal-root input[placeholder="0 表示不限制"]').first.fill(str(max_active_requests))
        page.locator('#headlessui-portal-root button:has-text("保存")').first.click(force=True)
        page.wait_for_timeout(2_000)
        final_url = page.url
        browser.close()

    return {
        "status": "updated",
        "operation": "edit-info-run",
        "base_url": base_url,
        "source_app_name": app_name,
        "name": new_name,
        "description": description,
        "max_active_requests": max_active_requests,
        "final_url": final_url,
        "username_env": username_env,
    }


def login_and_import_dsl(
    *,
    base_url: str,
    dsl_path: Path,
    username_env: str,
    password_env: str,
    headless: bool,
) -> dict[str, object]:
    if not dsl_path.exists():
        raise StudioAutomationError(f"DSL file not found: {dsl_path}")

    username = _require_secret(username_env)
    password = _require_secret(password_env)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:  # pragma: no cover
        browser = _launch_browser(playwright, headless=headless)
        page = browser.new_page()

        studio_url = base_url.rstrip("/") + "/apps"
        _maybe_login(page, base_url=base_url, username=username, password=password)
        page.goto(studio_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        _open_import_modal(page)
        _upload_dsl_file(page, dsl_path)
        final_url = _submit_import(page)
        browser.close()

    return {
        "status": "created" if "/app/" in final_url else "submitted",
        "operation": "import-dsl-run",
        "base_url": base_url,
        "dsl_path": str(dsl_path),
        "username_env": username_env,
        "final_url": final_url,
    }


# ── Session cookie capture for Community Edition Console API ──


def capture_console_cookie(
    *,
    base_url: str,
    username_env: str = "DIFY_STUDIO_USERNAME",
    password_env: str = "DIFY_STUDIO_PASSWORD",
    headless: bool = True,
) -> dict[str, object]:
    """Log into Dify via Playwright and capture the session cookie.

    Dify Community Edition uses session-based auth for its Console API.
    This function logs in and extracts the session cookie for use with
    ConsoleApiClient(auth=ConsoleAuth(type="cookie", value="session=...")).

    Returns a dict with the cookie value and metadata.
    """
    username = _require_secret(username_env)
    password = _require_secret(password_env)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:  # pragma: no cover
        browser = _launch_browser(playwright, headless=headless)
        context = browser.new_context()
        page = context.new_page()

        _maybe_login(page, base_url=base_url, username=username, password=password)

        # Navigate to settings to ensure we have full access
        settings_url = base_url.rstrip("/") + "/settings/provider"
        page.goto(settings_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        # Extract all cookies
        cookies = context.cookies()
        browser.close()

    # Build cookie header value from relevant cookies
    cookie_parts: list[str] = []
    for cookie in cookies:
        if cookie.get("name") and cookie.get("value"):
            cookie_parts.append(f"{cookie['name']}={cookie['value']}")

    cookie_header = "; ".join(cookie_parts) if cookie_parts else ""

    # Also extract the session cookie specifically (Dify uses 'session' or 'dify_session')
    session_cookie = ""
    for cookie in cookies:
        name = cookie.get("name", "").lower()
        if "session" in name or "dify" in name:
            session_cookie = f"{cookie['name']}={cookie['value']}"
            break
    if not session_cookie and cookie_parts:
        session_cookie = cookie_parts[0]

    return {
        "status": "ok",
        "operation": "capture-console-cookie",
        "base_url": base_url,
        "session_cookie": session_cookie,
        "full_cookie_header": cookie_header,
        "cookie_count": len(cookies),
        "username_env": username_env,
        "usage": f'Set env: DIFY_CONSOLE_KEY="{session_cookie}" and use: difyctl --console-key "$env:DIFY_CONSOLE_KEY" provider add --from provider.yaml',
    }


# ── Provider browser fallback ──

PROVIDER_ADD_SELECTORS = {
    "settings_nav": [
        'a[href*="/settings"]',
        'text="设置"',
        'text="Settings"',
    ],
    "provider_tab": [
        'text="模型供应商"',
        'text="Model Providers"',
        'div:has-text("模型供应商")',
    ],
    "add_provider_btn": [
        'button:has-text("添加供应商")',
        'button:has-text("Add Provider")',
    ],
    "provider_type_option": lambda t: [
        f'text="{t}"',
        f'div:has-text("{t}")',
    ],
    "name_input": [
        'input[placeholder*="名称" i]',
        'input[placeholder*="name" i]',
        'input[name="name"]',
    ],
    "api_base_input": [
        'input[placeholder*="API Base" i]',
        'input[placeholder*="api_base" i]',
        'input[name="api_base"]',
    ],
    "api_key_input": [
        'input[placeholder*="API Key" i]',
        'input[placeholder*="api_key" i]',
        'input[name="api_key"]',
        'input[type="password"]',
    ],
    "save_btn": [
        'button:has-text("保存")',
        'button:has-text("Save")',
        'button[type="submit"]',
    ],
}


def provider_add_browser(
    *,
    base_url: str,
    provider_type: str,
    provider_name: str,
    api_base: str,
    api_key: str,
    username_env: str,
    password_env: str,
    headless: bool = True,
) -> dict[str, object]:
    """Use Playwright to add a model provider through Dify Studio UI.

    This is the browser fallback when the Console API is unavailable.
    """
    username = _require_secret(username_env)
    password = _require_secret(password_env)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:  # pragma: no cover
        browser = _launch_browser(playwright, headless=headless)
        page = browser.new_page()
        _maybe_login(page, base_url=base_url, username=username, password=password)

        # Navigate to settings → model providers
        settings_url = base_url.rstrip("/") + "/settings/provider"
        page.goto(settings_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        # Click "Add Provider"
        _click_first(page, PROVIDER_ADD_SELECTORS["add_provider_btn"])
        page.wait_for_timeout(1_000)

        # Select provider type (look for text matching the type)
        type_selectors = PROVIDER_ADD_SELECTORS["provider_type_option"](provider_type)
        _click_first(page, type_selectors)

        # Fill form
        _fill_first(page, PROVIDER_ADD_SELECTORS["name_input"], provider_name)
        _fill_first(page, PROVIDER_ADD_SELECTORS["api_base_input"], api_base)
        _fill_first(page, PROVIDER_ADD_SELECTORS["api_key_input"], api_key)

        # Save
        _click_first(page, PROVIDER_ADD_SELECTORS["save_btn"])
        page.wait_for_timeout(3_000)
        page.wait_for_load_state("networkidle")

        final_url = page.url
        browser.close()

    return {
        "status": "submitted",
        "operation": "provider-add-browser-fallback",
        "base_url": base_url,
        "provider_type": provider_type,
        "provider_name": provider_name,
        "final_url": final_url,
        "username_env": username_env,
    }


def with_fallback(
    api_call,
    *,
    browser_call=None,
    no_fallback: bool = False,
) -> dict[str, object]:
    """Execute an API call, falling back to browser on eligible errors.

    Returns a dict with at least {"status": ..., "method": "api"|"browser"|"error"}.
    """
    from difyctl.console_api import ApiResult, should_fallback

    try:
        result: ApiResult = api_call()
        if 200 <= result.status_code < 300:
            return {"status": "ok", "method": "api", "result": result}
        if not no_fallback and browser_call and should_fallback(result.status_code):
            return {"status": "ok", "method": "browser", "result": browser_call()}
        return {
            "status": "error",
            "method": "api",
            "status_code": result.status_code,
            "payload": result.payload,
        }
    except Exception as exc:
        if not no_fallback and browser_call:
            try:
                return {"status": "ok", "method": "browser", "result": browser_call()}
            except Exception as browser_exc:
                return {"status": "error", "method": "none", "error": f"api: {exc}, browser: {browser_exc}"}
        return {"status": "error", "method": "none", "error": str(exc)}
