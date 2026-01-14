import argparse
import json
import subprocess
import sys
from pathlib import Path

if not getattr(sys, 'frozen', False) and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.log import Log
from src.utils.const import AppPath, Key
from src.extend.auto_linux_plan import create_crontab_task, delete_crontab_task
from src.runner.executor import run_task_by_id

def main(argv: list[str] | None = None) -> int:
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

    args = parser.parse_args(argv)

    # Backward compatible flags: auto-clock-runner --task_id=xxx [--headless]
    if args.command is None:
        legacy_parser = argparse.ArgumentParser(add_help=False)
        legacy_parser.add_argument("--task_id")
        legacy_parser.add_argument("--headless", action="store_true")
        legacy_args, _ = legacy_parser.parse_known_args(argv)
        if legacy_args.task_id:
            args.command = "run"
            args.task_id = legacy_args.task_id
            args.headless = legacy_args.headless
        else:
            parser.print_help()
            return 1

    Log.open()
    try:
        if args.command == "run":
            ok, error = run_task_by_id(task_id=args.task_id, headless=args.headless)
            if ok:
                return 0
            return 2

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
