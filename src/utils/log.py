import inspect
from pathlib import Path
from datetime import datetime

from src.utils.const import AppPath

_global_log_file = None
_global_log_path = None

class Log:
    @classmethod
    def open(cls):
        global _global_log_file, _global_log_path
        if _global_log_file is None:
            log_dir = Path(AppPath.LogRoot)
            log_dir.mkdir(parents=True, exist_ok=True)
            _global_log_path = log_dir / f"{datetime.now().strftime('%Y-%m-%d_%H_%M_%S.%f')}.log"

            _global_log_file = open(_global_log_path, 'a', encoding='utf-8')
            Log.info(f"日志文件已打开: {_global_log_path}")

    @classmethod
    def close(cls):
        global _global_log_file
        if _global_log_file is not None:
            _global_log_file.close()
            _global_log_file = None
            Log.info(f"日志文件已关闭: {_global_log_path}")

    @staticmethod
    def info(message):
        write("INFO", str(message))

    @staticmethod
    def waring(message):
        write("WARING", str(message))

    @staticmethod
    def error(message):
        write("ERROR", str(message))

def write(level: str, message: str):
    global _global_log_file

    if _global_log_file is None:
        return

    stack_info = "FUNCTION"
    stack = inspect.stack()
    if len(stack) >= 3:
        frame = stack[2]
        stack_info = f"{frame.function}:{frame.lineno}"

    log_line = f"{align_str(f'{level}',7)}  {datetime.now()}    {align_str(f'{stack_info}',25)}    {message}\n"
    print(log_line)
    _global_log_file.write(log_line)
    _global_log_file.flush()

def align_str(string: str, length: int):
    target_length = length
    current_length = len(string)
    if current_length < target_length:
        return string + " " * (target_length - current_length)
    else:
        return string[:target_length]