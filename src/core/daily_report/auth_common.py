import os
import sys
import stat
import time
import json
import base64
import shutil

from selenium.webdriver.common.by import By
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
]

AUTH_CODE_INPUT_SELECTORS = [
    (By.CSS_SELECTOR, "input.base-code-box-input:not([disabled])"),
    (By.CSS_SELECTOR, "input[name='code_box_input_item']:not([disabled])"),
    (By.XPATH, "//input[contains(@placeholder, '验证码') or contains(@placeholder, 'code')]"),
    (By.XPATH, "//*[contains(text(), '验证码')]/following::input[1]"),
]

AUTH_SEND_CODE_SELECTORS = [
    (By.XPATH, "//*[contains(text(), '获取') or contains(text(), '发送')]"),
    (By.XPATH, "//*[contains(@class, 'send')]"),
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
]

MSG_QR_READY = "qr_ready"
MSG_NEED_PHONE = "need_phone"
MSG_NEED_CODE = "need_code"
MSG_AUTH_SUCCESS = "auth_success"
MSG_AUTH_ERROR = "auth_error"
MSG_PHONE = "phone"
MSG_CODE = "code"
MSG_SWITCH_PHONE = "switch_phone"
MSG_SWITCH_QR = "switch_qr"
MSG_CANCEL = "cancel"


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
