import argparse
import json
import os
import re
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

            exact_version = _edge_version()
            if exact_version:
                try:
                    exact_driver = _download_driver(exact_version)
                    print(exact_driver)
                    return 0
                except Exception:
                    pass

            # Fallback to project existing logic when exact-version install is unavailable
            try:
                from src.utils.utils import Utils

                old_driver_root = AppPath.DriversRoot
                try:
                    AppPath.DriversRoot = driver_root
                    ok, result = Utils.download_edge_web_driver()
                finally:
                    AppPath.DriversRoot = old_driver_root

                if ok:
                    print(result)
                    return 0
            except Exception:
                pass

            version = exact_version or _latest_release()
            driver_path = _download_driver(version)
            print(str(driver_path))
            return 0

        if args.command == "auth":
            from src.core.daily_report.auth_common import (
                clean_profile_locks, clean_profile_cache, clean_profile_session,
                find_element_any,
                AUTH_QR_SELECTORS, AUTH_PHONE_SWITCH_SELECTORS, AUTH_QR_SWITCH_SELECTORS,
                AUTH_PHONE_INPUT_SELECTORS, AUTH_PHONE_NEXT_BUTTON,
                AUTH_CODE_INPUT_SELECTORS,
                AUTH_SEND_CODE_SELECTORS, AUTH_SUBMIT_SELECTORS, AUTH_AGREE_BUTTON,
                send_msg, recv_msg,
                MSG_QR_READY, MSG_NEED_PHONE, MSG_NEED_CODE,
                MSG_AUTH_SUCCESS, MSG_AUTH_ERROR,
                MSG_PHONE, MSG_CODE, MSG_SWITCH_PHONE, MSG_SWITCH_QR, MSG_CANCEL,
            )
            from src.core.daily_report.daily_report import DailyReport, DailyReportConfig, DAILY_REPORT_URL
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.common import TimeoutException

            driver_path = args.driver_path
            show_web_page = args.show_web_page
            interactive = args.interactive

            def _interactive_auth(driver):
                import base64
                profile_dir = os.path.join(AppPath.DataRoot, "daily_report_profile")
                try:
                    qr_el = find_element_any(driver, AUTH_QR_SELECTORS, timeout=3)
                    if qr_el:
                        png_data = qr_el.screenshot_as_png
                        send_msg({"type": MSG_QR_READY, "data": base64.b64encode(png_data).decode()})
                        while True:
                            try:
                                if "daily" in (driver.current_url or ""):
                                    send_msg({"type": MSG_AUTH_SUCCESS})
                                    return True
                            except Exception:
                                pass
                            msg = recv_msg()
                            if msg is None:
                                return False
                            t = msg.get("type", "")
                            if t == MSG_SWITCH_PHONE:
                                break
                            if t == MSG_CANCEL:
                                return False
                            time.sleep(1)

                    if "login" in (driver.current_url or "").lower():
                        return _phone_login(driver)
                    # No QR and no login page, try phone login as fallback
                    return _phone_login(driver)
                except Exception as e:
                    send_msg({"type": MSG_AUTH_ERROR, "data": str(e)})
                    return False

            def _phone_login(driver):
                switch_el = find_element_any(driver, AUTH_PHONE_SWITCH_SELECTORS)
                if switch_el:
                    try:
                        switch_el.click()
                        time.sleep(2)
                    except Exception:
                        pass

                send_msg({"type": MSG_NEED_PHONE})
                msg = recv_msg()
                if msg is None or msg.get("type") == MSG_CANCEL:
                    return False
                if msg.get("type") == MSG_SWITCH_QR:
                    qr_switch = find_element_any(driver, AUTH_QR_SWITCH_SELECTORS)
                    if qr_switch:
                        try:
                            qr_switch.click()
                            time.sleep(2)
                        except Exception:
                            pass
                    return _interactive_auth(driver)
                phone = (msg.get("data") or "").strip() if msg.get("type") == MSG_PHONE else ""
                if phone:
                    phone_input = find_element_any(driver, AUTH_PHONE_INPUT_SELECTORS, timeout=5)
                    if phone_input:
                        phone_input.clear()
                        phone_input.send_keys(phone)
                        time.sleep(1)
                        send_btn = find_element_any(driver, AUTH_PHONE_NEXT_BUTTON, timeout=5)
                        if send_btn:
                            send_btn.click()
                            time.sleep(1)
                        agree_btn = find_element_any(driver, AUTH_AGREE_BUTTON, timeout=3)
                        if agree_btn:
                            agree_btn.click()
                            time.sleep(2)

                send_msg({"type": MSG_NEED_CODE})
                msg = recv_msg()
                if msg is None or msg.get("type") == MSG_CANCEL:
                    return False
                if msg.get("type") == MSG_SWITCH_QR:
                    qr_switch = find_element_any(driver, AUTH_QR_SWITCH_SELECTORS)
                    if qr_switch:
                        try:
                            qr_switch.click()
                            time.sleep(2)
                        except Exception:
                            pass
                    return _interactive_auth(driver)
                code = (msg.get("data") or "").strip() if msg.get("type") == MSG_CODE else ""
                if code:
                    code_input = find_element_any(driver, AUTH_CODE_INPUT_SELECTORS, timeout=5)
                    if code_input:
                        code_input.send_keys(code)
                        time.sleep(5)
                    else:
                        submit_btn = find_element_any(driver, AUTH_SUBMIT_SELECTORS, timeout=3)
                        if submit_btn:
                            submit_btn.click()
                            time.sleep(3)

                try:
                    WebDriverWait(driver, 30).until(lambda d: "daily" in (d.current_url or ""))
                    send_msg({"type": MSG_AUTH_SUCCESS})
                    return True
                except TimeoutException:
                    send_msg({"type": MSG_AUTH_ERROR, "data": "登录超时，请重试"})
                    return False

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
                ok, error = report._navigate_and_authorize()
                if ok:
                    if interactive:
                        send_msg({"type": MSG_AUTH_SUCCESS})
                    return 0

                if interactive:
                    _interactive_auth(report.driver)
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
