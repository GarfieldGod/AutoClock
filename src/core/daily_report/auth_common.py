import os
import sys
import stat
import time
import json
import base64
import shutil
import re
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


AUTH_QR_SELECTORS = [
    (By.CSS_SELECTOR, "div.newLogin_scan-QR-code canvas"),
    (By.XPATH, "//*[contains(@class, 'newLogin_scan-QR')]//canvas"),
    (By.XPATH, "//img[contains(@class, 'qrcode')]"),
    (By.XPATH, "//img[contains(@src, 'qrcode')]"),
    (By.XPATH, "//img[contains(@src, 'dingtalk')]"),
    (By.XPATH, "//*[contains(@class, 'qrcode')]"),
    (By.XPATH, "//*[contains(@class, 'qr-code')]"),
    (By.XPATH, "//img[contains(@src, 'qr')]"),
]

AUTH_QR_SUCCESS_SELECTORS = [
    (By.XPATH, "//*[contains(text(), '扫码成功') or contains(text(), '扫描成功')]"),
]

AUTH_PHONE_SWITCH_SELECTORS = [
    (By.CSS_SELECTOR, "div.switch-login-mode-box"),
    (By.XPATH, "//*[contains(@class, 'switch-login-mode-box')]"),
]

AUTH_PHONE_INPUT_SELECTORS = [
    (By.CSS_SELECTOR, "input[type='tel']"),
    (By.XPATH, "//input[contains(@placeholder, '手机') or contains(@placeholder, 'phone')]"),
    (By.XPATH, "//*[contains(text(), '手机号')]/following::input[1]"),
]

AUTH_PHONE_NEXT_BUTTON = [
    (By.CSS_SELECTOR, "[data-test='login-phone-next-btn']"),
    (By.XPATH, "//button[contains(text(), '下一步')]"),
    (By.XPATH, "//button[contains(text(), '继续')]"),
]

AUTH_CODE_INPUT_SELECTORS = [
    (By.CSS_SELECTOR, "input.base-code-box-input:not([disabled])"),
    (By.CSS_SELECTOR, "input[name='code_box_input_item']:not([disabled])"),
    (By.XPATH, "//input[contains(@placeholder, '验证码') or contains(@placeholder, 'code')]"),
    (By.XPATH, "//*[contains(text(), '验证码')]/following::input[1]"),
]

AUTH_SEND_CODE_SELECTORS = [
    (By.CSS_SELECTOR, "button[data-test='send-code'], button[data-test='login-send-code-btn']"),
    (By.XPATH, "//button[contains(text(), '发送验证码') or contains(text(), '获取验证码') or contains(text(), '重新发送') or contains(text(), '发送') or contains(text(), '获取')]"),
    (By.XPATH, "//*[@role='button' and (contains(., '发送验证码') or contains(., '获取验证码') or contains(., '重新发送'))]"),
]

AUTH_SEND_CODE_COUNTDOWN_SELECTORS = [
    (By.CSS_SELECTOR, "div.base-code-box-count"),
    (By.XPATH, "//*[contains(text(), '秒后可重新获取验证码') or contains(text(), '秒后可重发') or contains(text(), '秒后')]"),
]

AUTH_SUBMIT_SELECTORS = [
    (By.XPATH, "//button[contains(text(), '登录') or contains(text(), '登入')]"),
    (By.XPATH, "//*[contains(@class, 'submit') or contains(@class, 'login')]"),
]

AUTH_QR_SWITCH_SELECTORS = [
    (By.CSS_SELECTOR, "div.switch-login-mode-box"),
    (By.XPATH, "//*[contains(@class, 'switch-login-mode-box')]"),
]

AUTH_AGREE_BUTTON = [
    (By.CSS_SELECTOR, "button.pp-modal-btn-confirm"),
    (By.XPATH, "//button[contains(text(), '同意')]"),
    (By.XPATH, "//button[contains(text(), '确认')]"),
]

AUTH_AUTHORIZED_SELECTORS = [
    (By.ID, "task"),
    (By.ID, "proList"),
    (By.XPATH, "//*[contains(text(), '新增')]"),
    (By.XPATH, "//*[contains(text(), '保存')]"),
    (By.ID, "date"),
]

MSG_QR_READY = "qr_ready"
MSG_NEED_PHONE = "need_phone"
MSG_NEED_CODE = "need_code"
MSG_AUTH_SUCCESS = "auth_success"
MSG_AUTH_ERROR = "auth_error"
MSG_LOG = "log"
MSG_PHONE = "phone"
MSG_CODE = "code"
MSG_SWITCH_PHONE = "switch_phone"
MSG_SWITCH_QR = "switch_qr"
MSG_CANCEL = "cancel"
MSG_SEND_CODE_TRIGGERED = "send_code_triggered"


def find_element_any(driver, selectors, timeout=3):
    for by, sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
            if el.is_displayed():
                return el
        except TimeoutException:
            continue
    return None


def fast_find_element_any(driver, selectors):
    for by, sel in selectors:
        try:
            elements = driver.find_elements(by, sel)
            for el in elements:
                try:
                    if el.is_displayed():
                        return el
                except Exception:
                    continue
        except Exception:
            continue
    return None


def clean_profile_locks(profile_dir):
    lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
    for subdir in ["", "Default"]:
        for name in lock_files:
            path = os.path.join(profile_dir, subdir, name)
            try:
                if os.path.isfile(path):
                    os.chmod(path, stat.S_IWRITE)
                    os.remove(path)
            except Exception:
                pass


def clean_profile_cache(profile_dir):
    cache_dirs = [
        "Default/Cache",
        "Default/Code Cache",
        "Default/Service Worker",
        "Default/GPUCache",
        "Default/Media Cache",
        "Default/Extensions",
        "Default/Storage/ext",
    ]
    for sub in cache_dirs:
        path = os.path.join(profile_dir, sub)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)


def clean_profile_session(profile_dir):
    session_files = [
        "Default/Current Session",
        "Default/Current Tabs",
        "Default/Last Session",
        "Default/Last Tabs",
        "Default/Last Active Tabs",
        "Default/Session_*",
    ]
    for pattern in session_files:
        if "*" in pattern:
            import glob
            for path in glob.glob(os.path.join(profile_dir, pattern)):
                try:
                    os.remove(path)
                except Exception:
                    pass
        else:
            path = os.path.join(profile_dir, pattern)
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                pass


def send_msg(msg_dict):
    print(json.dumps(msg_dict, ensure_ascii=False), flush=True)


def recv_msg():
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def is_daily_url(url):
    try:
        parsed = urlparse(url)
        return "daily" in (parsed.netloc + parsed.path).lower()
    except Exception:
        return False


def wait_auth_page_ready(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: (
                get_auth_page_state(d, element_timeout=0) in {"authorized", "qr", "qr_scanned", "phone", "login", "authen", "daily"}
            )
        )
    except TimeoutException:
        pass


def get_auth_page_state(driver, element_timeout=1):
    try:
        current = (driver.current_url or "").lower()
    except Exception:
        current = ""

    try:
        parsed = urlparse(current)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
    except Exception:
        host = ""
        path = ""

    if host in {"accounts.feishu.cn", "open.feishu.cn"} and path == "/open-apis/authen/v1/index":
        return "authorized"

    finder = find_element_any if element_timeout and element_timeout > 0 else fast_find_element_any

    if is_daily_url(current):
        auth_el = finder(driver, AUTH_AUTHORIZED_SELECTORS) if finder is fast_find_element_any else finder(driver, AUTH_AUTHORIZED_SELECTORS, timeout=element_timeout)
        if auth_el is not None:
            return "authorized"
        return "daily"

    qr_success_el = finder(driver, AUTH_QR_SUCCESS_SELECTORS) if finder is fast_find_element_any else finder(driver, AUTH_QR_SUCCESS_SELECTORS, timeout=element_timeout)
    if qr_success_el is not None:
        return "qr_scanned"

    qr_el = finder(driver, AUTH_QR_SELECTORS) if finder is fast_find_element_any else finder(driver, AUTH_QR_SELECTORS, timeout=element_timeout)
    if qr_el is not None:
        return "qr"

    phone_el = finder(driver, AUTH_PHONE_INPUT_SELECTORS) if finder is fast_find_element_any else finder(driver, AUTH_PHONE_INPUT_SELECTORS, timeout=element_timeout)
    if phone_el is not None:
        return "phone"

    if "login" in current:
        return "login"

    if "authen" in current or "auth" in current:
        return "authen"

    return "unknown"


def is_authorized(driver):
    return get_auth_page_state(driver, element_timeout=1) == "authorized"


def reset_to_qr_page(driver, daily_report_url, qr_timeout=10):
    try:
        driver.execute_script("""
            try { sessionStorage.clear(); } catch(e) {}
            try { localStorage.clear(); } catch(e) {}
        """)
    except Exception:
        pass
    try:
        driver.set_page_load_timeout(20)
        driver.get(daily_report_url)
    except TimeoutException:
        try:
            driver.execute_script("window.stop();")
        except Exception:
            pass
    except Exception:
        pass
    return find_element_any(driver, AUTH_QR_SELECTORS, timeout=qr_timeout)


def click_login_mode_switch(driver):
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
                try:
                    ActionChains(driver).move_to_element(el).click().perform()
                except Exception:
                    driver.execute_script("arguments[0].click();", el)
                time.sleep(2)
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def click_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    except Exception:
        pass
    try:
        element.click()
        return True
    except Exception:
        pass
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        return False


def find_send_code_element(driver, timeout=2):
    el = fast_find_element_any(driver, AUTH_SEND_CODE_SELECTORS)
    if el is not None:
        return el
    if timeout and timeout > 0:
        el = find_element_any(driver, AUTH_SEND_CODE_SELECTORS, timeout=timeout)
        if el is not None:
            return el
    try:
        return driver.execute_script("""
            const texts = ['发送验证码', '获取验证码', '重新发送'];
            const nodes = Array.from(document.querySelectorAll('button, [role="button"]'));
            for (const el of nodes) {
                if (!el || !el.textContent) continue;
                const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
                if (!text) continue;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;
                const rect = el.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) continue;
                if (texts.some(t => text.includes(t))) return el;
            }
            return null;
        """)
    except Exception:
        return None


def find_send_code_countdown_text(driver):
    el = fast_find_element_any(driver, AUTH_SEND_CODE_COUNTDOWN_SELECTORS)
    if el is None:
        return ""
    try:
        text = str(el.text or "").strip()
        if not text:
            return ""
        if re.search(r"\d+\s*秒", text):
            return text
        if "秒后" in text:
            return text
        return ""
    except Exception:
        return ""


def wait_for_send_code_ready_state(driver, timeout=6):
    deadline = time.time() + timeout
    # Phase 1: first 3 seconds, only check countdown and send button
    # This gives countdown text (e.g. "59秒后...") time to appear before
    # code_input elements are checked.
    phase1_deadline = min(time.time() + 3, deadline)
    while time.time() < phase1_deadline:
        countdown_text = find_send_code_countdown_text(driver)
        if countdown_text:
            return {"state": "countdown", "text": countdown_text, "element": None}
        send_btn = find_send_code_element(driver, timeout=0)
        if send_btn is not None:
            return {"state": "button", "text": "", "element": send_btn}
        time.sleep(0.2)
    # Phase 2: remaining time, also check code_input as fallback
    while time.time() < deadline:
        countdown_text = find_send_code_countdown_text(driver)
        if countdown_text:
            return {"state": "countdown", "text": countdown_text, "element": None}
        send_btn = find_send_code_element(driver, timeout=0)
        if send_btn is not None:
            return {"state": "button", "text": "", "element": send_btn}
        code_input = fast_find_element_any(driver, AUTH_CODE_INPUT_SELECTORS)
        if code_input is not None:
            return {"state": "code_input", "text": "", "element": code_input}
        time.sleep(0.2)
    # Final check after timeout
    countdown_text = find_send_code_countdown_text(driver)
    if countdown_text:
        return {"state": "countdown", "text": countdown_text, "element": None}
    send_btn = find_send_code_element(driver, timeout=0)
    if send_btn is not None:
        return {"state": "button", "text": "", "element": send_btn}
    code_input = fast_find_element_any(driver, AUTH_CODE_INPUT_SELECTORS)
    if code_input is not None:
        return {"state": "code_input", "text": "", "element": code_input}
    return {"state": "unknown", "text": "", "element": None}


def find_tenant_account_element(driver, tenant_name="东软集团", timeout=3):
    try:
        el = driver.execute_script("""
            const tenantName = arguments[0];
            const items = Array.from(document.querySelectorAll('.user-list-item[role="button"]'));
            for (const item of items) {
                const tenant = item.querySelector('.tenant-name');
                const text = (tenant?.textContent || '').replace(/\s+/g, ' ').trim();
                if (text === tenantName) return item;
            }
            return null;
        """, tenant_name)
        if el is not None:
            return el
    except Exception:
        pass
    selectors = [
        (By.XPATH, f"//div[contains(concat(' ', normalize-space(@class), ' '), ' user-list-item ') and @role='button'][.//*[contains(concat(' ', normalize-space(@class), ' '), ' tenant-name ') and normalize-space()='{tenant_name}']]"),
        (By.XPATH, f"//*[contains(concat(' ', normalize-space(@class), ' '), ' tenant-name ') and normalize-space()='{tenant_name}']/ancestor::div[@role='button' and contains(concat(' ', normalize-space(@class), ' '), ' user-list-item ')][1]"),
    ]
    return find_element_any(driver, selectors, timeout=timeout)


def maybe_select_tenant_account(driver, tenant_name="东软集团", timeout=2):
    el = find_tenant_account_element(driver, tenant_name=tenant_name, timeout=timeout)
    if el is None:
        return False
    if click_element(driver, el):
        time.sleep(2)
        return True
    return False


def wait_authorized_or_select_account(driver, timeout=30, tenant_name="东软集团"):
    deadline = time.time() + timeout
    selected = False
    while time.time() < deadline:
        if is_authorized(driver):
            return True, selected
        if maybe_select_tenant_account(driver, tenant_name=tenant_name, timeout=1):
            selected = True
            continue
        time.sleep(1)
    return is_authorized(driver), selected
