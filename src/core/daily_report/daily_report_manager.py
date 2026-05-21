import os
import time
import threading
from urllib.parse import urlparse
import subprocess

from PyQt5.QtCore import QThread, pyqtSignal

from src.utils.log import Log
from src.utils.const import Key, AppPath
from src.utils.utils import Utils
from src.core.daily_report.daily_report import DailyReport, DailyReportConfig, DAILY_REPORT_URL
from src.core.daily_report.auth_common import (
    find_element_any, clean_profile_locks, clean_profile_cache, clean_profile_session,
    AUTH_QR_SELECTORS, AUTH_PHONE_SWITCH_SELECTORS, AUTH_QR_SWITCH_SELECTORS,
    AUTH_PHONE_INPUT_SELECTORS, AUTH_PHONE_NEXT_BUTTON,
    AUTH_CODE_INPUT_SELECTORS,
    AUTH_SEND_CODE_SELECTORS, AUTH_SUBMIT_SELECTORS, AUTH_AGREE_BUTTON,
    MSG_QR_READY, MSG_NEED_PHONE, MSG_NEED_CODE,
    MSG_AUTH_SUCCESS, MSG_AUTH_ERROR,
    MSG_PHONE, MSG_CODE, MSG_SWITCH_PHONE, MSG_SWITCH_QR, MSG_CANCEL,
)
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
from src.extend.ssh_client import SshConfig, SshClient


class DailyReportManager:
    def __init__(self, show_web_page_override=None):
        try:
            if not os.path.exists(AppPath.DataJson):
                self.status = False
                self.error = f"{AppPath.DataJson} does not exist."
                return

            data = Utils.read_dict_from_json(AppPath.DataJson)

            self.driver_path = data.get(Key.DriverPath, "")
            self.show_web_page = data.get(Key.ShowWebPage, False)
            if show_web_page_override is not None:
                self.show_web_page = bool(show_web_page_override)

            self.work_desc = data.get(Key.DailyWorkDesc, "")
            self.normal_hours = data.get(Key.DailyNormalHours, "")
            self.overtime_hours = data.get(Key.DailyOvertimeHours, "")
            self.project_name = data.get(Key.DailyProjectName, "")
            self.project_task = data.get(Key.DailyTaskName, "")
            self.activity_type = data.get(Key.DailyActivityType, "")
            self.project_module = data.get(Key.DailyProjectModule, "")

            if not self.driver_path or not os.path.exists(self.driver_path):
                self.status = False
                self.error = "Driver path is invalid or missing."
                return

            self.status = True
        except Exception as e:
            Log.error(f"DailyReportManager init error: {e}")
            self.status = False
            self.error = str(e)

    def run(self):
        if not self.status:
            return self.status, self.error

        config = DailyReportConfig(
            driver_path=self.driver_path,
            show_web_page=self.show_web_page,
            work_desc=self.work_desc,
            normal_hours=self.normal_hours,
            overtime_hours=self.overtime_hours,
            project_name=self.project_name,
            project_task=self.project_task,
            activity_type=self.activity_type,
            project_module=self.project_module,
        )

        try:
            report = DailyReport(config)
            return report.run()
        except Exception as e:
            return False, str(e)


def run_daily_report(show_web_page_override=None):
    try:
        manager = DailyReportManager(show_web_page_override=show_web_page_override)
        if not manager.status:
            return False, manager.error
        return manager.run()
    except Exception as e:
        return False, str(e)


def run_manual_login(driver_path):
    try:
        profile_dir = os.path.join(AppPath.DataRoot, "daily_report_profile")
        os.makedirs(profile_dir, exist_ok=True)

        opts = Options()
        opts.page_load_strategy = 'eager'
        opts.add_argument("--window-size=1280,900")
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        opts.add_argument(f"--user-data-dir={profile_dir}")

        service = Service(executable_path=driver_path)
        driver = webdriver.Edge(service=service, options=opts)
        Log.info("Manual login: browser opened, navigating to daily report URL...")
        driver.get(DAILY_REPORT_URL)

        while True:
            try:
                _ = driver.current_url
                time.sleep(1)
            except Exception:
                break

        Log.info("Manual login: browser closed")
        return True, None
    except Exception as e:
        Log.error(f"Manual login failed: {e}")
        return False, str(e)


def fast_find_any(driver, selectors):
    """Synchronous element lookup — ~10ms per selector, no polling wait."""
    for by, sel in selectors:
        try:
            el = driver.find_element(by, sel)
            if el.is_displayed():
                return el
        except Exception:
            continue
    return None


class AuthStatusCheckWorker(QThread):
    status_ready = pyqtSignal(bool)
    status_error = pyqtSignal(str)

    def __init__(self, is_remote, driver_path, show_web_page=False, ssh_cfg=None):
        super().__init__()
        self._is_remote = bool(is_remote)
        self._driver_path = (driver_path or "").strip()
        self._show_web_page = bool(show_web_page)
        self._ssh_cfg = ssh_cfg

    def run(self):
        try:
            if self._is_remote:
                ok = self._check_remote_authorized()
            else:
                ok = self._check_local_authorized()
            self.status_ready.emit(ok)
        except Exception as e:
            self.status_error.emit(str(e))
            self.status_ready.emit(False)

    def _check_local_authorized(self):
        if not self._driver_path or not os.path.exists(self._driver_path):
            return False

        config = DailyReportConfig(
            driver_path=self._driver_path,
            show_web_page=self._show_web_page,
            work_desc="",
            normal_hours="",
            overtime_hours="",
            project_name="",
            project_task="",
            activity_type="",
            project_module="",
        )

        report = None
        try:
            report = DailyReport(config)
            driver = report.driver
            driver.get(DAILY_REPORT_URL)

            try:
                WebDriverWait(driver, 8).until(
                    lambda d: (
                        "daily" in (d.current_url or "").lower()
                        or "authen" in (d.current_url or "").lower()
                        or "login" in (d.current_url or "").lower()
                    )
                )
            except TimeoutException:
                pass

            current = (driver.current_url or "").lower()
            if "login" in current or "authen" in current or "auth" in current:
                return False
            if "daily" in current:
                form_el = fast_find_any(driver, [
                    (By.ID, "task"),
                    (By.ID, "proList"),
                ])
                return form_el is not None
            return False
        finally:
            if report:
                try:
                    report.quit()
                except Exception:
                    pass

    def _check_remote_authorized(self):
        if not self._ssh_cfg or not self._driver_path:
            return False

        runner_path = f"{AppPath.RemoteAppRoot}/servers/current/auto-clock-runner"
        cmd = f"{runner_path} auth --driver_path={self._driver_path}"
        with SshClient(self._ssh_cfg) as ssh:
            code, _, _ = ssh.exec(cmd, timeout_sec=180)
            return code == 0


class AuthWorker(QThread):
    qr_ready = pyqtSignal(bytes)
    need_phone = pyqtSignal()
    need_code = pyqtSignal()
    auth_success = pyqtSignal()
    auth_error = pyqtSignal(str)

    def __init__(self, driver_path, show_web_page=False):
        super().__init__()
        self.driver_path = driver_path
        self._show_web_page = show_web_page
        self._phone = None
        self._code = None
        self._use_phone = False
        self._switch_to_qr = False
        self._cancel = False
        self._restart = False
        self._lock = threading.RLock()

    def set_phone(self, phone):
        with self._lock:
            self._phone = phone

    def set_code(self, code):
        with self._lock:
            self._code = code

    def switch_to_phone(self):
        with self._lock:
            self._use_phone = True

    def switch_to_qr(self):
        with self._lock:
            self._switch_to_qr = True
            self._use_phone = False

    def cancel(self):
        self._cancel = True

    def _click_switch(self, driver):
        """Reliably click the QR/phone toggle button using real mouse click via ActionChains.
        Uses JS to find the visible .switch-login-mode-box (there may be two in DOM, one hidden)."""
        for _ in range(3):
            try:
                el = driver.execute_script("""
                    var boxes = document.querySelectorAll('div.switch-login-mode-box');
                    for (var i = 0; i < boxes.length; i++) {
                        if (boxes[i].offsetParent !== null) return boxes[i];
                    }
                    return null;
                """)
                if el:
                    ActionChains(driver).move_to_element(el).click().perform()
                    time.sleep(2)
                    Log.info("AuthWorker: clicked switch button via ActionChains")
                    return True
            except Exception:
                pass
            time.sleep(1)
        Log.warn("AuthWorker: switch button not found after 3 attempts")
        return False

    def _is_daily_url(self, url):
        try:
            parsed = urlparse(url)
            return "daily" in (parsed.netloc + parsed.path).lower()
        except Exception:
            return False

    def run(self):
        driver = None
        profile_dir = os.path.join(AppPath.DataRoot, "daily_report_profile")
        try:
            # Kill lingering Edge processes to release file locks (Windows only)
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True)
                subprocess.run(["taskkill", "/F", "/IM", "msedgedriver.exe"], capture_output=True)

            # Cleanly remove any previous profile
            import shutil
            if os.path.exists(profile_dir):
                clean_profile_locks(profile_dir)
                shutil.rmtree(profile_dir, ignore_errors=True)
            os.makedirs(profile_dir, exist_ok=True)

            opts = Options()
            opts.page_load_strategy = 'eager'
            if not self._show_web_page:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--start-maximized")
            opts.add_argument("--enable-logging")
            opts.add_argument("--v=1")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument(f"--user-data-dir={profile_dir}")

            service = Service(executable_path=self.driver_path)
            driver = webdriver.Edge(service=service, options=opts)

            Log.info("AuthWorker: navigating to daily report URL...")
            driver.get(DAILY_REPORT_URL)

            # Wait up to 5s for redirect chain to settle
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: (self._is_daily_url(d.current_url or "") or
                               "authen" in (d.current_url or "").lower() or
                               "login" in (d.current_url or "").lower())
                )
            except TimeoutException:
                pass

            final_url = (driver.current_url or "").lower()
            Log.info(f"AuthWorker: final URL type: {self._classify_url(final_url)}")

            # ── On daily host without form → fall through to content check ──
            if self._is_daily_url(driver.current_url or ""):
                form_el = fast_find_any(driver, [
                    (By.ID, "task"),
                    (By.ID, "proList"),
                ])
                if form_el:
                    Log.info("AuthWorker: on daily form page - authorized")
                    self.auth_success.emit()
                    return
                Log.info("AuthWorker: daily host without form, checking content...")

            # ── Check page content for QR or phone login form ──
            Log.info("AuthWorker: checking page content for auth state...")

            # Wait up to 5s for elements to render (JS may take time)
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: (
                        fast_find_any(d, AUTH_QR_SELECTORS + AUTH_PHONE_INPUT_SELECTORS) is not None
                        or self._is_daily_url(d.current_url or "")
                    )
                )
            except TimeoutException:
                pass

            while True:
                Log.info("AuthWorker: main auth loop iteration")
                if self._cancel:
                    Log.info("AuthWorker: cancelled in main loop")
                    return
                time.sleep(0.5)
                Log.info("AuthWorker: scanning for QR...")
                qr_element = fast_find_any(driver, AUTH_QR_SELECTORS)
                if qr_element:
                    Log.info("AuthWorker: QR element found, waiting for render...")
                    qr_element = find_element_any(driver, AUTH_QR_SELECTORS, timeout=3)
                    if qr_element:
                        self.qr_ready.emit(qr_element.screenshot_as_png)
                        self._wait_for_auth_or_switch(driver)
                        with self._lock:
                            if self._restart:
                                self._restart = False
                                self._use_phone = False
                                Log.info("AuthWorker: restarting auth loop from QR")
                                continue
                        return
                    if self._is_daily_url(driver.current_url or ""):
                        Log.info("AuthWorker: auth completed during QR wait")
                        self.auth_success.emit()
                        return
                    Log.info("AuthWorker: QR disappeared, trying phone login")
                    self._do_phone_login(driver)
                    return

                phone_el = fast_find_any(driver, AUTH_PHONE_INPUT_SELECTORS)
                if phone_el:
                    Log.info("AuthWorker: phone form found, starting phone login")
                    self._do_phone_login(driver)
                    return

                if self._is_daily_url(driver.current_url or ""):
                    Log.info("AuthWorker: redirected to daily during wait - authorized")
                    self.auth_success.emit()
                    return

                Log.warn("AuthWorker: no QR or phone form detected; cannot confirm auth")
                self.auth_error.emit("Cannot confirm authorization state. Please retry authorization.")
                return

        except Exception as e:
            Log.error(f"AuthWorker error: {e}")
            self.auth_error.emit(str(e))
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            clean_profile_cache(profile_dir)

    def _classify_url(self, url):
        try:
            parsed = urlparse(url)
            host_path = (parsed.netloc + parsed.path).lower()
        except Exception:
            host_path = url.lower()
        if "daily" in host_path:
            return "daily report page"
        if "authen" in host_path:
            return "authorize page"
        if "login" in host_path:
            return "login page"
        return "unknown"

    def _wait_for_auth_or_switch(self, driver):
        """After showing QR code, wait for user to scan QR or switch to phone login."""
        while True:
            with self._lock:
                if self._use_phone:
                    break
            if self._cancel:
                return
            time.sleep(1)
            try:
                if self._is_daily_url(driver.current_url or ""):
                    self.auth_success.emit()
                    return
            except Exception:
                self.auth_error.emit("Browser disconnected.")
                return

        # User switched to phone login
        self._do_phone_login(driver)
        Log.info("AuthWorker: _wait_for_auth_or_switch returning after _do_phone_login")

    def _do_phone_login(self, driver):
        Log.info("AuthWorker: starting phone login flow")

        # Switch to phone login tab only if phone input is not visible
        if not fast_find_any(driver, AUTH_PHONE_INPUT_SELECTORS):
            self._click_switch(driver)
            # Confirm browser switched to phone page before updating UI
            Log.info("AuthWorker: confirming browser switched to phone login...")
            phone_input = find_element_any(driver, AUTH_PHONE_INPUT_SELECTORS, timeout=5)
            if not phone_input:
                Log.warn("AuthWorker: browser did not switch to phone after click")
                qr_el = fast_find_any(driver, AUTH_QR_SELECTORS)
                if qr_el:
                    Log.info("AuthWorker: still on QR, sending back via _restart")
                    self.qr_ready.emit(qr_el.screenshot_as_png)
                    with self._lock:
                        self._restart = True
                else:
                    Log.info("AuthWorker: neither QR nor phone, trying phone login anyway")
                    self.need_phone.emit()
                    phone = self._wait_for_input("phone")
                    if phone is None:
                        with self._lock:
                            if self._switch_to_qr:
                                self._switch_to_qr = False
                                self._go_back_to_qr(driver)
                                Log.info("AuthWorker: _do_phone_login returning after _go_back_to_qr")
                                return
                        return
                    return
            Log.info("AuthWorker: browser switched to phone confirmed")

        # Check if user already requested switch back to QR during browser switch
        with self._lock:
            if self._switch_to_qr:
                Log.info("AuthWorker: user requested QR switch during browser transition, aborting need_phone")
                self._switch_to_qr = False
                self._go_back_to_qr(driver)
                return

        # Wait for phone number input
        self.need_phone.emit()
        phone = self._wait_for_input("phone")
        if phone is None:
            with self._lock:
                if self._switch_to_qr:
                    self._switch_to_qr = False
                    self._go_back_to_qr(driver)
                    return
            return
        Log.info("AuthWorker: got phone number")

        phone_input = find_element_any(driver, AUTH_PHONE_INPUT_SELECTORS, timeout=5)
        if phone_input:
            phone_input.clear()
            phone_input.send_keys(phone)
            time.sleep(1)

            # Click "下一步" (auto-triggers verification code)
            next_btn = find_element_any(driver, AUTH_PHONE_NEXT_BUTTON, timeout=5)
            if next_btn:
                next_btn.click()
                Log.info("AuthWorker: clicked next button")
                time.sleep(1)

            # Click "同意" if agreement modal appears
            agree_btn = find_element_any(driver, AUTH_AGREE_BUTTON, timeout=3)
            if agree_btn:
                agree_btn.click()
                Log.info("AuthWorker: clicked agree button")
                time.sleep(2)
            else:
                Log.info("AuthWorker: no agreement modal, proceeding")

        # Wait for verification code
        self.need_code.emit()
        code = self._wait_for_input("code")
        if code is None:
            with self._lock:
                if self._switch_to_qr:
                    self._switch_to_qr = False
                    self._go_back_to_qr(driver)
                    Log.info("AuthWorker: _do_phone_login(code phase) returning after _go_back_to_qr")
                    return
            return
        Log.info("AuthWorker: got verification code")

        code_input = find_element_any(driver, AUTH_CODE_INPUT_SELECTORS, timeout=5)
        if code_input:
            code_input.send_keys(code)
            Log.info("AuthWorker: entered verification code, waiting for auto-verify...")
            time.sleep(5)
        else:
            Log.info("AuthWorker: no code input found, trying submit button")
            submit_btn = find_element_any(driver, AUTH_SUBMIT_SELECTORS, timeout=3)
            if submit_btn:
                submit_btn.click()
                Log.info("AuthWorker: clicked login/submit button")
                time.sleep(3)

        # Wait for authorization redirect
        Log.info("AuthWorker: waiting for auth redirect...")
        try:
            WebDriverWait(driver, 30).until(
                lambda d: "daily" in (d.current_url or "")
            )
            Log.info("AuthWorker: phone login auth successful")
            self.auth_success.emit()
        except TimeoutException:
            Log.warn("AuthWorker: phone login auth timeout")
            self.auth_error.emit("Login timed out. Please try again.")

    def _go_back_to_qr(self, driver):
        """Clear storage and reload auth page to show QR by default. Sets _restart flag so outer loop re-enters auth flow."""
        Log.info("AuthWorker: clearing storage and reloading for QR login")
        driver.execute_script("""
            try { sessionStorage.clear(); } catch(e) {}
            try { localStorage.clear(); } catch(e) {}
        """)
        driver.get(DAILY_REPORT_URL)
        qr_element = find_element_any(driver, AUTH_QR_SELECTORS, timeout=10)
        if qr_element:
            Log.info("AuthWorker: back to QR login")
            self.qr_ready.emit(qr_element.screenshot_as_png)
            with self._lock:
                self._restart = True
                Log.info("AuthWorker: _restart set to True")
        else:
            self.auth_error.emit("Could not find QR code after page reload.")
        Log.info("AuthWorker: _go_back_to_qr returning")

    def _wait_for_input(self, input_type):
        """Wait for UI to provide input via set_phone / set_code. Returns value or None on timeout/cancel/switch-qr."""
        value = None
        for _ in range(120):  # 120 seconds timeout
            if self._cancel:
                return None
            with self._lock:
                if self._switch_to_qr:
                    return None
                if input_type == "phone" and self._phone is not None:
                    value = self._phone
                    self._phone = None
                    break
                if input_type == "code" and self._code is not None:
                    value = self._code
                    self._code = None
                    break
            time.sleep(1)
        return value


class RemoteAuthWorker(QThread):
    qr_ready = pyqtSignal(bytes)
    need_phone = pyqtSignal()
    need_code = pyqtSignal()
    auth_success = pyqtSignal()
    auth_error = pyqtSignal(str)

    def __init__(self, ssh_cfg, driver_path, show_web_page=False):
        super().__init__()
        self.ssh_cfg = ssh_cfg
        self.driver_path = driver_path
        self._show_web_page = bool(show_web_page)
        self._phone = None
        self._code = None
        self._use_phone = False
        self._switch_to_qr = False
        self._cancel = False
        self._lock = threading.RLock()

    def set_phone(self, phone):
        with self._lock:
            self._phone = phone

    def set_code(self, code):
        with self._lock:
            self._code = code

    def switch_to_phone(self):
        with self._lock:
            self._use_phone = True

    def cancel(self):
        self._cancel = True

    def switch_to_qr(self):
        with self._lock:
            self._switch_to_qr = True
            self._use_phone = False

    def run(self):
        import json as _json
        import socket

        try:
            runner_path = f"{AppPath.RemoteAppRoot}/servers/current/auto-clock-runner"
            cmd = f"{runner_path} auth --driver_path={self.driver_path} --interactive"
            if self._show_web_page:
                cmd += " --show_web_page"

            Log.info(f"RemoteAuthWorker: executing: {cmd}")

            with SshClient(self.ssh_cfg) as ssh:
                transport = ssh._client.get_transport()
                chan = transport.open_session(timeout=60)
                chan.exec_command(cmd)
                chan.settimeout(0.5)

                stdin = chan.makefile("wb")
                stdout = chan.makefile("r")
                stderr = chan.makefile_stderr("r")

                write_buf = []
                raw_non_json_lines = []

                def _flush_writes():
                    while write_buf:
                        data = write_buf.pop(0)
                        stdin.write(data)
                        stdin.flush()

                while not self._cancel:
                    # Check if we need to send something
                    with self._lock:
                        if self._use_phone:
                            write_buf.append(_json.dumps({"type": MSG_SWITCH_PHONE}) + "\n")
                            self._use_phone = False
                        if self._switch_to_qr:
                            write_buf.append(_json.dumps({"type": MSG_SWITCH_QR}) + "\n")
                            self._switch_to_qr = False
                    _flush_writes()

                    # Try to read a line (non-blocking with timeout)
                    line = None
                    try:
                        line = stdout.readline()
                    except socket.timeout:
                        continue
                    except Exception:
                        break

                    if not line:
                        break
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        msg = _json.loads(line)
                    except _json.JSONDecodeError:
                        raw_non_json_lines.append(line)
                        continue

                    msg_type = msg.get("type", "")

                    if msg_type == MSG_QR_READY:
                        import base64
                        raw = base64.b64decode(msg.get("data", ""))
                        self.qr_ready.emit(raw)

                    elif msg_type == MSG_NEED_PHONE:
                        self.need_phone.emit()
                        phone = self._wait_for_input("phone")
                        if phone is None:
                            continue
                        write_buf.append(_json.dumps({"type": MSG_PHONE, "data": phone}) + "\n")
                        _flush_writes()

                    elif msg_type == MSG_NEED_CODE:
                        self.need_code.emit()
                        code = self._wait_for_input("code")
                        if code is None:
                            continue
                        write_buf.append(_json.dumps({"type": MSG_CODE, "data": code}) + "\n")
                        _flush_writes()

                    elif msg_type == MSG_AUTH_SUCCESS:
                        self.auth_success.emit()
                        return

                    elif msg_type == MSG_AUTH_ERROR:
                        self.auth_error.emit(msg.get("data", "Unknown error"))
                        return

            if self._cancel:
                Log.info("RemoteAuthWorker: cancelled")
                return

            exit_code = -1
            try:
                if chan.exit_status_ready():
                    exit_code = chan.recv_exit_status()
            except Exception:
                pass

            err_lines = []
            try:
                err_content = stderr.read()
                if err_content:
                    err_lines.extend([ln.strip() for ln in str(err_content).splitlines() if ln.strip()])
            except Exception:
                pass

            detail_tail = ""
            merged_lines = raw_non_json_lines + err_lines
            if merged_lines:
                detail_tail = " | ".join(merged_lines[-2:])

            Log.warn(f"RemoteAuthWorker: SSH channel closed unexpectedly, exit_code={exit_code}, detail={detail_tail}")
            if detail_tail:
                self.auth_error.emit(f"Remote auth process exited unexpectedly (code={exit_code}): {detail_tail}")
            else:
                self.auth_error.emit(f"Remote auth process exited unexpectedly (code={exit_code}).")
        except Exception as e:
            Log.error(f"RemoteAuthWorker error: {e}")
            self.auth_error.emit(str(e))

    def _wait_for_input(self, input_type):
        value = None
        for _ in range(180):
            if self._cancel:
                return None
            with self._lock:
                if self._switch_to_qr:
                    return None
                if input_type == "phone" and self._phone is not None:
                    value = self._phone
                    self._phone = None
                    break
                if input_type == "code" and self._code is not None:
                    value = self._code
                    self._code = None
                    break
            self.msleep(1000)
        return value
