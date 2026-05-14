import cv2
import numpy as np
import time, base64, io, random, os

from PIL import Image
from datetime import datetime
from dataclasses import dataclass
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.log import Log
from src.utils.const import AppPath


def dataurl_to_cv2(data_url):
    header, b64 = data_url.split(',', 1)
    img_bytes = base64.b64decode(b64)
    pil = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    arr = np.array(pil)[:, :, ::-1]
    return arr


def png_bytes_to_cv2(png_bytes):
    pil = Image.open(io.BytesIO(png_bytes)).convert('RGB')
    arr = np.array(pil)[:, :, ::-1]
    return arr


def element_screenshot_bytes(driver, selector):
    try:
        we = driver.find_element(By.CSS_SELECTOR, selector)
        return we.screenshot_as_png
    except Exception:
        return None


def get_element_image_source(driver, selector):
    try:
        el = driver.find_element(By.CSS_SELECTOR, selector)
        tag = el.tag_name.lower()
        if tag == 'img':
            return el.get_attribute('src')
        if tag == 'canvas':
            return driver.execute_script("return arguments[0].toDataURL('image/png');", el)
        bg = el.value_of_css_property('background-image')
        if bg and bg != 'none':
            start = bg.find('url(')
            if start >= 0:
                start += 4
                end = bg.rfind(')')
                url = bg[start:end].strip('"').strip("'")
                if url:
                    return url
        return None
    except Exception:
        return None


def download_image_to_cv2(url):
    try:
        import requests
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return png_bytes_to_cv2(resp.content)
    except Exception:
        return None


def get_image_cv2(driver, selector):
    src = get_element_image_source(driver, selector)
    if src:
        if src.startswith('data:'):
            try:
                return dataurl_to_cv2(src)
            except Exception:
                pass
        elif src.startswith('http'):
            try:
                img = download_image_to_cv2(src)
                if img is not None:
                    return img
            except Exception:
                pass
    png = element_screenshot_bytes(driver, selector)
    if png:
        try:
            return png_bytes_to_cv2(png)
        except Exception:
            pass
    return None


def find_gap_position(bg_img, block_img):
    bg_gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
    if block_img.shape[2] == 4:
        block_bgr = block_img[:, :, :3]
        alpha = block_img[:, :, 3]
        _, mask = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
        block_gray = cv2.cvtColor(block_bgr, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(bg_gray, block_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
    else:
        block_gray = cv2.cvtColor(block_img, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(bg_gray, block_gray, cv2.TM_CCOEFF_NORMED)

    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    h, w = block_gray.shape[:2]
    target_x = max_loc[0] + w // 2
    Log.info(f"模板匹配结果: 位置=({max_loc[0]}, {max_loc[1]}), 置信度={max_val:.3f}, 目标x={target_x}")
    return target_x


def find_gap_by_edges(bg_img):
    gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    cols_sum = np.sum(edges, axis=0)
    threshold = np.max(cols_sum) * 0.3
    candidates = np.where(cols_sum > threshold)[0]
    if len(candidates) == 0:
        return None

    gap_center = int(np.mean(candidates))
    Log.info(f"边缘检测缺口位置: x={gap_center}")
    return gap_center


def drag_slider_to_position(driver, slider_sel, track_sel, target_x):
    slider = driver.find_element(By.CSS_SELECTOR, slider_sel)
    track_w = driver.execute_script(
        "var el=document.querySelector(arguments[0]); if(!el) return 300; return el.getBoundingClientRect().width;",
        track_sel
    )
    max_x = int(track_w) if track_w else 300

    actions = ActionChains(driver)
    actions.click_and_hold(slider).perform()

    moved = 0
    target = min(target_x, max_x)

    while moved < target:
        remaining = target - moved
        if remaining > 30:
            step = random.randint(8, 15)
        elif remaining > 15:
            step = random.randint(4, 8)
        elif remaining > 5:
            step = random.randint(2, 4)
        else:
            step = remaining

        step = min(step, remaining)
        actions.move_by_offset(step, random.uniform(-1, 1)).perform()
        moved += step
        time.sleep(random.uniform(0.02, 0.06))

    overshoot = random.randint(1, 3)
    actions.move_by_offset(overshoot, random.uniform(-1, 1)).perform()
    moved += overshoot
    time.sleep(0.05)

    if moved > target:
        back = moved - target
        actions.move_by_offset(-back, 0).perform()
        moved = target
        time.sleep(0.03)

    time.sleep(random.uniform(0.1, 0.2))
    actions.release().perform()
    Log.info(f"滑块拖动完成: 目标={target}px, 实际移动={moved}px")
    return moved


@dataclass
class SliderSelectors:
    bg: str
    block: str
    slider: str
    track: str


def solve_puzzle_captcha(driver, selectors: SliderSelectors, max_attempts=3):
    Log.info("进入拼图滑块验证码流程...")

    for attempt in range(max_attempts):
        Log.info(f"[{attempt + 1}/{max_attempts}] 尝试拼图滑块验证...")

        try:
            wait = WebDriverWait(driver, 10)
            wait.until(lambda d: d.execute_script(
                "return !!document.querySelector(arguments[0])", selectors.bg
            ))
        except Exception as e:
            Log.error(f"验证码背景元素未找到: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            return False, "验证码背景元素未找到"

        bg_img = get_image_cv2(driver, selectors.bg)
        if bg_img is None:
            Log.waring("无法获取背景图，尝试截图方式")
            png = element_screenshot_bytes(driver, selectors.bg)
            if png:
                bg_img = png_bytes_to_cv2(png)
        if bg_img is None:
            Log.error("获取背景图失败")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            return False, "获取验证码背景图失败"

        target_x = None
        block_img = get_image_cv2(driver, selectors.block)
        if block_img is not None:
            Log.info("获取到滑块拼图块，使用模板匹配定位缺口")
            try:
                target_x = find_gap_position(bg_img, block_img)
            except Exception as e:
                Log.waring(f"模板匹配失败: {e}")

        if target_x is None:
            Log.info("模板匹配无效，尝试边缘检测定位缺口")
            try:
                target_x = find_gap_by_edges(bg_img)
            except Exception as e:
                Log.waring(f"边缘检测失败: {e}")

        if target_x is None:
            Log.error("无法定位缺口位置")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            return False, "无法定位滑块缺口位置"

        try:
            drag_slider_to_position(driver, selectors.slider, selectors.track, target_x)
        except Exception as e:
            Log.error(f"拖动滑块失败: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            return False, f"拖动滑块失败: {e}"

        time.sleep(1.5)

        save_path = f"{AppPath.ScreenshotRoot}/{datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')}_puzzle_{attempt + 1}.png"
        try:
            if not os.path.exists(AppPath.ScreenshotRoot):
                os.makedirs(AppPath.ScreenshotRoot, exist_ok=True)
            bg_el = driver.find_element(By.CSS_SELECTOR, selectors.bg)
            bg_el.screenshot(save_path)
        except Exception:
            pass

        result = driver.execute_script("""
            var tip = document.querySelector('.captcha_verify_message, .slide-tip, .captcha-tip, .msg, .error');
            if (tip) return tip.textContent.includes('成功') || tip.textContent.includes('通过');
            return false;
        """)

        try:
            error_visible = driver.execute_script("""
                var el = document.querySelector('.captcha_verify_message, .slide-tip, .captcha-tip, .msg, .error');
                if (el) {
                    var txt = el.textContent || '';
                    return txt.includes('失败') || txt.includes('错误') || txt.includes('重新') || txt.includes('不对');
                }
                return false;
            """)
            if error_visible:
                Log.waring("检测到验证失败提示，准备重试")
                if attempt < max_attempts - 1:
                    reset_btn = driver.find_elements(By.CSS_SELECTOR, '.captcha-refresh, .refresh-btn, .reload')
                    if reset_btn:
                        reset_btn[0].click()
                        time.sleep(1)
                    time.sleep(2)
                    continue
                return False, "滑块验证失败"

        except Exception:
            pass

        Log.info(f"滑块验证尝试 {attempt + 1} 完成")
        if result:
            Log.info("拼图滑块验证通过")
            return True, None

        if attempt < max_attempts - 1:
            time.sleep(2)

    Log.error("拼图滑块验证重试结束，未通过")
    return False, "拼图滑块验证重试结束，未通过"
