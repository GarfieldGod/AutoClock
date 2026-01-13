import os
import re
import sys
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from src.utils.log import Log
from src.utils.utils import Utils
from src.utils.const import Key, AppPath


def get_crontab_content():
    """
    获取当前用户的crontab内容
    """
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')
        elif result.returncode == 1 and 'no crontab for' in result.stderr:
            # 用户没有crontab文件
            return []
        else:
            Log.error(f"获取crontab内容失败: {result.stderr}")
            return []
    except Exception as e:
        Log.error(f"获取crontab内容时出错: {str(e)}")
        return []


def set_crontab_content(entries):
    """
    设置用户的crontab内容
    """
    try:
        # 创建临时文件存储crontab内容
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            for entry in entries:
                if entry.strip():
                    temp_file.write(entry + '\n')
            temp_file_path = temp_file.name
        
        # 使用crontab命令设置内容
        result = subprocess.run(['crontab', temp_file_path], capture_output=True, text=True)
        os.unlink(temp_file_path)  # 删除临时文件
        
        if result.returncode == 0:
            Log.info("Crontab设置成功")
            return True, None
        else:
            Log.error(f"Crontab设置失败: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        Log.error(f"设置crontab内容时出错: {str(e)}")
        return False, str(e)


def create_crontab_entry(task_name, task_id, trigger_type, day=None, time=None):
    """
    创建crontab条目
    
    :param task_name: 任务名称
    :param task_id: 任务ID
    :param trigger_type: 触发类型
    :param day: 执行日期
    :param time: 执行时间
    :return: crontab条目字符串
    """
    # 获取执行文件路径
    exe_path = Utils.get_execute_file()
    if not exe_path:
        raise Exception("无法获取执行文件路径")

    # 构建crontab执行命令，设置必要的环境变量
    home_dir = os.path.expanduser("~")
    path_env = os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
    user = os.environ.get('USER', os.environ.get('LOGNAME', 'user'))
    
    # 构建完整的命令，包含环境变量设置
    command = f'PATH={path_env} HOME={home_dir} USER={user} DISPLAY=:1 {exe_path} --task_id={task_id}'
    
    # 解析时间
    try:
        hour, minute = time.split(':')
        hour = int(hour)
        minute = int(minute)
    except (ValueError, TypeError):
        raise Exception(f"无效的时间格式: {time} (有效格式: HH:MM, 例如 08:30)")
    
    # 创建crontab表达式
    comment = f"# auto-clock: {task_name}"
    
    if trigger_type == Key.Once and day:
        # 一次性任务
        year, month, day_of_month = map(int, day.split('-'))
        # 添加任务信息作为注释，crontab不直接支持一次性任务
        # 我们会通过清理机制移除过期任务
        cron_expr = f"{minute} {hour} {day_of_month} {month} * {command}"
    elif trigger_type == Key.Daily or trigger_type == Key.SmartHoliday:
        # 每日任务
        cron_expr = f"{minute} {hour} * * * {command}"
    elif trigger_type == Key.Weekly and day:
        # 每周任务
        # 转换星期几为crontab格式 (0=周日, 1=周一, ..., 6=周六)
        week_map = {
            'Mon': '1', 'Tue': '2', 'Wed': '3',
            'Thu': '4', 'Fri': '5', 'Sat': '6', 'Sun': '0',
            'Monday': '1', 'Tuesday': '2', 'Wednesday': '3',
            'Thursday': '4', 'Friday': '5', 'Saturday': '6', 'Sunday': '0'
        }
        
        # 支持多个星期几(逗号分隔)
        if ',' in day:
            days = [d.strip() for d in day.split(',')]
            cron_days = []
            for d in days:
                if d.isdigit():
                    cron_days.append(d)
                else:
                    cron_day = week_map.get(d.capitalize(), week_map.get(d, d))
                    cron_days.append(cron_day)
            cron_expr = f"{minute} {hour} * * {','.join(cron_days)} {command}"
        # 支持单个星期几
        elif day.isdigit():
            cron_expr = f"{minute} {hour} * * {day} {command}"
        else:
            cron_day = week_map.get(day.capitalize(), week_map.get(day, day))
            cron_expr = f"{minute} {hour} * * {cron_day} {command}"
    elif trigger_type == Key.Monthly and day:
        # 每月任务
        cron_expr = f"{minute} {hour} {day} * * {command}"
    else:
        raise Exception(f"不支持的触发类型: {trigger_type}")
    
    return [comment, cron_expr]


def create_scheduled_task(task_name, task_id, trigger_type, day=None, time=None):
    """
    创建Linux计划任务（crontab）
    
    :param task_name: 任务名称
    :param task_id: 任务ID
    :param trigger_type: 触发类型
    :param day: 执行日期
    :param time: 执行时间
    :return: 创建成功返回True，失败返回False
    """
    try:
        # 获取当前crontab内容
        crontab_entries = get_crontab_content()
        
        # 移除同名任务
        new_entries = []
        task_comment = f"# auto-clock: {task_name}"
        skip_next = False
        
        for i, entry in enumerate(crontab_entries):
            if skip_next:
                skip_next = False
                continue
            
            if task_comment in entry:
                # 找到任务注释，跳过注释行和命令行
                skip_next = True
                Log.info(f"移除旧任务: {task_name}")
            else:
                new_entries.append(entry)
        
        # 创建新任务条目
        task_entries = create_crontab_entry(task_name, task_id, trigger_type, day, time)
        new_entries.extend(task_entries)
        
        # 设置新的crontab内容
        success, error = set_crontab_content(new_entries)
        if success:
            Log.info(f"计划任务创建成功！")
            Log.info(f"任务名：{task_name}")
            Log.info(f"触发类型：{trigger_type}")
            if trigger_type in [Key.Daily, Key.Weekly]:
                Log.info(f"执行时间：{time}")
            Log.info(f"执行命令：{task_entries[1]}")
            return True
        else:
            raise Exception(f"创建任务失败: {error}")
            
    except Exception as e:
        message = f"创建任务错误: {str(e)}"
        Log.error(message)
        raise Exception(message)


def delete_scheduled_task(task_name):
    """
    删除Linux计划任务
    
    :param task_name: 任务名称
    :return: (是否成功, 错误信息)
    """
    try:
        # 获取当前crontab内容
        crontab_entries = get_crontab_content()
        
        # 检查任务是否存在
        task_comment = f"# auto-clock: {task_name}"
        task_exists = any(task_comment in entry for entry in crontab_entries)
        
        if not task_exists:
            Log.info(f"任务不存在或已删除：{task_name}")
            return True, None
        
        # 移除任务
        new_entries = []
        skip_next = False
        
        for entry in crontab_entries:
            if skip_next:
                skip_next = False
                continue
            
            if task_comment in entry:
                # 找到任务注释，跳过注释行和命令行
                skip_next = True
                Log.info(f"删除任务: {task_name}")
            else:
                new_entries.append(entry)
        
        # 设置新的crontab内容
        success, error = set_crontab_content(new_entries)
        if success:
            Log.info(f"已删除计划任务：{task_name}")
            return True, None
        else:
            Log.error(f"删除任务失败: {error}")
            return False, error
            
    except Exception as e:
        message = f"删除任务错误: {str(e)}"
        Log.error(message)
        return False, message


def delete_invalid_plan(plan_dict):
    """
    删除无效的计划任务（过期的一次性任务）
    """
    if not isinstance(plan_dict, dict):
        return False
    
    if plan_dict.get(Key.TriggerType) == Key.Once and plan_dict.get(Key.ExecuteDay):
        execute_day = plan_dict.get(Key.ExecuteDay)
        execute_date = datetime.strptime(execute_day, "%Y-%m-%d").date()
        if execute_date < datetime.today().date():
            plan_name = plan_dict.get(Key.SystemPlanName)
            Log.info(f"计划任务已过期：{plan_name}，将被删除")
            delete_scheduled_task(plan_name)
            return True
    
    # 对于Multiple类型的任务，Linux使用不同的处理方式
    # 我们可以在这里添加相应的逻辑
    
    return False


def clean_invalid_linux_plan():
    """
    清理无效的Linux计划任务
    检查所有已创建的crontab任务，如果对应的任务ID在本地任务列表中不存在，则删除
    :return: (是否成功, 错误信息)
    """
    try:
        Log.info("开始清理无效的Linux计划任务")
        
        # 获取本地任务列表
        tasks_dict = Utils.read_dict_from_json(AppPath.TasksJson)
        if tasks_dict is None:
            tasks_dict = []
        
        # 提取所有有效的任务ID
        valid_task_ids = set()
        for task in tasks_dict:
            if isinstance(task, dict) and Key.TaskID in task:
                valid_task_ids.add(task[Key.TaskID])
        
        # 使用已有的辅助函数获取crontab内容
        crontab_entries = get_crontab_content()
        if not crontab_entries:
            Log.info("没有找到crontab任务")
            return True, None
        
        # 检查每一行，删除无效的任务
        clean_entries = []
        removed_count = 0
        
        i = 0
        while i < len(crontab_entries):
            entry = crontab_entries[i].strip()
            
            # 跳过空行
            if not entry:
                clean_entries.append(entry)
                i += 1
                continue
                
            # 检查是否是auto-clock任务的注释行（使用与create_scheduled_task相同的格式）
            if entry.startswith('# auto-clock:'):
                # 检查下一行是否是实际的crontab条目
                if i + 1 < len(crontab_entries):
                    next_entry = crontab_entries[i + 1].strip()
                    if next_entry and not next_entry.startswith('#') and 'task_id=' in next_entry:
                        # 提取task_id
                        task_id_start = next_entry.find('task_id=') + len('task_id=')
                        task_id_end = next_entry.find(' ', task_id_start)
                        if task_id_end == -1:
                            task_id_end = len(next_entry)
                        task_id = next_entry[task_id_start:task_id_end]
                        
                        # 检查任务ID是否有效
                        if task_id in valid_task_ids:
                            # 保留有效的任务
                            clean_entries.append(entry)
                            clean_entries.append(next_entry)
                        else:
                            # 删除无效的任务
                            Log.info(f"删除无效的Linux计划任务，TaskID: {task_id}")
                            removed_count += 1
                        i += 2  # 跳过注释行和任务行
                        continue
                
                # 如果没有对应的任务行，保留注释行
                clean_entries.append(entry)
            else:
                # 保留非auto-clock的任务
                clean_entries.append(entry)
            
            i += 1
        
        # 如果有删除的任务，更新crontab
        if removed_count > 0:
            # 使用已有的辅助函数设置crontab内容
            success, error = set_crontab_content(clean_entries)
            if success:
                Log.info(f"已清理 {removed_count} 个无效的Linux计划任务")
            else:
                raise Exception(f"更新crontab失败: {error}")
        else:
            Log.info("没有发现无效的Linux计划任务")
        
        return True, None
    except Exception as e:
        Log.error(f"清理无效Linux计划任务失败: {str(e)}")
        return False, str(e)


def create_crontab_task(task):
    """
    创建Linux crontab任务
    
    :param task: 任务配置字典
    :return: (是否成功, 错误信息)
    """
    try:
        # 获取任务参数
        task_name = task.get(Key.SystemPlanName)
        task_id = task.get(Key.TaskID)
        trigger_type = task.get(Key.TriggerType)
        execute_day = task.get(Key.ExecuteDay)
        execute_time = task.get(Key.ExecuteTime)
        
        if not task_name or not task_id or not trigger_type or not execute_time:
            return False, "任务参数不完整"
        
        # 调用现有的create_scheduled_task函数
        success = create_scheduled_task(
            task_name=task_name,
            task_id=task_id,
            trigger_type=trigger_type,
            day=execute_day,
            time=execute_time
        )
        
        if success:
            return True, None
        else:
            return False, "创建crontab任务失败"
            
    except Exception as e:
        error_msg = f"创建crontab任务错误: {str(e)}"
        Log.error(error_msg)
        return False, error_msg


def delete_crontab_task(task_name):
    """
    删除Linux crontab任务
    
    :param task_name: 任务名称
    :return: (是否成功, 错误信息)
    """
    try:
        # 调用现有的delete_scheduled_task函数
        success, error = delete_scheduled_task(task_name)
        
        if success:
            return True, None
        else:
            return False, error
            
    except Exception as e:
        error_msg = f"删除crontab任务错误: {str(e)}"
        Log.error(error_msg)
        return False, error_msg


def create_task(task):
    """
    创建Linux计划任务
    
    :param task: 任务配置字典
    :return: (是否成功, 错误信息)
    """
    Log.info(f"创建Linux计划任务: {task}")
    try:
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
        Log.error(f"创建任务错误: {str(e)}")
        delete_scheduled_task(task.get(Key.SystemPlanName))
        return False, e