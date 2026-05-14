import time

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.log import Log
from src.core.daily_report.slider_captcha import solve_puzzle_captcha, SliderSelectors


def cps_login(driver, user, pwd, wait=2):
    username_selectors = [
        "input.textfield.userName",
        "input[name='username']",
        "input[type='text']",
        "input#username",
        "input[name='account']",
    ]
    password_selectors = [
        "input.textfield.password",
        "input[name='password']",
        "input[type='password']",
        "input#password",
    ]
    login_button_selectors = [
        "#loginButton",
        "button[type='submit']",
        "input[type='submit']",
        "#loginBtn",
        ".login-btn",
    ]

    waiter = WebDriverWait(driver, max(15, wait))

    username_el = None
    for sel in username_selectors:
        try:
            username_el = waiter.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            Log.info(f"定位用户名输入框: {sel}")
            break
        except TimeoutException:
            continue
    if username_el is None:
        return False, "定位用户名输入框失败"

    password_el = None
    for sel in password_selectors:
        try:
            password_el = waiter.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            Log.info(f"定位密码输入框: {sel}")
            break
        except TimeoutException:
            continue
    if password_el is None:
        return False, "定位密码输入框失败"

    username_el.clear()
    username_el.send_keys(user)
    password_el.clear()
    password_el.send_keys(pwd)
    Log.info("填写用户名和密码成功")

    login_btn = None
    for sel in login_button_selectors:
        try:
            login_btn = waiter.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            Log.info(f"定位登录按钮: {sel}")
            break
        except TimeoutException:
            continue

    if login_btn is None:
        return False, "定位登录按钮失败"

    login_btn.click()
    Log.info("已点击登录按钮")

    time.sleep(1)

    slider_selectors = SliderSelectors(
        bg='#slideBg, .slide-bg, canvas#captcha, .captcha-bg, #captchaImage, .geetest_canvas_bg',
        block='#slideBlock, .slide-block, .captcha-block, .geetest_slice_bg',
        slider='#slideBtn, .slide-btn, .drag-btn, .slider-btn, .captcha_verify_slide--control, .geetest_slider_button',
        track='.slide-track, .captcha_verify_slide, .geetest_slider, .captcha-control-wrap',
    )

    slider_visible = False
    for sel_candidate in ['#slideBtn', '.slide-btn', '.drag-btn', '.slider-btn',
                          '.captcha_verify_slide--control', '.geetest_slider_button']:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel_candidate)
            if els and els[0].is_displayed():
                slider_visible = True
                Log.info(f"检测到滑块按钮: {sel_candidate}")
                break
        except Exception:
            continue

    if slider_visible:
        Log.info("检测到滑块验证码，开始求解")
        ok, error = solve_puzzle_captcha(driver, slider_selectors, max_attempts=3)
        if not ok:
            Log.error(f"滑块验证失败: {error}")
            return False, f"滑块验证失败: {error}"
        Log.info("滑块验证通过，等待登录跳转")
        time.sleep(3)
    else:
        Log.info("未检测到滑块验证码，继续等待登录完成")

    return True, None
