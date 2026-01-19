import os
import sys
import json
from datetime import datetime, timedelta

import requests
import platform
from pathlib import Path

from webdriver_manager.core.driver_cache import DriverCacheManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from src.utils.log import Log
from src.utils.const import Key, AppPath

class Utils:
    @staticmethod
    def get_nums_array(start, end, bit=2):
        num_array = []
        for i in range(start, end + 1):
            num_str = str(i)
            if len(num_str) < bit:
                num_str = "0" * (bit - len(num_str)) + num_str
            num_array.append(num_str)
        return num_array

    @staticmethod
    def truncate_text(text, max_length=15):
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    @staticmethod
    def write_dict_to_file(file_path, data):
        if not os.path.exists(Path(file_path).parent):
            os.makedirs(Path(file_path).parent)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def read_dict_from_json(file_path):
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dict_list = json.load(f)
                return dict_list
        except Exception as e:
            Log.info(f"Load {file_path} failed. error: {e}")
            return None

    @staticmethod
    def get_app_version_from_config_json(default: str = "") -> str:
        try:
            data = Utils.read_dict_from_json(AppPath.ConfigJson)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                v = data[0].get("version")
                return str(v) if v is not None else default
            if isinstance(data, dict):
                v = data.get("version")
                return str(v) if v is not None else default
            return default
        except Exception:
            return default

    @staticmethod
    def get_ico_path():
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, "icon.ico")

    @staticmethod
    def find_task(task_id):
        tasks_data = Utils.read_dict_from_json(AppPath.TasksJson)
        if not tasks_data:
            return None
        if isinstance(tasks_data, list):
            for task in tasks_data:
                if str(task.get(Key.TaskID)) == str(task_id):
                    return task
        elif isinstance(tasks_data, dict):
            if str(tasks_data.get(Key.TaskID)) == str(task_id):
                return tasks_data
        return None

    @staticmethod
    def short_to_long_day(short_day: str):
        mapping = {
            "Mon": "Monday",
            "Tue": "Tuesday",
            "Wed": "Wednesday",
            "Thu": "Thursday",
            "Fri": "Friday",
            "Sat": "Saturday",
            "Sun": "Sunday"
        }
        return mapping.get(short_day, short_day)

    @staticmethod
    def get_device_info():
        info = {
            "device_name": platform.node(),
            "system": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "processor": platform.processor()
        }
        return info

    @staticmethod
    def get_location_into(ip=None):
        url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            info = {
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "loc": data.get("loc"),
                "org": data.get("org"),
                "timezone": data.get("timezone")
            }
            return info
        except Exception as e:
            Log.error(f"Get Location Into Failed: {e}")
            return None

    @staticmethod
    def get_execute_file():
        if hasattr(sys, '_MEIPASS'):
            exe_path = None
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            if not exe_path: return None
            exe_path = Path(exe_path).absolute()
            Log.info(exe_path)
            if not exe_path.exists():
                message = f"Error: exe file do not exist: {exe_path}"
                Log.error(message)
                raise Exception(message)
            return str(exe_path)
        else:
            if os.name == 'nt':  # Windows
                python_exe = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
            else:  # Linux
                python_exe = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"
            entry_script = Path(__file__).parent.parent.parent / "entry.py"
            
            # 处理路径中的空格，跨平台方式
            python_path = str(python_exe)
            script_path = str(entry_script)
            
            if os.name == 'nt':  # Windows使用双引号
                return f'"{python_path}" "{script_path}"'
            else:  # Linux不需要引号
                return f'{python_path} {script_path}'

    @staticmethod
    def get_runner_execute_file():
        """Return the command prefix used to execute runner.

        - Frozen (PyInstaller): resolve sibling executable: auto-clock-runner(.exe)
        - Dev: resolve venv python + src/runner/runner_main.py
        """
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).absolute().parent
            runner_name = "auto-clock-runner.exe" if os.name == 'nt' else "auto-clock-runner"
            runner_path = (base_dir / runner_name).absolute()
            if not runner_path.exists():
                raise Exception(f"Runner executable not found: {runner_path}")
            if os.name == 'nt':
                return f'"{str(runner_path)}"'
            return str(runner_path)

        if os.name == 'nt':
            python_exe = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
        else:
            python_exe = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"
        runner_script = Path(__file__).parent.parent.parent / "src" / "runner" / "runner_main.py"

        python_path = str(python_exe)
        script_path = str(runner_script)
        if os.name == 'nt':
            return f'"{python_path}" "{script_path}"'
        return f'{python_path} {script_path}'

    @staticmethod
    def replace_signs(string):
        ret = (string.
               replace(":", "_").
               replace(" ", "_").
               replace("-", "_").
               replace(",", "_"))
        return ret

    @staticmethod
    def hour_min_str_add_seconds(time_str: str, add_seconds: int):
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                Log.error("时间格式错误，需用冒号 ':' 分隔")
                return None
            hour = parts[0].zfill(2)
            minute = parts[1].zfill(2)
            time_str = f"{hour}:{minute}"

            time = datetime.strptime(time_str, "%H:%M")
            delta = timedelta(seconds=add_seconds)
            new_time = time + delta
            return new_time.strftime("%H:%M")
        except ValueError as e:
            Log.error(f"时间格式错误！请输入 'HH:MM' 或 'H:M' 格式，错误原因：{str(e)}")
            return None

    @staticmethod
    def download_edge_web_driver(target_os: str | None = None, target_arch: str | None = None):
        try:
            old_wdm_os = os.environ.get("WDM_OS")
            old_wdm_arch = os.environ.get("WDM_ARCH")

            if target_os:
                os.environ["WDM_OS"] = str(target_os)
            if target_arch:
                os.environ["WDM_ARCH"] = str(target_arch)

            if not os.path.exists(AppPath.DriversRoot):
                os.makedirs(AppPath.DriversRoot, exist_ok=True)

            driver_cache = DriverCacheManager(
                root_dir=AppPath.DriversRoot
            )

            Log.info("Start to download Edge Web Driver...")
            driver_path = EdgeChromiumDriverManager(
                url="https://msedgedriver.microsoft.com/",
                latest_release_url="https://msedgedriver.microsoft.com/LATEST_RELEASE",
                cache_manager=driver_cache
            ).install()

            if not driver_path or not os.path.exists(driver_path):
                raise Exception("Driver path is invalid after download.")

            Log.info(f'DownLoad driver success, path: {driver_path}')
        except Exception as e:
            Log.error(f'DownLoad driver failed: {e}')
            return False, str(e)

        finally:
            if old_wdm_os is None:
                os.environ.pop("WDM_OS", None)
            else:
                os.environ["WDM_OS"] = old_wdm_os

            if old_wdm_arch is None:
                os.environ.pop("WDM_ARCH", None)
            else:
                os.environ["WDM_ARCH"] = old_wdm_arch

        return True, driver_path