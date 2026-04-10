import os
import sys
from pathlib import Path
from dataclasses import dataclass

from platformdirs import user_data_dir


@dataclass
class Key:
    TaskName: str = "task_name"
    TaskID: str = "task_id"
    TriggerType: str = "trigger_type"
    DayTimeType: str = "day_time_type"
    Operation: str = "operation"
    # 用户输入的计划名称（用于展示/生成系统计划任务名的前缀）
    PlanName: str = "plan_name"
    # 系统侧真实的计划任务名称（Windows TaskScheduler / Linux crontab 标识）
    SystemPlanName: str = "system_plan_name"
    ExecuteTime: str = "execute_time"
    ExecuteDay: str = "execute_day"
    ExecuteDays: str = "execute_days"

    Year: str = "year"
    Month: str = "month"
    Day: str = "day"
    Hour: str = "hour"
    Minute: str = "minute"
    HourOffSet: str = "hour_offset"
    MinuteOffSet: str = "minute_offset"
    TimeOffset: str = "time_offset"
    CostTime: str = "cost_time"

    Once: str = "Once"
    Multiple: str = "Multiple"
    Daily: str = "Daily"
    Weekly: str = "Weekly"
    Monthly: str = "Monthly"
    SmartHoliday: str = "SmartHoliday"

    Random: str = "Random"
    Specify: str = "Specify"

    NotificationEmail: str = "notification_email"
    SendEmailWhenSuccess: str = "send_email_success"
    SendEmailWhenFailed: str = "send_email_failed"

    UserName: str = "user_name"
    UserPassword: str = "user_password"
    DriverPath: str = "driver_path"
    CaptchaRetryTimes: str = "captcha_retry_times"
    CaptchaToleranceAngle: str = "captcha_tolerance_angle"
    AlwaysRetry: str = "always_retry"
    ShowWebPage: str = "show_web_page"

    AutoClock: str = "Auto Clock"
    ShutDownSystem: str = "Shut Down"
    SystemSleep: str = "Sleep"
    # 新增断网和联网操作类型
    DisconnectNetwork: str = "Disconnect Network"
    ConnectNetwork: str = "Connect Network"

    DefaultSystemPlanName: str = "AutoClock_System_Plan"
    DefaultLinuxPlanName: str = "AutoClock_Linux_Plan"
    Unknown: str = "Unknown"
    Empty: str = ""
    LinuxUserName: str = "LinuxUserName"
    CheckLinuxCredentialsOnPlanCreate: str = "check_linux_credentials_on_plan_create"

@dataclass
class AppPath:
    if sys.platform.startswith('win'):
        # Windows: C:/Users/${username}/AppData/Local/auto-clock
        LogRoot = user_data_dir("log", "auto-clock")
        DataRoot = user_data_dir("data", "auto-clock")
        BackupRoot = user_data_dir("backup", "auto-clock")
        DriversRoot = user_data_dir("driver", "auto-clock")
        ScreenshotRoot = user_data_dir("screenshot", "auto-clock")
        AppRoot = os.path.dirname(DataRoot)  # auto-clock根目录
    else:
        # Linux/Unix: ~/.local/share/auto-clock
        AppRoot = user_data_dir("auto-clock", "auto-clock")
        LogRoot = os.path.join(AppRoot, "log")
        DataRoot = os.path.join(AppRoot, "data")
        BackupRoot = os.path.join(AppRoot, "backup")
        DriversRoot = os.path.join(AppRoot, "driver")
        ScreenshotRoot = os.path.join(AppRoot, "screenshot")
    
    DataJson: str = os.path.join(DataRoot, "data.json")
    TasksJson: str = os.path.join(DataRoot, "tasks.json")
    if hasattr(sys, '_MEIPASS'):
        ProjectRoot = sys._MEIPASS
    else:
        ProjectRoot = os.path.abspath(".")
    ConfigJson: str = os.path.join(ProjectRoot, "config.json")
    UiResourcePath: str = os.path.join(ProjectRoot, "ui", "resource")

@dataclass
class WebPath:
    AppConfigPathGitee: str = "https://gitee.com/garfieldgod/auto-clock/raw/master/config.json"
    AppConfigPathGitHub: str = "https://github.com/garfieldgod/auto-clock/raw/master/config.json"
    AppProjectPath: str = "https://github.com/GarfieldGod/auto-clock"
    AppProjectReleasePath: str = "https://github.com/GarfieldGod/AutoClock/releases"
    NeusoftKQPath: str = "https://kq.neusoft.com/"
    NeusoftKQLoginPath: str = "https://kq.neusoft.com/login"