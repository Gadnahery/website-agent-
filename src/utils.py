import os
import re
from datetime import datetime

from config import (
    get_build_package_output_dir,
    get_data_root_dir,
    get_proposal_output_dir,
    get_verbose,
)
from status import info


def assert_folder_structure() -> None:
    for directory in [
        os.path.join(get_data_root_dir(), ".mp"),
        get_proposal_output_dir(),
        get_build_package_output_dir(),
    ]:
        if not os.path.exists(directory):
            if get_verbose():
                info(f'Creating directory "{directory}"', False)
            os.makedirs(directory, exist_ok=True)


def get_first_time_running() -> bool:
    return not os.path.exists(os.path.join(get_data_root_dir(), ".mp"))


def slugify(value: str, max_length: int = 60) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized[:max_length] or "lead"


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_phone(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    if raw.startswith("+"):
        return "+" + re.sub(r"\D", "", raw[1:])

    return re.sub(r"\D", "", raw)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def normalize_business_name(value: str) -> str:
    cleaned = normalize_text(value)
    cleaned = re.sub(
        r"\b(ltd|limited|inc|company|co|plc|enterprise|enterprises|services|service|official)\b",
        "",
        cleaned,
    )
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()
