import sys
import ctypes
import subprocess
from pathlib import Path
from datetime import datetime

from src.utils.log import Log
from src.utils.utils import Utils
from src.utils.const import Key, AppPath


def create_scheduled_task(
    task_name: str,
    task_id: str,
    trigger_type: str,
    day: str = None,
    time: str = None,
) -> bool:
    """
    创建 Windows 计划任务，自动定时运行 exe

    :param task_name: 计划任务名称（唯一）
    :param task_id: 任务ID
    :param trigger_type: 触发类型
    :param day: 执行日期
    :param time: 执行时间
    :return: 创建成功返回 True，失败返回 False
    """
    run_as_admin: bool = True
    runner_cmd = Utils.get_runner_execute_file()
    if not runner_cmd:
        raise Exception("Can't get runner execute file path.")
    operation = f'{runner_cmd} --task_id={task_id}'

    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f"{operation}".strip(),
        "/sc", trigger_type,
        "/f", # 强制覆盖同名任务
    ]

    if trigger_type == Key.Once and day is not None:
        cmd.extend(["/sd", day])

    if trigger_type in [Key.Weekly, Key.Monthly] and day is not None:
        cmd.extend(["/d", day])

    if not time or len(time.split(":")) != 2:
        raise Exception(f"Error: Invalid time format: {time} (Valid format: HH:MM, e.g., 08:30)")
    cmd.extend(["/st", time])

    if run_as_admin:
        cmd.extend(["/rl", "highest"])

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            encoding="gbk",
            errors="ignore",
            capture_output=True,
            timeout=30
        )
        Log.info(cmd)

        if result.stdout:
            Log.info(f"命令输出：{result.stdout.strip()}")
        if result.stderr:
            Log.info(f"命令警告：{result.stderr.strip()}")

        check_cmd = ["schtasks", "/query", "/tn", task_name, "/fo", "list"]
        check_result = subprocess.run(
            check_cmd, shell=True, encoding="gbk", capture_output=True
        )

        # Log.info(check_result.stdout)

        if "任务名" in check_result.stdout or result.stderr is None:
            Log.info(f"计划任务创建成功！")
            Log.info(f"任务名：{task_name}")
            Log.info(f"触发类型：{trigger_type}")
            if trigger_type in [Key.Daily, Key.Weekly]:
                Log.info(f"执行时间：{time}")
            Log.info(f"执行命令：{operation}")
            Log.info(f"管理员权限：{'是' if run_as_admin else '否'}")
            return True
        else:
            message = f"\nCreate task failed!"
            Log.error(message)
            raise Exception(message)

    except subprocess.TimeoutExpired:
        message = f"Error：Create task timeout!"
        Log.error(message)
        raise Exception(message)
    except Exception as e:
        message = f"Create task error: {str(e)}"
        Log.error(message)
        raise Exception(message)

def delete_invalid_plan(plan_dict):
    if not isinstance(plan_dict, dict): return False
    if plan_dict.get(Key.TriggerType) == Key.Once and plan_dict.get(Key.ExecuteDay) is not None:
        execute_day = plan_dict.get(Key.ExecuteDay)
        execute_date = datetime.strptime(execute_day, "%Y-%m-%d").date()
        if execute_date < datetime.today().date():
            plan_name = plan_dict.get(Key.SystemPlanName)
            Log.info(f"Plan: {plan_name} has been invalid, it will be deleted.")
            delete_scheduled_task(plan_name)
            return True

    elif plan_dict.get(Key.TriggerType) == Key.Multiple:
        deleted_day = []
        for execute_day in plan_dict.get(Key.SystemPlanName):
            execute_date = datetime.strptime(execute_day, "%Y-%m-%d").date()
            if execute_date < datetime.today().date():
                deleted_day.append(execute_day)

        for execute_day in deleted_day:
            plan_name = plan_dict.get(Key.SystemPlanName).get(execute_day)
            Log.info(f"Plan: {plan_name} has been invalid, it will be deleted.")
            delete_scheduled_task(plan_name)
            plan_dict.get(Key.SystemPlanName).pop(execute_day)

        if len(plan_dict.get(Key.SystemPlanName)) == 0:
            return True
        else:
            return False

    return False

def clean_invalid_windows_plan():
    dict_list = Utils.read_dict_from_json(AppPath.TasksJson)
    if dict_list is None: return

    if isinstance(dict_list, list):
        delete_dict = []
        for plan_dict in dict_list:
            deleted = delete_invalid_plan(plan_dict)
            if deleted:
                delete_dict.append(plan_dict)
        for deleted in delete_dict:
            dict_list.remove(deleted)
    elif isinstance(dict_list, dict):
        deleted = delete_invalid_plan(dict_list)
        if deleted:
            Utils.write_dict_to_file(AppPath.TasksJson, [])
            return

    Utils.write_dict_to_file(AppPath.TasksJson, dict_list)

def is_task_invalid(task_name: str):
    """检查任务是否失效（不存在或无法访问）"""
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name],
            shell=True, encoding="gbk", capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        # 如果返回码不为0或者输出中包含特定的错误信息，表示任务不存在或失效
        if result.returncode != 0 or "找不到指定的任务" in result.stderr or "not found" in result.stderr:
            Log.info(f"任务不存在或已失效：{task_name}")
            return True
        return False
    except Exception as e:
        # 发生异常也视为任务失效
        Log.info(f"检查任务状态时出错（视为失效）：{str(e)}")
        return True

def delete_scheduled_task(task_name: str):
    """删除计划任务"""
    try:
        # 首先检查任务是否已经失效
        if is_task_invalid(task_name):
            return True, None

        Log.info(f"Delete plan: {task_name}")
        result = subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            shell=True, encoding="gbk", capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if "成功" in result.stdout or result.returncode == 0:
            Log.info(f"已删除计划任务：{task_name}")
            return True, None
    except Exception as e:
        # 如果异常信息表明任务不存在，也视为成功
        if "找不到指定的任务" in str(e) or "not found" in str(e):
            return True, None
        message = f"Delete task error: {str(e)}"
        Log.error(message)
        return False, message

def get_task_day(target_date):
    try:
        year, month, day = target_date.split("-")
        windows_date = f"{month}/{day}/{year}"
        return windows_date
    except Exception as e:
        message = f"Invalid time format (Valid format: HH:MM, e.g., 08:30), Error: {e}"
        Log.error(message)
        raise Exception(message)

def create_task(task):
    Log.info(f"Create Windows Scheduled Task: {task}")
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            message = "No permission! Please run as an administrator!"
            Log.error(message)
            raise Exception(message)

        # 删除旧任务
        delete_scheduled_task(task.get(Key.SystemPlanName))

        ui_trigger_type = task.get(Key.TriggerType)
        ok = False
        if ui_trigger_type == Key.Once or ui_trigger_type == Key.Multiple:
            ok = create_scheduled_task(
                task_name=task.get(Key.SystemPlanName),
                task_id=task.get(Key.TaskID),
                trigger_type=Key.Once,
                day=task.get(Key.ExecuteDay),
                time=task.get(Key.ExecuteTime)
            )
        elif ui_trigger_type == Key.Daily or ui_trigger_type == Key.SmartHoliday:
            ok = create_scheduled_task(
                task_name=task.get(Key.SystemPlanName),
                task_id=task.get(Key.TaskID),
                trigger_type=Key.Daily,
                day=None,
                time=task.get(Key.ExecuteTime)
            )
        elif ui_trigger_type == Key.Weekly:
            ok = create_scheduled_task(
                task_name=task.get(Key.SystemPlanName),
                task_id=task.get(Key.TaskID),
                trigger_type=Key.Weekly,
                day=task.get(Key.ExecuteDay),
                time=task.get(Key.ExecuteTime)
            )
        elif ui_trigger_type == Key.Monthly:
            ok = create_scheduled_task(
                task_name=task.get(Key.SystemPlanName),
                task_id=task.get(Key.TaskID),
                trigger_type=Key.Monthly,
                day=task.get(Key.ExecuteDay),
                time=task.get(Key.ExecuteTime)
            )
        return ok, None
    except Exception as e:
        Log.error(f"Create task error: {str(e)}")
        delete_scheduled_task(task.get(Key.SystemPlanName))
        return False, e