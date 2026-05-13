import os
import posixpath
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
    Enabled: str = "enabled"
    LastRunResult: str = "last_run_result"

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
    LinuxDisplay: str = "linux_display"
    CheckLinuxCredentialsOnPlanCreate: str = "check_linux_credentials_on_plan_create"
    CheckUpdateOnStartup: str = "check_update_on_startup"

    SshEnabled: str = "ssh_enabled"
    SshHost: str = "ssh_host"
    SshUsername: str = "ssh_username"
    SshPassword: str = "ssh_password"
    SshUsePrivateKey: str = "ssh_use_private_key"
    SshPrivateKeyPath: str = "ssh_private_key_path"
    SshServerPlatform: str = "ssh_server_platform"
    SshRemoteAppRoot: str = "ssh_remote_app_root"


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
    
    UpdaterRoot: str = os.path.join(AppRoot, "updater")
    DataJson: str = os.path.join(DataRoot, "data.json")
    TasksJson: str = os.path.join(DataRoot, "tasks.json")
    RunnerResultJson: str = os.path.join(DataRoot, "runner_result.json")
    if hasattr(sys, '_MEIPASS'):
        ProjectRoot = sys._MEIPASS
    else:
        ProjectRoot = os.path.abspath(".")
    ConfigJson: str = os.path.join(ProjectRoot, "config.json")
    UiResourcePath: str = os.path.join(ProjectRoot, "ui", "resource")

    RemoteAppRoot: str | None = None
    RemoteLogRoot: str | None = None
    RemoteDataRoot: str | None = None
    RemoteBackupRoot: str | None = None
    RemoteDriversRoot: str | None = None
    RemoteScreenshotRoot: str | None = None

    @staticmethod
    def update_remote(app_root_abs: str):
        app_root_abs = str(app_root_abs or "").strip()
        if not app_root_abs.startswith("/"):
            raise ValueError(f"remote app_root must be an absolute path: {app_root_abs}")

        AppPath.RemoteAppRoot = app_root_abs.rstrip("/")
        AppPath.RemoteLogRoot = posixpath.join(AppPath.RemoteAppRoot, "log")
        AppPath.RemoteDataRoot = posixpath.join(AppPath.RemoteAppRoot, "data")
        AppPath.RemoteBackupRoot = posixpath.join(AppPath.RemoteAppRoot, "backup")
        AppPath.RemoteDriversRoot = posixpath.join(AppPath.RemoteAppRoot, "driver")
        AppPath.RemoteScreenshotRoot = posixpath.join(AppPath.RemoteAppRoot, "screenshot")

    @staticmethod
    def clear_remote():
        AppPath.RemoteAppRoot = None
        AppPath.RemoteLogRoot = None
        AppPath.RemoteDataRoot = None
        AppPath.RemoteBackupRoot = None
        AppPath.RemoteDriversRoot = None
        AppPath.RemoteScreenshotRoot = None


@dataclass
class WebPath:
    AppConfigPathGitee: str = "https://gitee.com/garfieldgod/auto-clock/raw/master/config.json"
    AppConfigPathGitHub: str = "https://github.com/GarfieldGod/auto-clock/raw/master/config.json"
    AppProjectPath: str = "https://github.com/GarfieldGod/auto-clock"
    AppReleasePageTemplate: str = "https://github.com/GarfieldGod/auto-clock/releases/tag/v{version}"
    AppWindowsDownloadUrlTemplate: str = "https://github.com/GarfieldGod/auto-clock/releases/download/v{version}/auto-clock-{version}-windows.zip"
    AppLinuxDownloadUrlTemplate: str = "https://github.com/GarfieldGod/auto-clock/releases/download/v{version}/auto-clock-{version}-linux.tar.gz"
    NeusoftKQPath: str = "https://kq.neusoft.com/"
    NeusoftKQLoginPath: str = "https://kq.neusoft.com/login"
    LinuxRunnerDownloadUrlTemplate: str = "https://github.com/GarfieldGod/auto-clock/releases/download/v{version}/auto-clock-runner-{version}-linux.tar.gz"
    LocalWindowsRunnerDownloadUrlTemplate: str = "https://github.com/GarfieldGod/auto-clock/releases/download/v{version}/auto-clock-runner-{version}-windows.zip"
    LocalLinuxRunnerDownloadUrlTemplate: str = "https://github.com/GarfieldGod/auto-clock/releases/download/v{version}/auto-clock-runner-{version}-linux.tar.gz"