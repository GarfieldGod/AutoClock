import sys
import os
import time
import random
import argparse
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

from src.utils.log import Log
from src.utils.utils import Utils
from src.ui.ui import ConfigWindow
from src.core.clock_manager import run_clock
from src.utils.const import Key, AppPath
from src.extend.email_server import send_email_by_result
from ui.init_ui import init_ui

# 根据操作系统选择正确的网络管理模块
system_name = os.name
if system_name == 'nt':  # Windows
    from src.extend.network_manager import disconnect_network, connect_network
else:  # Linux
    from src.extend.auto_linux_network import disconnect_network, connect_network

# 根据操作系统类型导入相应的模块
if system_name == 'nt':  # Windows
    from src.extend.auto_windows_plan import clean_invalid_windows_plan
    from src.extend.auto_windows_operation import run_windows_shutdown, run_windows_sleep
else:  # Linux和其他系统
    # 尝试导入Linux专用模块，如果不存在则使用占位符
    try:
        from src.extend.auto_linux_operation import run_linux_shutdown as run_windows_shutdown
        from src.extend.auto_linux_operation import run_linux_sleep as run_windows_sleep
        from src.extend.auto_linux_plan import clean_invalid_linux_plan as clean_invalid_windows_plan
    except ImportError:
        # 定义Linux系统的相应函数占位符
        def clean_invalid_windows_plan():
            Log.info("Linux系统清理无效计划任务")
            # 这里可以实现基本的清理逻辑
            return True, None
        
        def run_windows_shutdown(delay=30):
            Log.info(f"Linux系统执行关机操作，延迟{delay}秒")
            return True, None
        
        def run_windows_sleep(delay=30):
            Log.info(f"Linux系统执行睡眠操作，延迟{delay}秒")
            return True, None

if __name__ == '__main__':
    Log.open()

    parser = argparse.ArgumentParser(
        description="Auto-Clock - 自动打卡工具",
        epilog="更多帮助信息请参考README.md和LINUX_INSTALL_GUIDE.md文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="%(prog)s [选项]"
    )
    parser.add_argument("--task_id", help="指定要执行的任务ID")
    parser.add_argument("--headless", action="store_true", help="以无头模式运行（不显示图形界面）")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")
    
    # 添加使用示例
    parser.description = """
Auto-Clock - 自动打卡工具

使用示例:
  %(prog)s                      # 启动图形界面
  %(prog)s --task_id=12345      # 执行指定任务
  %(prog)s --headless --task_id=12345  # 以无头模式执行指定任务

注意: 在Linux环境下，如果遇到图形界面问题，请参考LINUX_INSTALL_GUIDE.md文件
"""
    
    args = parser.parse_args()

    clean_invalid_windows_plan()

    # 修复GUI启动逻辑：只有当没有任何参数时才启动GUI
    use_gui = not any(vars(args).values())
    if use_gui:
        try:
            use_old_gui = False
            if use_old_gui:
                app = QApplication(sys.argv)
                window = ConfigWindow()
                window.show()
                app.exec_()
            else:
                init_ui()
        except Exception as e:
            error_msg = str(e)
            Log.error(f"GUI启动失败: {error_msg}")
            
            # 检查是否是Qt平台插件错误
            if "qt.qpa.plugin" in error_msg or "platform plugin" in error_msg or "xcb" in error_msg:
                Log.error("检测到Qt平台插件错误，这通常是因为缺少图形界面依赖库。")
                Log.error("请参考LINUX_INSTALL_GUIDE.md文件安装必要的依赖，或使用无头模式运行。")
                Log.error("无头模式示例: python entry.py --headless --task_id=YOUR_TASK_ID")
            
            Log.info("尝试使用无头模式运行...")
            # 如果GUI启动失败，切换到无头模式
            if not args.task_id:
                Log.error("无头模式需要提供task_id参数")
                Log.error("使用 --help 参数查看所有可用选项")
                sys.exit(1)
            # 继续执行下面的任务处理代码
    else:
        # 任务模式或无头模式
        if not args.task_id and not args.headless:
            Log.error("任务模式需要提供task_id参数")
            Log.error("使用 --help 参数查看所有可用选项")
            sys.exit(1)

        config_data = Utils.read_dict_from_json(AppPath.DataJson)
        send_email_success = False
        send_email_failed = False
        email = None
        if config_data and config_data.get(Key.NotificationEmail):
            email = config_data.get(Key.NotificationEmail)
            send_email_success = config_data.get(Key.SendEmailWhenSuccess, False)
            send_email_failed = config_data.get(Key.SendEmailWhenFailed, False)

        ok = False
        error = None
        task = None
        try:
            if args.task_id:
                task = Utils.find_task(args.task_id)
                Log.info(f"Auto Clock Get Task Id: {args.task_id}")
                if not task:
                    raise Exception(f"Task ID: {args.task_id} not found.")
                operation = task.get(Key.Operation)
                day_time_type = task.get(Key.DayTimeType)
                if day_time_type and day_time_type == Key.Random:
                    time_offset = task.get(Key.TimeOffset, 0)
                    random_sec = random.randint(0, time_offset)
                    Log.info(f"将等待 {random_sec} 秒...")
                    time.sleep(random_sec)
                    Log.info("等待结束！继续执行任务")

                Log.info(f"Task ID: {args.task_id} has found, Task Name: {task.get(Key.TaskName)} Operation: {operation}")
                start_time = datetime.now()

                if operation == Key.AutoClock:
                    ok, error = run_clock()
                elif operation == Key.ShutDownWindows:
                    ok, error = run_windows_shutdown(30)
                elif operation == Key.WindowsSleep:
                    ok, error = run_windows_sleep(30)
                elif operation == Key.DisconnectNetwork:
                    # 对于断网操作，Windows和Linux都支持延迟参数
                    ok, error = disconnect_network(30)
                elif operation == Key.ConnectNetwork:
                    # 对于联网操作，通常不需要延迟
                    ok, error = connect_network()
                    # 联网后等待10秒，确保网络已经稳定连接
                    if ok:
                        Log.info("网络连接成功，等待10秒确保网络稳定...")
                        time.sleep(10)
                        Log.info("网络稳定等待完成")
                else:
                    error = f"No operation specified for: {operation}"

                end_time = datetime.now()
                elapsed_time = end_time - start_time
                elapsed_sec = elapsed_time.total_seconds()
                task[Key.CostTime] = int(elapsed_sec)
                Log.info(f"Finish Task. Start at: {start_time} End at: {end_time} Cost time: {elapsed_sec} sec")
            else:
                exit()
        except Exception as e:
            error = str(e)

        config_data = Utils.read_dict_from_json(AppPath.DataJson)
        if not config_data or not config_data.get(Key.NotificationEmail): exit()

        email = config_data.get(Key.NotificationEmail)
        send_email_success = config_data.get(Key.SendEmailWhenSuccess, False)
        send_email_failed = config_data.get(Key.SendEmailWhenFailed, False)

        if not error: error = "Unknow Error"
        Log.info(f"task: {task}")
        Log.info(f"ok: {ok} error: {error}")
        Log.info(f"email: {email} send_email_success: {send_email_success} send_email_failed: {send_email_failed}")
        
        send_email_by_result(task=task, email=email, send_email_success=send_email_success,
                             send_email_failed=send_email_failed, ok=ok, error=error)
    Log.close()
