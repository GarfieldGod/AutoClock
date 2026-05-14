import os
import json

from src.utils.log import Log
from src.utils.utils import Utils
from src.utils.const import Key, AppPath
from src.core.daily_report.daily_report import DailyReport, DailyReportConfig


class DailyReportManager:
    def __init__(self, show_web_page_override=None):
        try:
            if not os.path.exists(AppPath.DataJson):
                self.status = False
                self.error = f"{AppPath.DataJson} does not exist."
                return

            with open(AppPath.DataJson, "r", encoding="utf-8") as f:
                data = json.load(f)

                check_ret = DailyReportManager.check_data(data)
                if not check_ret:
                    raise Exception("Check data error.")

                self.user_name = data[Key.UserName]
                self.user_password = data[Key.UserPassword]
                self.driver_path = data[Key.DriverPath]

                self.work_description = data.get(Key.ReportWorkDescription, "")
                self.normal_workload = data.get(Key.ReportNormalWorkload, "")
                self.overtime_workload = data.get(Key.ReportOvertimeWorkload, "")
                self.project_name = data.get(Key.ReportProjectName, "")
                self.project_task = data.get(Key.ReportProjectTask, "")
                self.activity_type = data.get(Key.ReportActivityType, "")
                self.project_type = data.get(Key.ReportProjectType, "")

                self.show_web_page = data.get(Key.ShowWebPage, False)
                if show_web_page_override is not None:
                    self.show_web_page = bool(show_web_page_override)

                self.status = True
        except Exception as e:
            Log.error(f"DailyReportManager initialization error: {e}")
            self.status = False
            self.error = str(e)

    def run(self):
        if not self.status:
            return self.status, self.error

        config = DailyReportConfig(
            driver_path=self.driver_path,
            user_name=self.user_name,
            user_password=self.user_password,
            work_description=self.work_description,
            normal_workload=self.normal_workload,
            overtime_workload=self.overtime_workload,
            project_name=self.project_name,
            project_task=self.project_task,
            activity_type=self.activity_type,
            project_type=self.project_type,
            show_web_page=self.show_web_page,
            wait_time=2,
        )

        report = DailyReport(config)
        ok, error = report.run()
        return ok, error

    @staticmethod
    def check_data(data):
        Log.info(f"user_name: [{data.get(Key.UserName)}]")
        if data.get(Key.UserName) == Key.Empty:
            Log.error("[username] is empty.")
            raise Exception("[username] is empty.")

        if data.get(Key.UserPassword) == Key.Empty:
            Log.error("[password] is empty.")
            raise Exception("[password] is empty.")

        if data.get(Key.DriverPath) == Key.Empty:
            Log.error("[driver path] is empty.")
            raise Exception("[driver path] is empty.")

        if not os.path.exists(data.get(Key.DriverPath, "")):
            Log.error("[driver path] does not exist.")
            raise Exception("[driver path] does not exist.")

        return True


def run_daily_report(is_test=False, show_web_page_override=None):
    try:
        if not is_test:
            manager = DailyReportManager(show_web_page_override=show_web_page_override)
            ok, error = manager.run()
            return ok, error
        else:
            return True, None
    except BaseException as e:
        return False, str(e)
