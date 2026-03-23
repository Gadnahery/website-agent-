import json
import os
from typing import Any

from config import get_data_root_dir


def get_cache_path() -> str:
    return os.path.join(get_data_root_dir(), ".mp")


def get_leads_cache_path() -> str:
    return os.path.join(get_cache_path(), "website_leads.json")


def get_scraper_input_path() -> str:
    return os.path.join(get_cache_path(), "search_queries.txt")


def get_scraper_results_path() -> str:
    return os.path.join(get_cache_path(), "scraper_results.csv")


def get_call_sheet_path() -> str:
    return os.path.join(get_cache_path(), "call_sheet.csv")


def _initial_payload() -> dict[str, Any]:
    return {"leads": []}


def load_leads() -> list[dict[str, Any]]:
    cache_path = get_leads_cache_path()

    if not os.path.exists(cache_path):
        with open(cache_path, "w", encoding="utf-8") as file:
            json.dump(_initial_payload(), file, indent=2)

    with open(cache_path, "r", encoding="utf-8") as file:
        payload = json.load(file) or _initial_payload()
        return list(payload.get("leads", []))


def save_leads(leads: list[dict[str, Any]]) -> None:
    with open(get_leads_cache_path(), "w", encoding="utf-8") as file:
        json.dump({"leads": leads}, file, indent=2, ensure_ascii=False)


def upsert_leads(incoming_leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {lead["id"]: lead for lead in load_leads()}

    for lead in incoming_leads:
        lead_id = lead["id"]
        previous = existing.get(lead_id, {})

        merged = dict(previous)
        merged.update(lead)
        merged["created_at"] = previous.get("created_at", lead.get("created_at", ""))
        merged["status"] = previous.get("status", lead.get("status", "new"))
        merged["notes"] = previous.get("notes", lead.get("notes", ""))
        merged["proposal_path"] = previous.get(
            "proposal_path", lead.get("proposal_path", "")
        )
        merged["build_package_path"] = previous.get(
            "build_package_path", lead.get("build_package_path", "")
        )
        merged["last_contacted_at"] = previous.get("last_contacted_at", "")
        existing[lead_id] = merged

    leads = sorted(
        existing.values(),
        key=lambda item: (item.get("score", 0), item.get("review_count", 0)),
        reverse=True,
    )
    save_leads(leads)
    return leads


def update_lead(lead_id: str, **fields: Any) -> dict[str, Any] | None:
    leads = load_leads()
    updated = None

    for lead in leads:
        if lead.get("id") == lead_id:
            lead.update(fields)
            updated = lead
            break

    if updated is not None:
        save_leads(leads)

    return updated
