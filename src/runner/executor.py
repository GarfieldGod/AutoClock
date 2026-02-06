import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, date

import chinese_calendar as calendar

from src.core.clock_manager import run_clock
from src.extend.email_server import send_email_by_result
from src.utils.const import AppPath, Key
from src.utils.log import Log
from src.utils.utils import Utils


@dataclass
class RunnerResult:
    ok: bool
    error: str | None
    task: dict | None
    start_time: str
    end_time: str
    cost_time_sec: int | None


def _write_runner_result(result: RunnerResult):
    try:
        payload = {
            "ok": result.ok,
            "error": result.error,
            "task": result.task,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "cost_time_sec": result.cost_time_sec,
        }
        os.makedirs(os.path.dirname(AppPath.RunnerResultJson), exist_ok=True)
        with open(AppPath.RunnerResultJson, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
    except Exception as e:
        Log.error(f"Write runner result failed: {e}")


def run_task_by_id(task_id: str, headless: bool = False):
    config_data = Utils.read_dict_from_json(AppPath.DataJson) or {}

    email = config_data.get(Key.NotificationEmail)
    send_email_success = config_data.get(Key.SendEmailWhenSuccess, False)
    send_email_failed = config_data.get(Key.SendEmailWhenFailed, False)

    ok = False
    error = None
    task = None
    start_time = datetime.now()

    try:
        task = Utils.find_task(task_id)
        if not task:
            raise Exception(f"Task ID: {task_id} not found.")

        operation = task.get(Key.Operation)
        day_time_type = task.get(Key.DayTimeType)
        trigger_type = task.get(Key.TriggerType)

        if trigger_type == Key.SmartHoliday:
            try:
                start_year = int(task.get(Key.Year))
                start_month = int(task.get(Key.Month))
                start_day = int(task.get(Key.Day))
                start_date = date(start_year, start_month, start_day)
            except Exception as e:
                return False, "SmartHoliday task missing or invalid start date"

            today = date.today()

            if today.year != start_year:
                return True, None

            if today < start_date or today > date(start_year, 12, 31):
                return True, None

            if not calendar.is_workday(today):
                return True, None

        Log.open()
        Log.info(f"Runner Get Task Id: {task_id}")

        if day_time_type and day_time_type == Key.Random:
            time_offset = task.get(Key.TimeOffset, 0)
            random_sec = random.randint(0, time_offset)
            Log.info(f"Runner wait {random_sec} sec...")
            time.sleep(random_sec)

        Log.info(f"Task ID: {task_id} Operation: {operation}")

        if operation == Key.AutoClock:
            ok, error = run_clock(show_web_page_override=(False if headless else None))
        elif operation == Key.ShutDownSystem:
            if os.name == 'nt':
                from src.extend.auto_windows_operation import run_windows_shutdown
            else:
                from src.extend.auto_linux_operation import run_linux_shutdown as run_windows_shutdown
            ok, error = run_windows_shutdown(30)
        elif operation == Key.SystemSleep:
            if os.name == 'nt':
                from src.extend.auto_windows_operation import run_windows_sleep
            else:
                from src.extend.auto_linux_operation import run_linux_sleep as run_windows_sleep
            ok, error = run_windows_sleep(30)
        elif operation == Key.DisconnectNetwork:
            if os.name == 'nt':
                from src.extend.network_manager import disconnect_network
            else:
                from src.extend.auto_linux_network import disconnect_network
            ok, error = disconnect_network(30)
        elif operation == Key.ConnectNetwork:
            if os.name == 'nt':
                from src.extend.network_manager import connect_network
            else:
                from src.extend.auto_linux_network import connect_network
            ok, error = connect_network()
            if ok:
                Log.info("Network connected, wait 10 sec...")
                time.sleep(10)
        else:
            error = f"No operation specified for: {operation}"

        end_time = datetime.now()
        elapsed_sec = int((end_time - start_time).total_seconds())
        if task is not None:
            task[Key.CostTime] = elapsed_sec

        runner_result = RunnerResult(
            ok=ok,
            error=error,
            task=task,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            cost_time_sec=elapsed_sec,
        )
        _write_runner_result(runner_result)

    except Exception as e:
        end_time = datetime.now()
        error = str(e)
        runner_result = RunnerResult(
            ok=False,
            error=error,
            task=task,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            cost_time_sec=int((end_time - start_time).total_seconds()),
        )
        _write_runner_result(runner_result)

    try:
        if email:
            if not error:
                error = "Unknow Error"
            send_email_by_result(
                task=task,
                email=email,
                send_email_success=send_email_success,
                send_email_failed=send_email_failed,
                ok=ok,
                error=error,
            )
    except Exception as e:
        Log.error(f"Send email failed: {e}")

    return ok, error
