import argparse
from pathlib import Path
import sys

if not getattr(sys, 'frozen', False) and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.log import Log
from src.runner.executor import run_task_by_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-Clock Runner")
    parser.add_argument("--task_id", required=True, help="Task ID")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args(argv)

    Log.open()
    try:
        ok, error = run_task_by_id(task_id=args.task_id, headless=args.headless)
        if ok:
            return 0
        return 2
    except Exception as e:
        Log.error(str(e))
        return 1
    finally:
        Log.close()


if __name__ == "__main__":
    raise SystemExit(main())
