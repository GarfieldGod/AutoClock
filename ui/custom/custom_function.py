import copy
from datetime import datetime

from PyQt5.QtCore import QDate

from src.utils.const import Key
from src.utils.log import Log
from src.utils.utils import Utils

class UiFunc:
    @staticmethod
    def generate_task_name(task):
        task_name = (task.get(Key.TaskName) +
                     "_Type_" + task.get(Key.TriggerType) +
                     "_Date_" + task.get(Key.ExecuteDay) +
                     "_Time_" + task.get(Key.ExecuteTime) +
                     "_Id_" + task.get(Key.TaskID))
        return Utils.replace_signs(task_name)

    @staticmethod
    def generate_task_execute_day(value):
        trigger_type = value.get(Key.TriggerType)
        execute_day = None
        match trigger_type:
            case Key.Once:
                q_date = QDate(int(value.get(Key.Year)), int(value.get(Key.Month)), int(value.get(Key.Day)))
                if q_date < QDate.currentDate():
                    raise Exception(f"Invalid Date: {q_date} Early than Today!")
                execute_day = value.get(Key.Year) + "-" + value.get(Key.Month) + "-" + value.get(Key.Day)
            case Key.Weekly:
                dates = value.get(Key.Weekly)
                if dates:
                    execute_day = ",".join(dates)
            case Key.Monthly:
                execute_day = value.get(Key.Monthly)
            case Key.Daily:
                execute_day = Key.Daily
            case Key.SmartHoliday:
                # SmartHoliday uses Daily schedule with runtime smart check,
                # we keep a placeholder value for execute_day.
                execute_day = Key.SmartHoliday
            case _:
                print(f"No match Task Trigger Type: {trigger_type}")
        return execute_day

    @staticmethod
    def parse_ui_value_to_task(value, task_id_override: str | None = None):
        create_list = []
        Log.info(f"parse system plan value: {value}")
        plan_name = value.get(Key.PlanName)
        operation = value.get(Key.Operation)
        trigger_type = value.get(Key.TriggerType)
        if not value or not trigger_type or not operation:
            return None

        task_id = task_id_override or datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")

        is_no_name = plan_name is None or plan_name == Key.Empty or plan_name == Key.DefaultSystemPlanName
        task = {
            Key.TaskName: Key.DefaultSystemPlanName if is_no_name else plan_name,
            Key.TaskID: task_id,
            Key.Operation: operation,
            Key.DayTimeType: value.get(Key.DayTimeType),
            Key.TriggerType: trigger_type,
            Key.ExecuteTime: value.get(Key.Hour) + ":" + value.get(Key.Minute)
        }

        # For SmartHoliday, record creation date (year/month/day) for runtime range checking
        if trigger_type == Key.SmartHoliday:
            task[Key.Year] = value.get(Key.Year)
            task[Key.Month] = value.get(Key.Month)
            task[Key.Day] = value.get(Key.Day)

        if task[Key.DayTimeType] == Key.Random:
            task[Key.TimeOffset] = value.get(Key.TimeOffset, 0)
            Log.info(f"Random Time Offset: {task[Key.TimeOffset]}")

        if trigger_type == Key.Multiple:
            multiple_tasks = {}
            execute_days = value.get(Key.ExecuteDays)
            for execute_day in execute_days:
                child_task = copy.deepcopy(task)
                child_task[Key.ExecuteDay] = execute_day
                child_task[Key.SystemPlanName] = UiFunc.generate_task_name(child_task)

                multiple_tasks[execute_day] = child_task[Key.SystemPlanName]
                create_list.append(child_task)
            task[Key.SystemPlanName] = multiple_tasks
        else:
            execute_day = UiFunc.generate_task_execute_day(value)
            if not execute_day: return None

            task[Key.ExecuteDay] = execute_day
            task[Key.SystemPlanName] = UiFunc.generate_task_name(task)
            create_list.append(task)

        return task, create_list