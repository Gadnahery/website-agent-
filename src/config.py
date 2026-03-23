import json
import os
from typing import Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(name: str, default: str = "") -> str:
    return str(os.environ.get(name, default)).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _load_config() -> dict[str, Any]:
    config_path = os.path.join(ROOT_DIR, "config.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(ROOT_DIR, "config.example.json")
        if os.path.exists(example_path):
            config_path = example_path
        else:
            raise FileNotFoundError(
                f"Missing config.json at {config_path}. Copy config.example.json first."
            )

    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_verbose() -> bool:
    return bool(_load_config().get("verbose", True))


def get_country() -> str:
    return str(_load_config().get("country", "Tanzania")).strip() or "Tanzania"


def get_target_cities() -> list[str]:
    value = _load_config().get("target_cities", [])
    return [str(item).strip() for item in value if str(item).strip()]


def get_target_niches() -> list[str]:
    value = _load_config().get("target_niches", [])
    return [str(item).strip() for item in value if str(item).strip()]


def get_target_queries() -> list[str]:
    value = _load_config().get("target_queries", [])
    return [str(item).strip() for item in value if str(item).strip()]


def get_must_have_phone() -> bool:
    return bool(_load_config().get("must_have_phone", True))


def get_require_missing_website() -> bool:
    return bool(_load_config().get("require_missing_website", True))


def get_minimum_review_count() -> int:
    return int(_load_config().get("minimum_review_count", 3))


def get_minimum_rating() -> float:
    return float(_load_config().get("minimum_rating", 3.8))


def get_google_maps_scraper_zip_url() -> str:
    return str(_load_config().get("google_maps_scraper", "")).strip()


def get_scraper_timeout() -> int:
    return int(_load_config().get("scraper_timeout", 300))


def get_scraper_depth() -> int:
    return int(_load_config().get("scraper_depth", 1))


def get_scraper_concurrency() -> int:
    return int(_load_config().get("scraper_concurrency", 2))


def get_scraper_fast_mode() -> bool:
    return bool(_load_config().get("scraper_fast_mode", False))


def get_scraper_geo() -> str:
    return str(_load_config().get("scraper_geo", "")).strip()


def get_scraper_radius() -> int:
    return int(_load_config().get("scraper_radius", 10000))


def get_scraper_lang() -> str:
    return str(_load_config().get("scraper_lang", "en")).strip() or "en"


def get_city_geos() -> dict[str, str]:
    value = _load_config().get("city_geos", {})
    if not isinstance(value, dict):
        return {}

    geos: dict[str, str] = {}
    for city, coords in value.items():
        city_name = str(city).strip().lower()
        coord_value = str(coords).strip()
        if city_name and coord_value:
            geos[city_name] = coord_value
    return geos


def get_service_offer_name() -> str:
    return str(
        _load_config().get("service_offer_name", "Website design and launch package")
    ).strip()


def get_service_package_price_range() -> str:
    return str(_load_config().get("service_package_price_range", "")).strip()


def get_service_turnaround_days() -> int:
    return int(_load_config().get("service_turnaround_days", 10))


def get_service_stack() -> list[str]:
    value = _load_config().get("service_stack", [])
    return [str(item).strip() for item in value if str(item).strip()]


def get_outreach_angle() -> str:
    return str(
        _load_config().get(
            "outreach_angle",
            "You help local businesses convert phone inquiries into bookings and trust.",
        )
    ).strip()


def get_proposal_output_dir() -> str:
    configured = _env(
        "MPRINTER_PROPOSAL_OUTPUT_DIR",
        str(_load_config().get("proposal_output_dir", "proposals")).strip(),
    )
    if os.path.isabs(configured):
        return configured
    return os.path.join(get_data_root_dir(), configured or "proposals")


def get_build_package_output_dir() -> str:
    configured = _env(
        "MPRINTER_BUILD_PACKAGE_OUTPUT_DIR",
        str(_load_config().get("build_package_output_dir", "build-packages")).strip(),
    )
    if os.path.isabs(configured):
        return configured
    return os.path.join(get_data_root_dir(), configured or "build-packages")


def get_data_root_dir() -> str:
    configured = _env("MPRINTER_DATA_DIR", ROOT_DIR)
    return configured or ROOT_DIR


def get_ollama_base_url() -> str:
    return str(_load_config().get("ollama_base_url", "http://127.0.0.1:11434")).strip()


def get_ollama_model() -> str:
    return str(_load_config().get("ollama_model", "")).strip()


def get_target_currency() -> str:
    return str(_load_config().get("target_currency", "USD")).strip() or "USD"


def get_google_drive_enabled() -> bool:
    if _env("GOOGLE_DRIVE_ENABLED"):
        return _env_bool("GOOGLE_DRIVE_ENABLED")
    return bool(_load_config().get("google_drive_enabled", False))


def get_google_drive_folder_id() -> str:
    return _env(
        "GOOGLE_DRIVE_FOLDER_ID",
        str(_load_config().get("google_drive_folder_id", "")).strip(),
    )


def get_google_drive_service_account_json() -> str:
    return _env("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")


def get_google_drive_service_account_file() -> str:
    configured = str(_load_config().get("google_drive_service_account_file", "")).strip()
    if configured and not os.path.isabs(configured):
        configured = os.path.join(ROOT_DIR, configured)
    return _env("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", configured)
