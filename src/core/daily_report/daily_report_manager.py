import os
import time

from src.utils.log import Log
from src.utils.const import Key, AppPath
from src.utils.utils import Utils
from src.core.daily_report.daily_report import DailyReport, DailyReportConfig, DAILY_REPORT_URL
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium import webdriver


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
