import json
from pathlib import Path
from typing import Dict

_CONFIG_PATH = Path("./.ICAdvConfig")


def _read_raw_config() -> Dict[str, str]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict):
        return {str(key): value for key, value in data.items()}
    return {}


def _write_raw_config(data: Dict[str, str]) -> None:
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    try:
        with _CONFIG_PATH.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)
    except OSError:
        pass


def load_tool_path() -> str:
    return _read_raw_config().get("tool_path", "")

def load_parameter() -> str:
    return _read_raw_config().get("parameter", "")


def save_tool_path(path: str) -> None:
    data = _read_raw_config()
    cleaned = path.strip()
    if cleaned:
        data["tool_path"] = cleaned
    else:
        data.pop("tool_path", None)
    _write_raw_config(data)
