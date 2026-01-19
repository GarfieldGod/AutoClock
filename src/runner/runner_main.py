import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

if not getattr(sys, 'frozen', False) and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.log import Log
from src.utils.const import AppPath, Key
from src.extend.auto_linux_plan import create_crontab_task, delete_crontab_task
from src.runner.executor import run_task_by_id

def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Auto-Clock Runner")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a task by task_id")
    run_parser.add_argument("--task_id", required=True, help="Task ID")
    run_parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    cron_create_parser = subparsers.add_parser("cron_create", help="Create a Linux crontab entry for a task")
    cron_create_parser.add_argument("--task_json_path", required=True, help="Path to task json file on Linux")

    cron_delete_parser = subparsers.add_parser("cron_delete", help="Delete a Linux crontab entry by task name")
    cron_delete_parser.add_argument("--task_name", required=True, help="System plan name")

    set_current_parser = subparsers.add_parser("set_current", help="Set servers/current to a version directory")
    set_current_parser.add_argument("--version", required=True, help="Version string")
    set_current_parser.add_argument(
        "--servers_root",
        default=str(Path(AppPath.AppRoot) / "servers"),
        help="Servers root directory (default: ~/.local/share/auto-clock/servers)",
    )

    driver_install_parser = subparsers.add_parser("driver_install", help="Install Edge WebDriver using webdriver_manager")
    driver_install_parser.add_argument(
        "--driver_root",
        default=str(Path(AppPath.AppRoot) / "driver"),
        help="Driver root directory (default: ~/.local/share/auto-clock/driver)",
    )

    # Backward compatible flags: auto-clock-runner --task_id=xxx [--headless]
    legacy_parser = argparse.ArgumentParser(add_help=False)
    legacy_parser.add_argument("--task_id")
    legacy_parser.add_argument("--headless", action="store_true")
    legacy_args, _ = legacy_parser.parse_known_args(argv)
    if legacy_args.task_id:
        normalized = ["run", "--task_id", legacy_args.task_id]
        if legacy_args.headless:
            normalized.append("--headless")
        args = parser.parse_args(normalized)
    else:
        args = parser.parse_args(argv)
        if args.command is None:
            parser.print_help()
            return 1

    Log.open()
    try:
        if args.command == "run":
            ok, error = run_task_by_id(task_id=args.task_id, headless=args.headless)
            if ok:
                return 0
            return 2

        if args.command == "driver_install":
            driver_root = str(Path(args.driver_root).expanduser().resolve())
            Path(driver_root).mkdir(parents=True, exist_ok=True)

            # 1) Prefer webdriver_manager if present (保持项目既有逻辑)
            try:
                from webdriver_manager.core.driver_cache import DriverCacheManager
                from webdriver_manager.microsoft import EdgeChromiumDriverManager

                cache = DriverCacheManager(root_dir=driver_root)
                path = EdgeChromiumDriverManager(
                    url="https://msedgedriver.microsoft.com/",
                    latest_release_url="https://msedgedriver.microsoft.com/LATEST_RELEASE",
                    cache_manager=cache,
                ).install()
                print(path)
                return 0
            except ModuleNotFoundError:
                # Fallback without extra dependencies
                pass

            # 2) Fallback: download zip and extract to driver_root/.wdm/drivers/edgedriver/linux64/<version>/
            def _edge_version() -> str | None:
                for cmd in ["microsoft-edge --version", "microsoft-edge-stable --version", "msedge --version"]:
                    try:
                        res = subprocess.run(cmd.split(), capture_output=True, text=True)
                        out = (res.stdout or res.stderr or "").strip()
                        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
                        if m:
                            return m.group(1)
                    except Exception:
                        continue
                return None

            def _latest_release() -> str:
                url = "https://msedgedriver.microsoft.com/LATEST_RELEASE"
                with urllib.request.urlopen(url, timeout=20) as resp:
                    return resp.read().decode("utf-8").strip()

            version = _edge_version() or _latest_release()
            zip_url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_linux64.zip"

            target_dir = Path(driver_root) / ".wdm" / "drivers" / "edgedriver" / "linux64" / version
            target_dir.mkdir(parents=True, exist_ok=True)
            driver_path = target_dir / "msedgedriver"
            if driver_path.exists():
                print(str(driver_path))
                return 0

            with tempfile.TemporaryDirectory() as td:
                tmp_zip = Path(td) / "edgedriver_linux64.zip"
                urllib.request.urlretrieve(zip_url, tmp_zip)
                with zipfile.ZipFile(tmp_zip, "r") as z:
                    z.extractall(target_dir)

            # zip contains msedgedriver at root; ensure executable bit
            try:
                st = os.stat(driver_path)
                os.chmod(driver_path, st.st_mode | 0o111)
            except Exception:
                pass

            print(str(driver_path))
            return 0

        if args.command == "cron_create":
            task_path = Path(args.task_json_path)
            if not task_path.exists():
                Log.error(f"Task json not found: {task_path}")
                return 1
            task = json.loads(task_path.read_text(encoding="utf-8"))
            ok, error = create_crontab_task(task)
            if ok:
                return 0
            Log.error(error or "Create crontab task failed")
            return 2

        if args.command == "cron_delete":
            ok, error = delete_crontab_task(args.task_name)
            if ok:
                return 0
            Log.error(error or "Delete crontab task failed")
            return 2

        if args.command == "set_current":
            servers_root = Path(args.servers_root).expanduser().resolve()
            target_dir = (servers_root / args.version).resolve()
            link_path = servers_root / "current"
            servers_root.mkdir(parents=True, exist_ok=True)
            if not target_dir.exists():
                Log.error(f"Version directory not found: {target_dir}")
                return 1
            # Use ln -sfn to update atomically
            result = subprocess.run(["ln", "-sfn", str(target_dir), str(link_path)], capture_output=True, text=True)
            if result.returncode != 0:
                Log.error(result.stderr.strip() or f"ln failed with code {result.returncode}")
                return 2
            return 0

        Log.error(f"Unknown command: {args.command}")
        return 1
    except Exception as e:
        Log.error(str(e))
        return 1
    finally:
        Log.close()


if __name__ == "__main__":
    raise SystemExit(main())
