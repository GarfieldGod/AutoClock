import platform
from datetime import datetime

from PyQt5.QtCore import QSize, QDate, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, \
    QDialog, QWidget, QApplication, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView

from src.ui.ui_message import MessageBox
from src.utils.const import AppPath, Key
from src.utils.log import Log
from src.utils.utils import Utils
from ui.custom.custom_function import UiFunc
from ui.custom.custom_style import get_group_css
from ui.custom.custom_widget import TaskListWidget
from ui.template.ui_page import PageContent, Container
from src.ui.ui_system_plan import SystemPlanDialog
from src.ui.ui_system_plan_edit import EditSystemPlanDialog
from src.utils.const import WebPath

# 根据操作系统导入相应的模块
if platform.system() == 'Windows':
    from src.ui.ui_windows_login import WindowsLoginDialog
    from src.extend.auto_windows_plan import create_task, delete_scheduled_task
    from src.extend.network_manager import connect_network, disconnect_network
elif platform.system() == 'Linux':
    from src.ui.ui_linux_login import LinuxLoginDialog
    from src.extend.auto_linux_plan import create_crontab_task, delete_crontab_task
    from src.extend.auto_linux_network import connect_network, disconnect_network
else:
    # 其他系统暂不支持特定功能
    pass


class SystemTaskPage(PageContent):
    # show_grid = True
    def __init__(self, y, x):
        super(SystemTaskPage, self).__init__(y, x)

    def init_container(self):
        task = TaskListContainer(6, 4)
        self.add_container(task, 0,0)

        login = SystemLoginContainer(2,2)
        self.add_container(login, 4,0)

        if platform.system() == 'Linux':
            nettest = NetWorkTestContainer(2,2)
            self.add_container(nettest, 4,2)

class TaskListContainer(Container):
    def __init__(self, x, y):
        super(TaskListContainer, self).__init__(x, y)

        self.task_list = []
        self.system_plan_list = QTableWidget()
        self.button_create = QPushButton("Create")
        self.button_delete = QPushButton("Delete")
        self.button_refresh = QPushButton("Refresh Result")

        self.init_ui_layout()
        self.update_plan_list()

    def _get_cfg(self, key, default=None):
        try:
            w = self.window()
            if hasattr(w, "get_save_data"):
                return w.get_save_data(key, default)
        except Exception:
            pass
        return default

    @staticmethod
    def _error_text(error, default: str) -> str:
        text = str(error or "").strip()
        return text if text else default

    def _normalize_task(self, task: dict) -> tuple[dict, bool]:
        changed = False
        if Key.Enabled not in task:
            task[Key.Enabled] = True
            changed = True
        if Key.LastRunResult not in task:
            task[Key.LastRunResult] = "-"
            changed = True
        return task, changed

    def _read_tasks(self):
        try:
            w = self.window()
            if hasattr(w, "read_tasks_list"):
                return w.read_tasks_list()
        except Exception:
            pass
        return Utils.read_dict_from_json(AppPath.TasksJson)

    def _write_tasks(self, tasks) -> bool:
        try:
            w = self.window()
            if hasattr(w, "write_tasks_list"):
                return bool(w.write_tasks_list(tasks))
        except Exception:
            pass
        try:
            Utils.write_dict_to_file(AppPath.TasksJson, tasks)
            return True
        except Exception:
            return False

    def _get_remote_plan_service(self):
        try:
            w = self.window()
            if hasattr(w, "remote_plan_service"):
                return w.remote_plan_service
        except Exception:
            pass
        return None

    def _read_config(self) -> dict:
        try:
            w = self.window()
            if hasattr(w, "data_store") and hasattr(w.data_store, "read_config"):
                data = w.data_store.read_config()
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
        try:
            data = Utils.read_dict_from_json(AppPath.DataJson)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_config(self, config: dict) -> bool:
        try:
            w = self.window()
            if hasattr(w, "data_store") and hasattr(w.data_store, "write_config"):
                return bool(w.data_store.write_config(config))
        except Exception:
            pass
        try:
            Utils.write_dict_to_file(AppPath.DataJson, config)
            return True
        except Exception:
            return False

    @staticmethod
    def _is_compact_screen() -> bool:
        try:
            app = QApplication.instance()
            if app is None:
                return False
            screen = app.primaryScreen()
            if screen is None:
                return False
            return int(screen.availableGeometry().width()) <= 1366
        except Exception:
            return False

    def init_ui_layout(self):
        TaskListWidget.set_compact(self._is_compact_screen())

        group_system = QGroupBox(f"System Plan List")
        group_system.setStyleSheet(get_group_css({}))
        layout_system = QVBoxLayout(group_system)

        self.system_plan_list.setColumnCount(7)
        self.system_plan_list.setHorizontalHeaderLabels([
            "Task Name", "Operation", "Trigger", "Time", "Schedule", "Result", "Status"
        ])
        self.system_plan_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.system_plan_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.system_plan_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.system_plan_list.setAlternatingRowColors(False)
        self.system_plan_list.setShowGrid(False)
        self.system_plan_list.setWordWrap(False)
        self.system_plan_list.setCornerButtonEnabled(False)
        self.system_plan_list.verticalHeader().setVisible(False)
        self.system_plan_list.verticalHeader().setDefaultSectionSize(34)
        self.system_plan_list.horizontalHeader().setStretchLastSection(False)
        self.system_plan_list.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.system_plan_list.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.system_plan_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.system_plan_list.setStyleSheet(
            "QTableWidget { border: 1px solid #d1d5db; border-radius: 6px; background: white; }"
            "QHeaderView::section { background: white; color: black; border: none; border-bottom: 1px solid #d1d5db; padding: 6px 8px; font-size: 10pt; text-align: left; }"
            "QTableWidget::item { padding: 4px 8px; }"
        )
        self.system_plan_list.setColumnWidth(0, TaskListWidget.COL_TASK)
        self.system_plan_list.setColumnWidth(1, TaskListWidget.COL_OPERATION)
        self.system_plan_list.setColumnWidth(2, TaskListWidget.COL_TRIGGER)
        self.system_plan_list.setColumnWidth(3, TaskListWidget.COL_TIME)
        self.system_plan_list.setColumnWidth(4, TaskListWidget.COL_SCHEDULE)
        self.system_plan_list.setColumnWidth(5, TaskListWidget.COL_RESULT)
        self.system_plan_list.setColumnWidth(6, TaskListWidget.COL_STATUS)
        layout_system.addWidget(self.system_plan_list)

        layout_plan_list_buttons = QHBoxLayout()
        layout_plan_list_buttons.addWidget(self.button_create)
        layout_plan_list_buttons.addWidget(self.button_delete)
        layout_plan_list_buttons.addWidget(self.button_refresh)
        layout_system.addLayout(layout_plan_list_buttons)

        self.button_create.clicked.connect(self.create_system_plan)
        self.button_delete.clicked.connect(self.delete_system_plan)
        self.button_refresh.clicked.connect(self.refresh_last_results)
        self.system_plan_list.cellDoubleClicked.connect(self.edit_system_plan)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def _create_plan_tasks(self, task_list_to_create):
        for task in task_list_to_create:
            try:
                if platform.system() == "Windows":
                    w = self.window()
                    if hasattr(w, "is_remote_connected") and w.is_remote_connected():
                        svc = self._get_remote_plan_service()
                        if svc is None:
                            return False, "远端服务未初始化，请重新连接SSH"
                        ok, error = svc.cron_create(task)
                    else:
                        ok, error = create_task(task)
                elif platform.system() == "Linux":
                    ok, error = create_crontab_task(task)
                else:
                    return False, "System not supported"
            except Exception as e:
                return False, self._error_text(e, "Create plan failed")

            if error or not ok:
                return False, self._error_text(error, "Create plan failed")
        return True, None

    def _delete_plan_task(self, task):
        plan_name = task[Key.SystemPlanName]

        try:
            if platform.system() == "Windows":
                w = self.window()
                if hasattr(w, "is_remote_connected") and w.is_remote_connected():
                    svc = self._get_remote_plan_service()
                    if svc is None:
                        return False, "远端服务未初始化，请重新连接SSH"

                    names = svc.task_names_from_plan(task)
                    ok, error = svc.cron_delete(names)
                else:
                    if task[Key.TriggerType] == Key.Multiple and isinstance(plan_name, dict):
                        for task_name in plan_name:
                            ok, error = delete_scheduled_task(plan_name.get(task_name))
                            if not ok:
                                return False, self._error_text(error, "Delete plan failed")
                    else:
                        ok, error = delete_scheduled_task(plan_name)
                        if not ok:
                            return False, self._error_text(error, "Delete plan failed")
            elif platform.system() == "Linux":
                if task[Key.TriggerType] == Key.Multiple and isinstance(plan_name, dict):
                    for task_name in plan_name:
                        ok, error = delete_crontab_task(plan_name.get(task_name))
                        if not ok:
                            return False, self._error_text(error, "Delete plan failed")
                else:
                    ok, error = delete_crontab_task(plan_name)
                    if not ok:
                        return False, self._error_text(error, "Delete plan failed")
            else:
                return False, "System not supported"
        except Exception as e:
            return False, self._error_text(e, "Delete plan failed")

        return True, None

    def _find_task_by_plan_id(self, plan_id):
        for index, task in enumerate(self.task_list):
            if task[Key.TaskID] == plan_id:
                return index, task
        return -1, None

    def _plan_id_for_row(self, row):
        try:
            if row is None or row < 0 or row >= len(self.task_list):
                return None
            return str(self.task_list[row].get(Key.TaskID, "") or "")
        except Exception:
            return None

    @staticmethod
    def _schedule_text(task):
        if task[Key.TriggerType] in [Key.Once, Key.Weekly, Key.Monthly]:
            return str(task.get(Key.ExecuteDay, "") or "")
        if task[Key.TriggerType] == Key.SmartHoliday:
            return "Smart"
        if task[Key.TriggerType] == Key.Multiple:
            return "[Multiple]"
        return "Daily"

    def check_linux_credentials(self):
        try:
            credentials_valid = False
            max_attempts = 3
            attempt = 0

            while not credentials_valid and attempt < max_attempts:
                # 检查当前账号状态
                login_dlg = LinuxLoginDialog(self)

                # 如果是第一次尝试，先检查是否已有有效配置
                if attempt == 0:
                    is_valid, status_msg = login_dlg.get_credentials_status()
                    if is_valid:
                        credentials_valid = True
                        break

                # 显示登录对话框要求用户配置或验证账号
                if login_dlg.exec_() == QDialog.Accepted:
                    is_valid, status_msg = login_dlg.get_credentials_status()
                    if is_valid:
                        credentials_valid = True
                        break
                    else:
                        # 账号无效，询问是否重试
                        retry = MessageBox(f"账号验证失败：{status_msg}\n\n是否重新配置账号信息？", "账号验证失败",
                                           buttons=["重试", "取消"])
                        if retry != "重试":
                            return False
                else:
                    # 用户取消了登录对话框
                    return False

                attempt += 1

            if not credentials_valid:
                MessageBox("账号验证失败次数过多，无法创建任务。请确保Linux账号配置正确后重试。")
                return False

            return True
        except Exception as e:
            message = self._error_text(e, "Edit task failed")
            Log.error(message)
            MessageBox(message)
            return False

    def create_system_plan(self):
        if platform.system() == 'Linux':
            # 如果当前Linux账号配置已有效，则不再弹出提示，直接创建计划
            try:
                login_dlg = LinuxLoginDialog(self)
                is_valid, _ = login_dlg.get_credentials_status()
            except Exception as e:
                Log.error(str(e))
                is_valid = False

            if not is_valid:
                try:
                    config = self._read_config() or {}
                except Exception as e:
                    Log.error(str(e))
                    config = {}

                need_check = config.get(Key.CheckLinuxCredentialsOnPlanCreate, True)

                if need_check:
                    choice = MessageBox(
                        "建议先配置并验证Linux账号与自动登录，以确保计划任务执行后能够自动登录系统。\n\n"
                        "请选择下一步操作：",
                        "Linux账号配置提示",
                        buttons=["去配置并验证", "直接创建", "不再提示"],
                    )

                    if choice == "去配置并验证":
                        if not self.check_linux_credentials():
                            return
                    elif choice == "不再提示":
                        config[Key.CheckLinuxCredentialsOnPlanCreate] = False
                        try:
                            self._write_config(config)
                        except Exception as e:
                            Log.error(str(e))
                    # "直接创建" 以及 "不再提示" 最终都继续创建计划

        task = self.do_create_plan()

        if task is None: return
        self.task_list.append(task)
        if not self._write_tasks(self.task_list):
            MessageBox("Save tasks failed")
            return
        self.update_plan_list()

    def do_create_plan(self):
        try:
            plan_ui = SystemPlanDialog(self)
            if plan_ui.exec_() == QDialog.Accepted:
                value = plan_ui.values()
                task_to_json, task_list_to_create = UiFunc.parse_ui_value_to_task(value)
                ok, error = self._create_plan_tasks(task_list_to_create)
                if not ok:
                    raise Exception(error or "Create task failed")

                task_to_json[Key.Enabled] = True
                task_to_json[Key.LastRunResult] = "-"

                MessageBox(f"Create Task: {task_to_json[Key.TaskName]} Success!")
                Log.info(f"create system plan task: {task_to_json}")

                return task_to_json
        except Exception as e:
            message = self._error_text(e, "Create task failed")
            Log.error(message)
            MessageBox(message)
            return None

    def edit_system_plan(self, row, _column=0):
        try:
            if row is None or row < 0:
                return
            plan_id = self._plan_id_for_row(row)
            task_index, old_task = self._find_task_by_plan_id(plan_id)
            if old_task is None:
                raise Exception(f"Edit plan failed, no plan id: {plan_id}")

            edit_dlg = EditSystemPlanDialog(old_task, self)
            if edit_dlg.exec_() != QDialog.Accepted:
                return

            value = edit_dlg.values()
            parsed = UiFunc.parse_ui_value_to_task(value, task_id_override=old_task.get(Key.TaskID))
            if not parsed:
                raise Exception("Edit plan failed, invalid plan data")

            task_to_json, task_list_to_create = parsed
            task_to_json[Key.Enabled] = bool(old_task.get(Key.Enabled, True))
            task_to_json[Key.LastRunResult] = str(old_task.get(Key.LastRunResult, "-") or "-")
            ok, error = self._delete_plan_task(old_task)
            if not ok:
                raise Exception(error or "Delete old task failed")

            ok, error = self._create_plan_tasks(task_list_to_create)
            if not ok:
                raise Exception(error or "Create new task failed")

            self.task_list[task_index] = task_to_json
            if not self._write_tasks(self.task_list):
                raise Exception("Save tasks failed")
            self.update_plan_list()
            MessageBox(f"Edit Task: {task_to_json[Key.TaskName]} Success!")
        except Exception as e:
            Log.error(str(e))
            MessageBox(str(e))

    def delete_system_plan(self):
        try:
            current_row = self.system_plan_list.currentRow()
            if current_row is None or current_row < 0:
                MessageBox("请选择要删除的计划任务")
                return

            plan_id = self._plan_id_for_row(current_row)
            Log.info(f"删除Plan: {plan_id}")

            _, delete_task = self._find_task_by_plan_id(plan_id)
            if delete_task is None:
                raise Exception(f"Delete plan failed, no plan id: {plan_id}")
            short_name = delete_task[Key.TaskName]

            dlg = MessageBox(f"\nAre you really want to delete this Plan:\n\n{short_name}\n", need_check=True, message_only=False, message_name="Delete Plan")
            if dlg.exec_() != QDialog.Accepted:
                return

            ok, error = self._delete_plan_task(delete_task)
            if not ok:
                raise Exception(error or "Delete plan failed")

            self.task_list.remove(delete_task)
            if not self._write_tasks(self.task_list):
                raise Exception("Save tasks failed")
            self.update_plan_list()

        except Exception as e:
            message = self._error_text(e, "Delete plan failed")
            Log.error(message)
            MessageBox(message)

    def toggle_system_plan_enabled(self, plan_id=None, enabled=None):
        try:
            if not plan_id:
                current_row = self.system_plan_list.currentRow()
                if current_row is None or current_row < 0:
                    MessageBox("Please select one task")
                    return False
                plan_id = self._plan_id_for_row(current_row)

            task_index, task = self._find_task_by_plan_id(plan_id)
            if task is None or task_index < 0:
                raise Exception(f"Task not found: {plan_id}")

            if enabled is None:
                new_enabled = not bool(task.get(Key.Enabled, True))
            else:
                new_enabled = bool(enabled)

            self.task_list[task_index][Key.Enabled] = new_enabled
            if not self._write_tasks(self.task_list):
                raise Exception("Save task status failed")

            self.update_plan_list()
            if enabled is None:
                MessageBox(f"Task status updated: {'ON' if new_enabled else 'OFF'}")
            return True
        except Exception as e:
            message = self._error_text(e, "Update task status failed")
            Log.error(message)
            MessageBox(message)
            return False

    def update_plan_list(self):
        try:
            dict_list = self._read_tasks()
            if dict_list is None: return

            self.system_plan_list.setRowCount(0)
            self.task_list = []
            changed = False
            if isinstance(dict_list, list):
                for plan_dict in dict_list:
                    if not isinstance(plan_dict, dict):
                        continue
                    normalized_task, task_changed = self._normalize_task(plan_dict)
                    self.task_list.append(normalized_task)
                    changed = changed or task_changed
                    self.add_plan_ui(normalized_task)
            elif isinstance(dict_list, dict):
                normalized_task, changed = self._normalize_task(dict_list)
                self.task_list.append(normalized_task)
                self.add_plan_ui(normalized_task)
            else:
                raise Exception("Load tasks failed!")

            if changed:
                self._write_tasks(self.task_list)

        except Exception as e:
            message = f"Update windows plan list failed: {e}"
            Log.error(message)
            MessageBox(message)

    def add_plan_ui(self, task):
        row = self.system_plan_list.rowCount()
        self.system_plan_list.insertRow(row)

        values = [
            str(task.get(Key.TaskName, "") or ""),
            str(task.get(Key.Operation, "") or ""),
            str(task.get(Key.TriggerType, "") or ""),
            str(task.get(Key.ExecuteTime, "") or ""),
            self._schedule_text(task),
            str(task.get(Key.LastRunResult, "-") or "-"),
        ]

        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item.setToolTip(value)
            self.system_plan_list.setItem(row, col, item)

        status_button = QPushButton()
        status_button.setCheckable(True)
        status_on = bool(task.get(Key.Enabled, True))
        status_button.setChecked(status_on)
        status_button.setFixedWidth(52)
        if status_on:
            status_button.setText("ON")
            status_button.setStyleSheet(
                "QPushButton {background-color: #16a34a; color: white; border: 1px solid #15803d;"
                "border-radius: 10px; padding: 2px 6px; font-weight: 600;}"
            )
        else:
            status_button.setText("OFF")
            status_button.setStyleSheet(
                "QPushButton {background-color: #6b7280; color: white; border: 1px solid #4b5563;"
                "border-radius: 10px; padding: 2px 6px; font-weight: 600;}"
            )
        plan_id = str(task.get(Key.TaskID, "") or "")
        status_button.clicked.connect(
            lambda checked, pid=plan_id: self.toggle_system_plan_enabled(pid, checked)
        )

        holder = QWidget()
        holder_layout = QHBoxLayout(holder)
        holder_layout.setContentsMargins(8, 0, 8, 0)
        holder_layout.setSpacing(0)
        holder_layout.addWidget(status_button, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.system_plan_list.setCellWidget(row, 6, holder)

    def refresh_last_results(self):
        try:
            self.update_plan_list()
        except Exception as e:
            message = self._error_text(e, "Refresh last results failed")
            Log.error(message)
            MessageBox(message)

class SystemLoginContainer(Container):
    def __init__(self, x, y):
        super(SystemLoginContainer, self).__init__(x, y)

        self.set_auto_login = QPushButton("System Auto Login")

        self.init_ui_layout()

    def init_ui_layout(self):
        system_name = platform.system()
        group_system = QGroupBox(f"Auto Login")
        group_system.setStyleSheet(get_group_css({}))
        layout_system = QVBoxLayout(group_system)

        self.set_auto_login.clicked.connect(self.auto_system_login)

        if system_name == 'Linux':
            tip_label = QLabel("提示：Linux自动登录功能需要管理员权限运行应用")
            tip_label.setStyleSheet("color: orange; font-size: 12px;")
            tip_label.setWordWrap(True)
            layout_system.addWidget(tip_label)

        layout_system.addWidget(self.set_auto_login)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def auto_system_login(self):
        dlg = None
        if platform.system() == 'Linux':
            dlg = LinuxLoginDialog(self)
        elif platform.system() == 'Windows':
            dlg = WindowsLoginDialog(self)

        if dlg is not None:
            dlg.exec_()

class NetWorkTestContainer(Container):
    def __init__(self, x, y):
        super(NetWorkTestContainer, self).__init__(x, y)

        self.button_disconnect_network = QPushButton("立即断网")
        self.button_connect_network = QPushButton("立即联网")

        self.init_ui_layout()

    def init_ui_layout(self):
        self.button_disconnect_network.clicked.connect(self.disconnect_network_now)
        self.button_connect_network.clicked.connect(self.connect_network_now)

        group_system = QGroupBox(f"Test Network")
        group_system.setStyleSheet(get_group_css({}))

        net_layout = QHBoxLayout(group_system)
        net_layout.addWidget(self.button_disconnect_network)
        net_layout.addWidget(self.button_connect_network)

        layout_container = QVBoxLayout(self)
        layout_container.addWidget(group_system)

    def disconnect_network_now(self):
        try:
            # 检查网络管理功能是否可用
            if disconnect_network is None:
                MessageBox("Network management is not supported on this platform")
                return

            success, error = disconnect_network()
            if success:
                MessageBox("Network disconnected successfully!")
            else:
                MessageBox(f"Failed to disconnect network: {error}")
        except Exception as e:
            MessageBox(f"Error disconnecting network: {str(e)}")

    def connect_network_now(self):
        try:
            # 检查网络管理功能是否可用
            if connect_network is None:
                MessageBox("Network management is not supported on this platform")
                return

            success, error = connect_network()
            if success:
                MessageBox("Network connected successfully!")
            else:
                MessageBox(f"Failed to connect network: {error}")
        except Exception as e:
            MessageBox(f"Error connecting network: {str(e)}")


