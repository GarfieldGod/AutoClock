import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from src.utils.const import AppPath
from src.utils.log import Log


DAILY_REPORT_URL = "https://fsyy1.neusoft.com/daily?m=dailyList&app_id=cli_a222a3254261900b"

SELECTORS = {
    "authorize_button": (By.XPATH, "//button[contains(@class, 'ud__button--filled-primary')]"),
    "add_button": (By.XPATH, "//*[contains(text(), '新增')]"),
    "save_button": (By.XPATH, "//*[contains(text(), '保存')]"),
    "success_dialog": (By.XPATH, "//*[contains(., '操作成功')]"),
    "success_ok_button": (By.XPATH, "//*[contains(., 'OK') or contains(., '确定')]"),
    "date_field": (By.ID, "date"),
    "work_desc": (By.ID, "task"),
    "normal_hours": (By.ID, "normalTime"),
    "overtime_hours": (By.ID, "overTime"),
    "project_name_trigger": (By.ID, "proList"),
    "project_task_trigger": (By.ID, "proTask"),
    "activity_type_trigger": (By.ID, "activityType"),
    "project_module_trigger": (By.ID, "projectModule"),
    "popup_visible": (By.XPATH, "//div[contains(@class, 'popup') or contains(@class, 'dialog') or contains(@class, 'modal') or contains(@class, 'select-dropdown') or contains(@class, 'ant-select-dropdown') or contains(@class, 'el-select-dropdown')]"),
    "popup_option_template": "//*[contains(text(), '{text}')]",
}


@dataclass
class DailyReportConfig:
    driver_path: str
    show_web_page: bool
    work_desc: str
    normal_hours: str
    overtime_hours: str
    project_name: str
    project_task: str
    activity_type: str
    project_module: str


class DailyReport:
    def __init__(self, config: DailyReportConfig):
        self.config = config
        self.driver = None
        try:
            self.driver = self.create_driver()
        except Exception as e:
            detail = self._build_driver_failure_detail(e)
            Log.error(f"DailyReport: create driver error: {detail}")
            raise RuntimeError(detail)

    def create_driver(self):
        profile_dir = self._get_profile_dir()
        try:
            driver = self._start_edge_driver(profile_dir, safe_mode=False)
            Log.info("DailyReport: create driver successfully")
            return driver
        except Exception as first_error:
            if platform.system() != "Linux":
                raise

            Log.warn(f"DailyReport: first create driver attempt failed, retry with reset profile: {first_error}")
            self._reset_profile_dir(profile_dir)
            driver = self._start_edge_driver(profile_dir, safe_mode=True)
            Log.info("DailyReport: create driver successfully after safe retry")
            return driver

    def _can_show_web_page(self):
        if not self.config.show_web_page:
            return False
        if platform.system() != "Linux":
            return True
        display = str(os.environ.get("DISPLAY", "")).strip()
        wayland = str(os.environ.get("WAYLAND_DISPLAY", "")).strip()
        return bool(display or wayland)

    def _build_edge_options(self, profile_dir, safe_mode=False):
        opts = Options()
        opts.page_load_strategy = 'eager'
        effective_show_web_page = self._can_show_web_page()
        has_display = True
        if platform.system() == "Linux":
            display = str(os.environ.get("DISPLAY", "")).strip()
            wayland = str(os.environ.get("WAYLAND_DISPLAY", "")).strip()
            has_display = bool(display or wayland)

        if self.config.show_web_page and not effective_show_web_page:
            Log.warn("DailyReport: show_web_page requested but no DISPLAY/WAYLAND_DISPLAY found, fallback to headless")

        hidden_window_mode = (not self.config.show_web_page and has_display)
        if not self.config.show_web_page and hidden_window_mode:
            Log.info("DailyReport: show_web_page=false but display exists, use hidden window mode (non-headless)")

        if not effective_show_web_page and not hidden_window_mode:
            opts.add_argument("--headless=new")

        if platform.system() == "Linux":
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--enable-logging")
            opts.add_argument("--v=1")
            opts.add_argument("--password-store=basic")
            opts.add_argument("--use-mock-keychain")
            if not safe_mode:
                opts.add_argument("--disable-software-rasterizer")
                opts.add_argument("--disable-extensions")

        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        if effective_show_web_page:
            opts.add_argument("--start-maximized")
        elif hidden_window_mode:
            opts.add_argument("--start-minimized")
            opts.add_argument("--window-position=-32000,-32000")

        opts.add_argument(f"--user-data-dir={profile_dir}")

        edge_binary = self._find_edge_binary()
        if edge_binary:
            opts.binary_location = edge_binary
        return opts

    def _start_edge_driver(self, profile_dir, safe_mode=False):
        opts = self._build_edge_options(profile_dir, safe_mode=safe_mode)
        service = Service(
            executable_path=self.config.driver_path,
            service_args=["--verbose"],
            log_output=self._get_driver_log_path(),
        )
        return webdriver.Edge(service=service, options=opts)

    def _reset_profile_dir(self, profile_dir):
        try:
            if os.path.exists(profile_dir):
                shutil.rmtree(profile_dir, ignore_errors=True)
            os.makedirs(profile_dir, exist_ok=True)
        except Exception as e:
            Log.warn(f"DailyReport: reset profile dir failed: {e}")

    def _get_profile_dir(self):
        profile_dir = os.path.join(AppPath.DataRoot, "daily_report_profile")
        os.makedirs(profile_dir, exist_ok=True)
        return profile_dir

    def _get_driver_log_path(self):
        log_dir = os.path.join(AppPath.DataRoot, "logs")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "daily_report_chromedriver.log")

    def _find_edge_binary(self):
        candidates = [
            "microsoft-edge",
            "microsoft-edge-stable",
            "msedge",
            "microsoft-edge-beta",
            "microsoft-edge-dev",
        ]
        for name in candidates:
            path = shutil.which(name)
            if path:
                return path
        return None

    def _run_cmd_text(self, args):
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=8)
            return (result.stdout or result.stderr or "").strip()
        except Exception:
            return ""

    def _tail_file(self, file_path, max_lines=3):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            return " | ".join(lines[-max_lines:])
        except Exception:
            return ""

    def _build_driver_failure_detail(self, error):
        parts = [str(error).strip()]
        parts.append(f"profile_dir={self._get_profile_dir()}")
        parts.append(f"show_web_page={self.config.show_web_page}")
        parts.append(f"effective_show_web_page={self._can_show_web_page()}")
        parts.append(f"DISPLAY={os.environ.get('DISPLAY', '')}")
        parts.append(f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')}")

        edge_binary = self._find_edge_binary()
        parts.append(f"edge_binary={edge_binary or 'not_found'}")

        edge_version = self._run_cmd_text([edge_binary, "--version"]) if edge_binary else ""
        if edge_version:
            parts.append(f"edge_version={edge_version}")

        driver_version = self._run_cmd_text([self.config.driver_path, "--version"])
        if driver_version:
            parts.append(f"driver_version={driver_version}")

        log_tail = self._tail_file(self._get_driver_log_path())
        if log_tail:
            parts.append(f"chromedriver_log={log_tail}")

        return " | ".join([p for p in parts if p])

    def run(self):
        try:
            ok, error = self._navigate_and_authorize()
            if not ok:
                return False, error
            ok, error = self._fill_and_submit()
            if not ok:
                return False, error
            return True, None
        except Exception as e:
            Log.error(f"Daily report run failed: {e}")
            return False, str(e)
        finally:
            time.sleep(3)
            self.quit()

    def _navigate_and_authorize(self):
        try:
            Log.info(f"Navigating to {DAILY_REPORT_URL}")
            self.driver.get(DAILY_REPORT_URL)
            time.sleep(3)

            # Wait for page to settle: either redirect to auth/login, or stay on daily page
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: ("authen" in (d.current_url or "").lower() or
                               "login" in (d.current_url or "").lower())
                )
                Log.info("Detected redirect to auth/login page")
            except TimeoutException:
                if "daily" in (self.driver.current_url or ""):
                    Log.info("Stayed on daily report page (no redirect) - authorized")
                    return True, None
                Log.warn(f"Timeout waiting for page state, URL: {self.driver.current_url}")

            auth_clicked = False
            time.sleep(3)
            try:
                wait = WebDriverWait(self.driver, 25)
                auth_btn = wait.until(
                    EC.element_to_be_clickable(SELECTORS["authorize_button"])
                )
                Log.info("Found authorize button, clicking...")
                auth_btn.click()
                auth_clicked = True
                Log.info("Waiting for redirect to daily report page...")
                try:
                    WebDriverWait(self.driver, 30).until(
                        lambda d: "daily" in (d.current_url or "")
                    )
                    Log.info("Authorization successful, on daily report page")
                    return True, None
                except TimeoutException:
                    Log.warn("Still not on daily report page after 30s")
                    time.sleep(5)
                    if "daily" in (self.driver.current_url or ""):
                        return True, None
            except TimeoutException:
                pass

            current = self.driver.current_url or ""
            if "login" in current.lower():
                return False, "Login page detected. Please run manual authorization first."
            if auth_clicked:
                if "authen" in current.lower():
                    Log.warn("Still on auth page after clicking authorize")
                    return False, "Authorization button clicked but redirect did not complete."
                if "daily" in current.lower():
                    return True, None
            if "authen" in current.lower() or "auth" in current.lower():
                return False, "Authorization page detected. Please click the 'Authorization' button first."

            Log.warn(f"Unknown page state: {current}, proceeding anyway")
            return True, None

        except Exception as e:
            return False, f"Navigation failed: {e}"

    def _fill_and_submit(self):
        try:
            wait = WebDriverWait(self.driver, 15)

            Log.info("Clicking '新增'...")
            add_btn = wait.until(EC.element_to_be_clickable(SELECTORS["add_button"]))
            add_btn.click()
            time.sleep(3)

            # Project Name must be filled first (triggers sub_proList() → populates proTask)
            self._select_option(SELECTORS["project_name_trigger"], self.config.project_name, "project_name")
            time.sleep(2)

            self._check_date()

            self._fill_text(SELECTORS["work_desc"], self.config.work_desc)
            self._fill_text(SELECTORS["normal_hours"], self.config.normal_hours)
            self._fill_text(SELECTORS["overtime_hours"], self.config.overtime_hours)

            self._select_option(SELECTORS["project_task_trigger"], self.config.project_task, "project_task")
            self._select_option(SELECTORS["activity_type_trigger"], self.config.activity_type, "activity_type")
            self._select_option(SELECTORS["project_module_trigger"], self.config.project_module, "project_module")

            Log.info("Clicking '保存'...")
            save_btn = wait.until(EC.element_to_be_clickable(SELECTORS["save_button"]))
            save_btn.click()
            time.sleep(3)

            try:
                wait.until(EC.presence_of_element_located(SELECTORS["success_dialog"]))
                Log.info("Success dialog appeared")
                ok_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(SELECTORS["success_ok_button"])
                )
                ok_btn.click()
                Log.info("Clicked OK on success dialog")
                time.sleep(2)
            except TimeoutException:
                Log.warn("Success dialog not detected, proceeding anyway")

            return True, None

        except Exception as e:
            return False, f"Fill/submit failed: {e}"

    def _check_date(self):
        try:
            el = self.driver.find_element(*SELECTORS["date_field"])
            val = el.get_attribute("value") or ""
            today = date.today().isoformat()
            if val == today:
                Log.info(f"Date is today: {today}")
            else:
                Log.info(f"Date {val} != today {today}, adjusting...")
                el.clear()
                el.send_keys(today)
                time.sleep(1)
        except (NoSuchElementException, TimeoutException):
            Log.warn("Date field not found, assuming today's date is default")

    def _fill_text(self, selector, value):
        if not value:
            return
        try:
            el = self.driver.find_element(*selector)
            el.clear()
            el.send_keys(value)
            Log.info(f"Filled: {value[:60]}...")
        except (NoSuchElementException, TimeoutException):
            Log.warn(f"Text field not found: {selector}")

    def _select_option(self, trigger_selector, target_text, field_name):
        if not target_text:
            return
        try:
            el = WebDriverWait(self.driver, 10).until(
                lambda d: d.find_element(*trigger_selector)
            )
            tag = el.tag_name.lower()

            # 原生 <select> 元素：直接用 Select，绕过覆盖层点击拦截
            if tag == "select":
                Select(el).select_by_visible_text(target_text)
                Log.info(f"Selected '{target_text}' for {field_name}")
                return

            # 非 select 元素：点击触发弹窗后选择
            trigger = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(trigger_selector)
            )
            Log.info(f"Clicking selection: {field_name}")
            trigger.click()
            time.sleep(2)

            try:
                Select(trigger).select_by_visible_text(target_text)
                Log.info(f"Selected '{target_text}' via Select")
                return
            except Exception:
                pass

            try:
                popup = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(SELECTORS["popup_visible"])
                )
                option_xpath = SELECTORS["popup_option_template"].replace("{text}", target_text)
                option = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, option_xpath))
                )
                option.click()
                Log.info(f"Selected '{target_text}'")
                time.sleep(1)
                return
            except TimeoutException:
                pass

            Log.warn(f"Could not select '{target_text}' for {field_name}")
            try:
                trigger.click()
            except Exception:
                pass

        except Exception as e:
            Log.warn(f"Selection failed for {field_name}: {e}")

    def quit(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
