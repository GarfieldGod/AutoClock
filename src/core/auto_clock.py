import time

from selenium import webdriver
from dataclasses import dataclass
from selenium.webdriver.common.by import By
from selenium.common import TimeoutException
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.const import Key, AppPath
from src.utils.log import Log
from src.core.clock import clock
from src.core.login import login
from src.core.captcha import captcha, Selectors
from src.utils.utils import Utils


@dataclass
class Config:
    driver_path: str
    remote_url: str
    user_name: str
    user_password: str
    captcha_attempts: int = 3
    tolerance: int = 5
    wait_time: int = 2
    always_retry: bool = False
    show_web_page: bool = True
    auto_update_driver: bool = True

class AutoClock:
    def __init__(self, config: Config):
        self.driver_path = config.driver_path
        self.user_name = config.user_name
        self.user_password = config.user_password
        self.wait_time = config.wait_time
        self.captcha_attempts = config.captcha_attempts
        self.tolerance = config.tolerance
        self.remote_url = config.remote_url
        self.always_retry = config.always_retry
        self.show_web_page = config.show_web_page
        self.auto_update_driver = config.auto_update_driver
        self.driver = None
        try:
            self.driver = self.create_driver()
        except Exception as e:
            Log.error(f"Create driver error: {e}")

            if 'version' in str(e):
                try:
                    if not self.auto_update_driver:
                        raise Exception("Edge version not support, need to redownload driver.")

                    ok, driver_path = Utils.download_edge_web_driver()
                    if not ok:
                        raise Exception("Redownload Edge web driver error.")

                    self.driver_path = driver_path
                    self.driver = self.create_driver()

                    if self.driver is not None:
                        data = Utils.read_dict_from_json(AppPath.DataJson)
                        data[Key.DriverPath] = self.driver_path
                        Utils.write_dict_to_file(AppPath.DataJson, data)

                except Exception as e:
                    Log.error(f"Redownload and Create driver error: {e}")
                    raise Exception(f"Failed to create WebDriver: {e}")
            else:
                raise Exception(f"Failed to create WebDriver: {e}")

    def create_driver(self):
        # 创建浏览器驱动
        opts = Options()
        if not self.show_web_page:
            opts.add_argument("--headless=new")
            # 添加headless模式必需的选项
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
        
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--start-maximized")
        opts.add_argument("--enable-logging")
        opts.add_argument("--v=1")
        # 禁用一些可能导致问题的功能
        opts.add_argument("--disable-blink-features=AutomationControlled")
        
        service = Service(executable_path=self.driver_path)
        driver = webdriver.Edge(service=service, options=opts)

        Log.info("create driver successfully")
        return driver

    def auto_login(self):
        try:
            Log.info("DO AUTO LOGIN")
            self.driver.get(self.remote_url)
            Log.info(f"打开URL: {self.remote_url}")
            ret, error = login(self.driver, self.user_name, self.user_password, wait=self.wait_time)
            if ret:
                Log.info("已尝试提交登录表单。")
            else:
                info = f"自动登录执行失败，请检查选择器或页面加载。{error}"
                Log.error(info)
                raise Exception(info)

            time.sleep(2)
            WebDriverWait(self.driver, 3).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "#loginButton")))
            Log.info("登录按钮已消失，可能登录成功。")
            return True

        except TimeoutException as e:
            Log.error(f"等待登录按钮消失超时，登录状态未知")
            return False
        except Exception as e:
            info = f"登录失败: {e}"
            Log.error(info)
            return False
        finally:
            Log.info("登录流程结束; 保留浏览器窗口。")

    def auto_captcha(self):
        try:
            selectors = Selectors(
                canvas='#captchaImage',
                slider='.captcha-root .captcha-control-button',
                track='.captcha-control-wrap'
            )
            ret, error = captcha(self.driver, selectors=selectors, max_attempts=self.captcha_attempts,tolerance=self.tolerance)
            if ret:
                Log.info(f"识别验证码成功。")
            else:
                info = f"尝试自动通过验证码失败。请手动进行操作或重试！{error}"
                Log.error(info)

            return ret, error

        except Exception as e:
            info = f"验证码验证失败。请手动进行操作或重试！{e}"
            Log.error(info)
            return False

    def do_clock(self):
        try:
            Log.info("DO FINAL CLOCK")
            ret, error = clock(self.driver)
            return ret, error
        except Exception as e:
            Log.error(f"auto clock failed: {e}")
            return False, str(e)

    def quit(self):
        if self.driver:
            self.driver.quit()

    def auto_clock(self):
        try:
            ret_login = self.auto_login()
            Log.info(f"Login Result: {format(ret_login)}")
            ret, error = self.auto_captcha()
            Log.info(f"Captcha Result: {format(ret)}")
            if not ret:
                Log.info(f"Captcha failed, Always retry: {self.always_retry}")
                if self.always_retry:
                    round_count = 0
                    while not ret:
                        round_count += 1
                        # 每次auto_captcha调用已经是一轮完整的尝试(captcha_attempts次)
                        # 一轮失败后，重启浏览器进行新一轮尝试
                        Log.info(f"第{round_count}轮尝试失败(每轮{self.captcha_attempts}次)，重启浏览器进行新一轮尝试...")
                        self.quit()
                        time.sleep(2)
                        try:
                            self.driver = self.create_driver()
                            ret_login = self.auto_login()
                            Log.info(f"重启浏览器后登录结果: {format(ret_login)}")
                        except Exception as e:
                            Log.error(f"重启浏览器失败: {e}")
                            return False, f"重启浏览器失败: {e}"
                        
                        ret, error = self.auto_captcha()
                        Log.info(f"第{round_count + 1}轮Captcha结果: {format(ret)}, error: {error}")
                else:
                    return ret, error
            return self.do_clock()
        except Exception as e:
            return False, str(e)

    def run(self):
        ok, error = self.auto_clock()
        time.sleep(5)
        Log.info("流程结束，关闭浏览器驱动。")
        self.quit()
        if ok:
            Log.info("最终结果：成功! 结束运行。")
        else:
            Log.error(f"最终结果：失败! 请重试。{error}")

        return ok, error