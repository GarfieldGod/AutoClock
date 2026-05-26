import argparse
import select
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

if not getattr(sys, 'frozen', False) and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.log import Log
from src.utils.const import AppPath, Key
from src.extend.auto_linux_plan import create_crontab_task, delete_crontab_task
from src.runner.executor import run_task_by_id

def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Auto-Clock Runner")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show runner version (read from bundled config.json)",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a task by task_id")
    run_parser.add_argument("--task_id", required=True, help="Task ID")
    run_parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    cron_create_parser = subparsers.add_parser("cron_create", help="Create a Linux crontab entry for a task")
    cron_create_parser.add_argument("--task_json_path", required=True, help="Path to task json file on Linux")

    cron_delete_parser = subparsers.add_parser("cron_delete", help="Delete a Linux crontab entry by task name")
    cron_delete_parser.add_argument("--task_name", required=True, help="System plan name")

    set_current_parser = subparsers.add_parser("set_current", help="Set servers/current to a version directory")
    set_current_parser.add_argument("--version", required=True, help="Version string")
    set_current_parser.add_argument(
        "--servers_root",
        default=str(Path(AppPath.AppRoot) / "servers"),
        help="Servers root directory (default: ~/.local/share/auto-clock/servers)",
    )

    driver_install_parser = subparsers.add_parser("driver_install", help="Install Edge WebDriver using webdriver_manager")
    driver_install_parser.add_argument(
        "--driver_root",
        default=str(Path(AppPath.AppRoot) / "driver"),
        help="Driver root directory (default: ~/.local/share/auto-clock/driver)",
    )

    auth_parser = subparsers.add_parser("auth", help="Daily report authorization (check or interactive)")
    auth_parser.add_argument("--driver_path", required=True, help="Path to msedgedriver")
    auth_parser.add_argument("--show_web_page", action="store_true", help="Show browser window")
    auth_parser.add_argument("--interactive", action="store_true", help="Interactive mode with stdin/stdout JSON protocol")

    auth_status_parser = subparsers.add_parser("auth_status", help="Check daily report authorization state without triggering login flow")
    auth_status_parser.add_argument("--driver_path", required=True, help="Path to msedgedriver")

    # Backward compatible flags: auto-clock-runner --task_id=xxx [--headless]
    legacy_parser = argparse.ArgumentParser(add_help=False)
    legacy_parser.add_argument("--task_id")
    legacy_parser.add_argument("--headless", action="store_true")
    legacy_args, _ = legacy_parser.parse_known_args(argv)
    if legacy_args.task_id:
        normalized = ["run", "--task_id", legacy_args.task_id]
        if legacy_args.headless:
            normalized.append("--headless")
        args = parser.parse_args(normalized)
    else:
        args = parser.parse_args(argv)
        if args.command is None and getattr(args, "version", False):
            try:
                from src.utils.utils import Utils

                v = Utils.get_app_version_from_config_json(default="unknown")
            except Exception:
                v = "unknown"
            print(v)
            return 0
        if args.command is None:
            parser.print_help()
            return 1

    try:
        if args.command == "run":
            ok, error = run_task_by_id(task_id=args.task_id, headless=args.headless)
            if ok:
                return 0
            return 2

        if args.command == "driver_install":
            driver_root = str(Path(args.driver_root).expanduser().resolve())
            Path(driver_root).mkdir(parents=True, exist_ok=True)
            exact_version_error = None

            def _edge_version() -> str | None:
                for cmd in [
                    "microsoft-edge --version",
                    "microsoft-edge-stable --version",
                    "msedge --version",
                    "microsoft-edge-beta --version",
                    "microsoft-edge-dev --version",
                ]:
                    try:
                        res = subprocess.run(cmd.split(), capture_output=True, text=True)
                        out = (res.stdout or res.stderr or "").strip()
                        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
                        if m:
                            return m.group(1)
                    except Exception:
                        continue
                return None

            def _latest_release() -> str:
                url = "https://msedgedriver.microsoft.com/LATEST_RELEASE"
                with urllib.request.urlopen(url, timeout=20) as resp:
                    return resp.read().decode("utf-8").strip()

            def _download_driver(version: str) -> str:
                zip_url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_linux64.zip"
                target_dir = Path(driver_root) / ".wdm" / "drivers" / "edgedriver" / "linux64" / version
                target_dir.mkdir(parents=True, exist_ok=True)
                driver_path = target_dir / "msedgedriver"
                if driver_path.exists():
                    return str(driver_path)

                with tempfile.TemporaryDirectory() as td:
                    tmp_zip = Path(td) / "edgedriver_linux64.zip"
                    urllib.request.urlretrieve(zip_url, tmp_zip)
                    with zipfile.ZipFile(tmp_zip, "r") as z:
                        z.extractall(target_dir)

                try:
                    st = os.stat(driver_path)
                    os.chmod(driver_path, st.st_mode | 0o111)
                except Exception:
                    pass

                if not driver_path.exists():
                    raise FileNotFoundError(f"Driver not found after extract: {driver_path}")
                return str(driver_path)

            def _driver_version(driver_path: str) -> str | None:
                try:
                    res = subprocess.run([driver_path, "--version"], capture_output=True, text=True)
                    out = (res.stdout or res.stderr or "").strip()
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
                    if m:
                        return m.group(1)
                except Exception:
                    pass
                return None

            def _ensure_exact_driver(driver_path: str, expected_version: str) -> str:
                actual_version = _driver_version(driver_path)
                if actual_version != expected_version:
                    raise RuntimeError(
                        f"Downloaded driver version mismatch: expected={expected_version}, actual={actual_version}, path={driver_path}"
                    )
                return driver_path

            exact_version = _edge_version()
            # Prefer webdriver_manager exact-version resolution first
            try:
                from src.utils.utils import Utils

                old_driver_root = AppPath.DriversRoot
                try:
                    AppPath.DriversRoot = driver_root
                    if exact_version:
                        ok, result = Utils.download_edge_web_driver(version=exact_version)
                        if ok:
                            exact_driver = _ensure_exact_driver(str(result), exact_version)
                            print(exact_driver)
                            return 0
                        exact_version_error = str(result or "")

                    ok, result = Utils.download_edge_web_driver()
                finally:
                    AppPath.DriversRoot = old_driver_root

                if ok:
                    print(result)
                    return 0
            except Exception as e:
                if exact_version and not exact_version_error:
                    exact_version_error = str(e)

            if exact_version:
                try:
                    exact_driver = _ensure_exact_driver(_download_driver(exact_version), exact_version)
                    print(exact_driver)
                    return 0
                except Exception as e:
                    if not exact_version_error:
                        exact_version_error = str(e)

            version = exact_version or _latest_release()
            try:
                driver_path = _download_driver(version)
                print(str(driver_path))
                return 0
            except Exception as e:
                suffix = f"; exact_version={exact_version}; exact_error={exact_version_error}" if exact_version else ""
                raise RuntimeError(f"driver_install failed: {e}{suffix}")

        if args.command in {"auth", "auth_status"}:
            from src.core.daily_report.auth_common import (
                clean_profile_locks, clean_profile_cache, clean_profile_session,
                find_element_any, fast_find_element_any,
                AUTH_QR_SELECTORS, AUTH_PHONE_SWITCH_SELECTORS, AUTH_QR_SWITCH_SELECTORS,
                AUTH_PHONE_INPUT_SELECTORS, AUTH_PHONE_NEXT_BUTTON,
                AUTH_CODE_INPUT_SELECTORS,
                AUTH_SEND_CODE_SELECTORS, AUTH_SUBMIT_SELECTORS, AUTH_AGREE_BUTTON,
                send_msg, recv_msg,
                MSG_QR_READY, MSG_NEED_PHONE, MSG_NEED_CODE,
                MSG_AUTH_SUCCESS, MSG_AUTH_ERROR,
                MSG_LOG, MSG_PHONE, MSG_CODE, MSG_SWITCH_PHONE, MSG_SWITCH_QR, MSG_CANCEL,
                MSG_SEND_CODE_TRIGGERED,
                wait_auth_page_ready, get_auth_page_state, is_authorized,
                reset_to_qr_page, click_element,
                find_send_code_element, wait_authorized_or_select_account, wait_for_send_code_ready_state,
            )
            from src.core.daily_report.daily_report import DailyReport, DailyReportConfig, DAILY_REPORT_URL
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.common import TimeoutException
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC

            driver_path = args.driver_path
            show_web_page = getattr(args, "show_web_page", False)
            interactive = getattr(args, "interactive", False)

            def _check_authorized(driver, navigate=True):
                if navigate:
                    driver.get(DAILY_REPORT_URL)
                wait_auth_page_ready(driver, timeout=10)
                return is_authorized(driver)

            def _emit_log(message):
                Log.info(message)
                if interactive:
                    try:
                        send_msg({"type": MSG_LOG, "data": message})
                    except Exception:
                        pass

            def _recv_msg_non_blocking(timeout_sec=1.0):
                try:
                    ready, _, _ = select.select([sys.stdin], [], [], timeout_sec)
                except Exception:
                    time.sleep(timeout_sec)
                    return None
                if not ready:
                    return None
                return recv_msg()

            def _click_element(driver, element, label):
                ok = click_element(driver, element)
                if ok:
                    Log.info(f"interactive_auth: clicked {label}")
                else:
                    Log.warn(f"interactive_auth: failed to click {label}")
                return ok

            def _page_state(driver):
                try:
                    return {
                        "url": driver.current_url or "",
                        "title": driver.title or "",
                    }
                except Exception:
                    return {"url": "", "title": ""}

            def _go_back_to_qr(driver):
                _emit_log("interactive_auth: clearing storage and reloading for qr login")
                qr_element = reset_to_qr_page(driver, DAILY_REPORT_URL, qr_timeout=15)
                if qr_element is not None:
                    _emit_log("interactive_auth: qr visible again after reset")
                    return True
                state = _page_state(driver)
                _emit_log(f"interactive_auth: qr not found after reset, url={state['url']} title={state['title']}")
                return False

            def _interactive_auth(driver):
                import base64
                profile_dir = os.path.join(AppPath.DataRoot, "daily_report_profile")
                try:
                    # Warm-up: navigate to about:blank first to reduce first-navigation overhead
                    try:
                        t0 = time.time()
                        driver.get("about:blank")
                        _emit_log(f"interactive_auth: warm-up blank page done in {time.time()-t0:.2f}s")
                    except Exception:
                        pass

                    t0 = time.time()
                    try:
                        driver.get(DAILY_REPORT_URL)
                    except Exception:
                        pass
                    _emit_log(f"interactive_auth: navigate to daily report done in {time.time()-t0:.2f}s")

                    t0 = time.time()
                    wait_auth_page_ready(driver, timeout=10)
                    _emit_log(f"interactive_auth: wait_auth_page_ready done in {time.time()-t0:.2f}s")

                    state = _page_state(driver)
                    _emit_log(f"interactive_auth: initial state url={state['url']} title={state['title']}")

                    if _check_authorized(driver, navigate=False):
                        _emit_log("interactive_auth: already authorized, reset to QR for re-authorization")
                        if _go_back_to_qr(driver):
                            state = _page_state(driver)
                            _emit_log(f"interactive_auth: reset to QR done, continue interactive auth, url={state['url']} title={state['title']}")
                        else:
                            _emit_log("interactive_auth: reset to QR failed, keep current authorized state")
                            send_msg({"type": MSG_AUTH_SUCCESS})
                            return True

                    # Only look for authorize button if page is still on daily host
                    current_state = get_auth_page_state(driver, element_timeout=0)
                    if current_state == "daily":
                        try:
                            auth_btn = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'授权') or contains(text(),'Authorize') or contains(text(),'Authorization')]"))
                            )
                            auth_btn.click()
                            time.sleep(1)
                            state = _page_state(driver)
                            _emit_log(f"interactive_auth: clicked authorize button, url={state['url']} title={state['title']}")
                        except Exception:
                            pass
                    elif current_state in {"phone", "login"}:
                        try:
                            qr_switch = find_element_any(driver, AUTH_QR_SWITCH_SELECTORS, timeout=2)
                            if qr_switch is not None:
                                _click_element(driver, qr_switch, "switch-to-qr")
                                time.sleep(1)
                                _emit_log("interactive_auth: switched to QR mode from phone/login state")
                            else:
                                _emit_log(f"interactive_auth: qr switch not found, keep current state={current_state}")
                        except Exception:
                            pass
                    else:
                        _emit_log(f"interactive_auth: skip authorize button lookup, current_state={current_state}")

                    t0 = time.time()
                    try:
                        WebDriverWait(driver, 20).until(
                            lambda d: (
                                get_auth_page_state(d, element_timeout=0) in {"authorized", "qr", "qr_scanned", "phone", "login", "authen"}
                            )
                        )
                    except TimeoutException:
                        pass
                    _emit_log(f"interactive_auth: wait for auth page state done in {time.time()-t0:.2f}s")

                    state = _page_state(driver)
                    _emit_log(f"interactive_auth: waiting result url={state['url']} title={state['title']}")

                    switched_to_phone = False
                    qr_el = fast_find_element_any(driver, AUTH_QR_SELECTORS)
                    if qr_el is None:
                        qr_el = find_element_any(driver, AUTH_QR_SELECTORS, timeout=2)
                    if qr_el:
                        png_data = qr_el.screenshot_as_png
                        send_msg({"type": MSG_QR_READY, "data": base64.b64encode(png_data).decode()})
                        _emit_log("interactive_auth: qr_ready sent to UI, entering scan wait loop")
                        while True:
                            try:
                                state_now = get_auth_page_state(driver, element_timeout=0)
                                if state_now == "qr_scanned":
                                    _emit_log("interactive_auth: qr page shows scan success")
                                if state_now == "authorized" or is_authorized(driver):
                                    state = _page_state(driver)
                                    _emit_log(f"interactive_auth: confirmed authorized while waiting QR loop, url={state['url']}")
                                    send_msg({"type": MSG_AUTH_SUCCESS})
                                    return True
                            except Exception:
                                pass
                            msg = _recv_msg_non_blocking(1.0)
                            if msg is None:
                                continue
                            t = msg.get("type", "")
                            if t == MSG_SWITCH_PHONE:
                                _emit_log("interactive_auth: received switch_phone while waiting for QR scan")
                                switched_to_phone = True
                                break
                            if t == MSG_CANCEL:
                                _emit_log("interactive_auth: received cancel while waiting for QR scan")
                                return False
                            _emit_log(f"interactive_auth: ignored message while waiting for QR scan: {t}")

                    if switched_to_phone:
                        state = _page_state(driver)
                        _emit_log(f"interactive_auth: switch_phone confirmed, entering phone login directly, url={state['url']} title={state['title']}")
                        return _phone_login(driver)

                    if _check_authorized(driver, navigate=False):
                        state = _page_state(driver)
                        _emit_log(f"interactive_auth: authorized without QR prompt, url={state['url']}")
                        send_msg({"type": MSG_AUTH_SUCCESS})
                        return True

                    # Check if phone input is visible (wait for page transition)
                    phone_input = find_element_any(driver, AUTH_PHONE_INPUT_SELECTORS, timeout=8)
                    if phone_input is not None:
                        state = _page_state(driver)
                        _emit_log(f"interactive_auth: phone input found, falling back to phone login, url={state['url']} title={state['title']}")
                        return _phone_login(driver)

                    # Fallback: URL-based detection for login pages
                    if "login" in (driver.current_url or "").lower():
                        state = _page_state(driver)
                        _emit_log(f"interactive_auth: login url detected, falling back to phone login, url={state['url']} title={state['title']}")
                        return _phone_login(driver)

                    if _check_authorized(driver, navigate=True):
                        state = _page_state(driver)
                        _emit_log(f"interactive_auth: authorized after final navigate check, url={state['url']}")
                        send_msg({"type": MSG_AUTH_SUCCESS})
                        return True

                    state = _page_state(driver)
                    send_msg({"type": MSG_AUTH_ERROR, "data": f"未检测到二维码，当前页面 url={state['url']} title={state['title']}"})
                    return False
                except Exception as e:
                    send_msg({"type": MSG_AUTH_ERROR, "data": str(e)})
                    return False

            def _phone_login(driver):
                state = _page_state(driver)
                _emit_log(f"interactive_auth: entering phone login, url={state['url']} title={state['title']}")
                phone_input = fast_find_element_any(driver, AUTH_PHONE_INPUT_SELECTORS)
                if phone_input is None:
                    switch_el = find_element_any(driver, AUTH_PHONE_SWITCH_SELECTORS)
                    if switch_el:
                        try:
                            _click_element(driver, switch_el, "phone-switch")
                            time.sleep(2)
                        except Exception:
                            pass

                phone_input = find_element_any(driver, AUTH_PHONE_INPUT_SELECTORS, timeout=8)
                if phone_input is None:
                    state = _page_state(driver)
                    _emit_log(f"interactive_auth: phone input not found after switch, url={state['url']} title={state['title']}")

                send_msg({"type": MSG_NEED_PHONE})
                msg = recv_msg()
                if msg is None or msg.get("type") == MSG_CANCEL:
                    return False
                if msg.get("type") == MSG_SWITCH_QR:
                    _go_back_to_qr(driver)
                    return _interactive_auth(driver)
                phone = (msg.get("data") or "").strip() if msg.get("type") == MSG_PHONE else ""
                if phone:
                    phone_input = find_element_any(driver, AUTH_PHONE_INPUT_SELECTORS, timeout=8)
                    if phone_input:
                        phone_input.clear()
                        phone_input.send_keys(phone)
                        _emit_log(f"interactive_auth: phone number filled, len={len(phone)}")
                        time.sleep(1)
                        next_btn = find_element_any(driver, AUTH_PHONE_NEXT_BUTTON, timeout=5)
                        if next_btn:
                            _click_element(driver, next_btn, "phone-next")
                            _emit_log("interactive_auth: clicked next button")
                            time.sleep(1)
                        agree_btn = find_element_any(driver, AUTH_AGREE_BUTTON, timeout=3)
                        if agree_btn:
                            _click_element(driver, agree_btn, "agree")
                            _emit_log("interactive_auth: clicked agree button")
                            time.sleep(2)
                        send_code_state = wait_for_send_code_ready_state(driver, timeout=10)
                        send_code_btn = send_code_state.get("element")
                        if send_code_state.get("state") == "button" and send_code_btn:
                            try:
                                btn_text = str(send_code_btn.text or "").strip()
                                btn_disabled = bool(send_code_btn.get_attribute("disabled")) or str(send_code_btn.get_attribute("aria-disabled") or "").lower() == "true"
                            except Exception:
                                btn_text = ""
                                btn_disabled = False
                            _emit_log(f"interactive_auth: send code button found, text={btn_text!r}, disabled={btn_disabled}")
                            if not btn_disabled:
                                clicked_btn = _click_element(driver, send_code_btn, "send-code")
                                if clicked_btn:
                                    _emit_log("interactive_auth: clicked send code button")
                                    confirmed = False
                                    retry_state = wait_for_send_code_ready_state(driver, timeout=4)
                                    if retry_state.get("state") == "countdown":
                                        _emit_log(f"interactive_auth: send code confirmed by countdown={retry_state.get('text', '')!r}")
                                        confirmed = True
                                    else:
                                        try:
                                            driver.execute_script("""
                                                const el = arguments[0];
                                                if (!el) return false;
                                                const events = ['mouseover', 'mousedown', 'mouseup', 'click'];
                                                for (const type of events) {
                                                    el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
                                                }
                                                return true;
                                            """, send_code_btn)
                                            _emit_log("interactive_auth: send code not confirmed, retried with DOM mouse events")
                                        except Exception:
                                            pass
                                        retry_state = wait_for_send_code_ready_state(driver, timeout=4)
                                        if retry_state.get("state") == "countdown":
                                            _emit_log(f"interactive_auth: send code confirmed after retry, countdown={retry_state.get('text', '')!r}")
                                            confirmed = True
                                    if confirmed and interactive:
                                        send_msg({"type": MSG_SEND_CODE_TRIGGERED})
                                    if not confirmed:
                                        _emit_log("interactive_auth: send code click not confirmed by countdown; SMS may not be sent")
                                else:
                                    _emit_log("interactive_auth: send code button click failed")
                        elif send_code_state.get("state") == "countdown":
                            _emit_log(f"interactive_auth: send code already triggered, countdown={send_code_state.get('text', '')!r}")
                            if interactive:
                                send_msg({"type": MSG_SEND_CODE_TRIGGERED})
                        elif send_code_state.get("state") == "code_input":
                            _emit_log("interactive_auth: code input visible without explicit send code button, proceeding")
                            # Feishu phone flow can auto-send SMS once code input is shown.
                            # Keep consistent with local flow: no forced click when explicit send button is absent.
                            if interactive:
                                send_msg({"type": MSG_SEND_CODE_TRIGGERED})
                            try:
                                retry_state = wait_for_send_code_ready_state(driver, timeout=8)
                                if retry_state.get("state") == "countdown":
                                    _emit_log(f"interactive_auth: auto send confirmed by countdown={retry_state.get('text', '')!r}")
                                elif retry_state.get("state") == "button":
                                    _emit_log("interactive_auth: send code button appeared later after code_input")
                                else:
                                    _emit_log("interactive_auth: no countdown/button after code_input; continue waiting for user code")
                            except Exception:
                                pass
                        else:
                            _emit_log("interactive_auth: neither code input, countdown nor send code button found yet")
                        state = _page_state(driver)
                        _emit_log(f"interactive_auth: waiting for code input, url={state['url']} title={state['title']}")
                    else:
                        _emit_log("interactive_auth: phone input missing when trying to fill phone")

                send_msg({"type": MSG_NEED_CODE})
                msg = recv_msg()
                if msg is None or msg.get("type") == MSG_CANCEL:
                    return False
                if msg.get("type") == MSG_SWITCH_QR:
                    _go_back_to_qr(driver)
                    return _interactive_auth(driver)
                code = (msg.get("data") or "").strip() if msg.get("type") == MSG_CODE else ""
                if code:
                    code_input = find_element_any(driver, AUTH_CODE_INPUT_SELECTORS, timeout=5)
                    if code_input:
                        code_input.send_keys(code)
                        _emit_log(f"interactive_auth: code entered, len={len(code)}")
                        time.sleep(5)
                    else:
                        submit_btn = find_element_any(driver, AUTH_SUBMIT_SELECTORS, timeout=3)
                        if submit_btn:
                            _click_element(driver, submit_btn, "submit-login")
                            time.sleep(5)

                ok, selected_account = wait_authorized_or_select_account(driver, timeout=30, tenant_name="东软集团")
                if ok:
                    state = _page_state(driver)
                    if selected_account:
                        _emit_log(f"interactive_auth: selected tenant account 东软集团 and authorized, url={state['url']} title={state['title']}")
                    else:
                        _emit_log(f"interactive_auth: phone login authorized, url={state['url']} title={state['title']}")
                else:
                    state = _page_state(driver)
                    _emit_log(f"interactive_auth: phone login not authorized, url={state['url']} title={state['title']}")
                return ok

            profile_dir = os.path.join(AppPath.DataRoot, "daily_report_profile")
            clean_profile_locks(profile_dir)
            clean_profile_cache(profile_dir)
            clean_profile_session(profile_dir)

            if not driver_path or not os.path.exists(driver_path):
                Log.error(f"Driver not found: {driver_path}")
                if interactive:
                    send_msg({"type": MSG_AUTH_ERROR, "data": f"Driver not found: {driver_path}"})
                return 1

            config = DailyReportConfig(
                driver_path=driver_path,
                show_web_page=show_web_page,
                work_desc="", normal_hours="", overtime_hours="",
                project_name="", project_task="",
                activity_type="", project_module="",
            )
            report = None
            try:
                report = DailyReport(config)
                if args.command == "auth_status":
                    return 0 if _check_authorized(report.driver) else 2

                if interactive:
                    return 0 if _interactive_auth(report.driver) else 2

                ok, error = report._navigate_and_authorize()
                if ok:
                    if interactive:
                        send_msg({"type": MSG_AUTH_SUCCESS})
                    return 0

                Log.error(error or "Auth check failed")
                return 2
            except Exception as e:
                Log.error(f"Auth error: {e}")
                if interactive:
                    send_msg({"type": MSG_AUTH_ERROR, "data": str(e)})
                return 1
            finally:
                if report:
                    try:
                        report.quit()
                    except Exception:
                        pass
                try:
                    clean_profile_cache(profile_dir)
                except Exception:
                    pass

        if args.command == "cron_create":
            task_path = Path(args.task_json_path)
            if not task_path.exists():
                Log.error(f"Task json not found: {task_path}")
                return 1
            task = json.loads(task_path.read_text(encoding="utf-8"))
            ok, error = create_crontab_task(task)
            if ok:
                return 0
            Log.error(error or "Create crontab task failed")
            return 2

        if args.command == "cron_delete":
            ok, error = delete_crontab_task(args.task_name)
            if ok:
                return 0
            Log.error(error or "Delete crontab task failed")
            return 2

        if args.command == "set_current":
            servers_root = Path(args.servers_root).expanduser().resolve()
            target_dir = (servers_root / args.version).resolve()
            link_path = servers_root / "current"
            servers_root.mkdir(parents=True, exist_ok=True)
            if not target_dir.exists():
                Log.error(f"Version directory not found: {target_dir}")
                return 1
            # Use ln -sfn to update atomically
            result = subprocess.run(["ln", "-sfn", str(target_dir), str(link_path)], capture_output=True, text=True)
            if result.returncode != 0:
                Log.error(result.stderr.strip() or f"ln failed with code {result.returncode}")
                return 2
            return 0

        Log.error(f"Unknown command: {args.command}")
        return 1
    except Exception as e:
        Log.error(str(e))
        try:
            sys.stderr.write(f"{e}\n")
            sys.stderr.flush()
        except Exception:
            pass
        return 1
    finally:
        Log.close()


if __name__ == "__main__":
    raise SystemExit(main())
