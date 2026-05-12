import os
import json

from src.utils.log import Log
from src.utils.utils import Utils
from src.utils.const import Key, AppPath, WebPath
from src.core.auto_clock import AutoClock, Config

class ClockManager:
    def __init__(self, show_web_page_override=None):
        try:
            if not os.path.exists(f"{AppPath.DataJson}"):
                self.status = False
                self.error = f"{AppPath.DataJson} does not exist."
                return

            with open(f"{AppPath.DataJson}", "r", encoding="utf-8") as f:
                data = json.load(f)

                check_ret = ClockManager.check_data(data)
                if not check_ret:
                    raise Exception("Check data error.")

                self.user_name = data[Key.UserName]
                self.user_password = data[Key.UserPassword]
                self.driver_path = data[Key.DriverPath]

                self.always_retry = data.get(Key.AlwaysRetry, False)
                self.captcha_retry_times = int(data.get(Key.CaptchaRetryTimes, 5))
                self.captcha_tolerance_angle = int(data.get(Key.CaptchaToleranceAngle, 5))
                self.show_web_page = data.get(Key.ShowWebPage, False)
                if show_web_page_override is not None:
                    self.show_web_page = bool(show_web_page_override)

                self.status = True
        except Exception as e:
            Log.error(f"ClockManager initialization error: {e}")
            self.status = False
            self.error = str(e)

    def clock(self):
        config = Config(
            driver_path=self.driver_path,
            remote_url=WebPath.NeusoftKQLoginPath,
            user_name=self.user_name,
            user_password=self.user_password,
            always_retry=self.always_retry,
            captcha_attempts=self.captcha_retry_times,
            tolerance=self.captcha_tolerance_angle,
            show_web_page=self.show_web_page,
            wait_time=2,
        )

        auto_clock = AutoClock(config)
        ok, error = auto_clock.run()
        auto_clock.quit()

        return ok, error

    def run(self):
        if not self.status:
            return
        self.status, self.error = self.clock()

    @staticmethod
    def check_data(data):
        Log.info(f"user_name: [{data[Key.UserName]}]")
        if data.get(Key.UserName) == Key.Empty:
            Log.error("[username] is empty.")
            raise Exception("[username] is empty.")

        if data.get(Key.UserPassword) == Key.Empty :
            Log.error("[password] is empty.")
            raise Exception("[password] is empty.")

        if data.get(Key.DriverPath) == Key.Empty:
            Log.error("[driver path] is empty.")
            raise Exception("[driver path] is empty.")

        if not os.path.exists(data[Key.DriverPath]):
            Log.error("[driver path] does not exist.")
            raise Exception("[driver path] does not exist.")

        return True

def run_clock(is_test=False, show_web_page_override=None):
    try:
        if not is_test:
            clock = ClockManager(show_web_page_override=show_web_page_override)
            clock.run()
            return clock.status, clock.error
        else:
            # run_test()
            return True, None
    except BaseException as e:
        return False, str(e)