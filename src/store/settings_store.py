import os
from pathlib import Path

from src.utils.const import AppPath
from src.utils.utils import Utils


class SettingsStore:
    def __init__(self, file_path: str | None = None):
        if file_path is None:
            file_path = os.path.join(AppPath.DataRoot, "settings.json")
        self._file_path = str(file_path)
        self._data: dict = {}

    @property
    def file_path(self) -> str:
        return self._file_path

    def load(self) -> bool:
        try:
            if not os.path.exists(self._file_path):
                self._data = {}
                return False
            data = Utils.read_dict_from_json(self._file_path)
            self._data = data if isinstance(data, dict) else {}
            return True
        except Exception:
            self._data = {}
            return False

    def save(self) -> bool:
        try:
            Path(os.path.dirname(self._file_path)).mkdir(parents=True, exist_ok=True)
            Utils.write_dict_to_file(self._file_path, self._data if isinstance(self._data, dict) else {})
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        try:
            if not isinstance(self._data, dict):
                return default
            return self._data.get(key, default)
        except Exception:
            return default

    def set(self, key, value):
        try:
            if not isinstance(self._data, dict):
                self._data = {}
            self._data[key] = value
            return True
        except Exception:
            return False

    def as_dict(self) -> dict:
        return dict(self._data) if isinstance(self._data, dict) else {}

    def update(self, payload: dict):
        try:
            if not isinstance(payload, dict):
                return False
            if not isinstance(self._data, dict):
                self._data = {}
            self._data.update(payload)
            return True
        except Exception:
            return False
