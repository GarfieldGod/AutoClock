from datetime import datetime, timedelta

from src.ui.ui_system_plan import SystemPlanDialog
from src.utils.const import Key


class EditSystemPlanDialog(SystemPlanDialog):
    def __init__(self, task: dict, parent=None):
        self._task = task if isinstance(task, dict) else {}
        super().__init__(parent)
        self.setWindowTitle("Edit System Plan")
        self._apply_task_to_ui()

    def _set_combo_text(self, combo, text: str):
        if not text:
            return
        idx = combo.findText(str(text))
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _apply_task_to_ui(self):
        task = self._task
        if not task:
            return

        self.plan_name_edit.setText(str(task.get(Key.TaskName, "")))
        self._set_combo_text(self.operation, task.get(Key.Operation, ""))

        trigger_type = str(task.get(Key.TriggerType, Key.Once))
        self._set_combo_text(self.trigger_type, trigger_type)
        self.trigger_type_changed()

        day_time_type = str(task.get(Key.DayTimeType, Key.Specify) or Key.Specify)
        self._set_combo_text(self.day_time_type, day_time_type)
        self.day_time_type_changed()

        execute_time = str(task.get(Key.ExecuteTime, ""))
        if ":" in execute_time:
            hour, minute = execute_time.split(":", 1)
            self._set_combo_text(self.hour_sel, hour.strip())
            self._set_combo_text(self.minute_sel, minute.strip())
            self._set_combo_text(self.hour_sel_start, hour.strip())
            self._set_combo_text(self.minute_sel_start, minute.strip())

        if day_time_type == Key.Random:
            offset = int(task.get(Key.TimeOffset, 0) or 0)
            try:
                start_dt = datetime.strptime(execute_time.strip(), "%H:%M") if execute_time else datetime.now()
            except Exception:
                start_dt = datetime.now()
            end_dt = start_dt + timedelta(seconds=offset)
            self._set_combo_text(self.hour_sel_end, end_dt.strftime("%H"))
            self._set_combo_text(self.minute_sel_end, end_dt.strftime("%M"))

        execute_day = str(task.get(Key.ExecuteDay, ""))
        if trigger_type == Key.Once and execute_day:
            parts = execute_day.split("-")
            if len(parts) == 3:
                year, month, day = parts
                self._set_combo_text(self.year_sel, year)
                self._set_combo_text(self.month_sel, month)
                self.month_changed()
                self._set_combo_text(self.day_sel, day)
        elif trigger_type == Key.Weekly and execute_day:
            self.weekly_day_sel.selected_dates = [d.strip() for d in execute_day.split(",") if d.strip()]
        elif trigger_type == Key.Monthly and execute_day:
            self._set_combo_text(self.monthly_day_sel, execute_day)
        elif trigger_type == Key.Multiple:
            plan_name_map = task.get(Key.SystemPlanName)
            if isinstance(plan_name_map, dict):
                self.calendar_selector.selected_dates = [d for d in plan_name_map.keys() if d]
        elif trigger_type == Key.SmartHoliday:
            self._set_combo_text(self.year_sel, task.get(Key.Year, ""))
            self._set_combo_text(self.month_sel, task.get(Key.Month, ""))
            self.month_changed()
            self._set_combo_text(self.day_sel, task.get(Key.Day, ""))
