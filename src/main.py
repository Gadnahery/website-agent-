import os
import subprocess
import sys

from art import print_banner
from classes.WebsiteSalesAgent import WebsiteSalesAgent
from constants import LEAD_STATUSES, OPTIONS
from status import error, info, question, success, warning
from utils import assert_folder_structure, get_first_time_running, parse_int


def _show_menu() -> int:
    info("\n============ OPTIONS ============", False)
    for idx, option in enumerate(OPTIONS, start=1):
        print(f" {idx}. {option}")
    info("=================================\n", False)

    raw = input("Select an option: ").strip()
    if not raw:
        raise ValueError("Empty input is not allowed.")
    return int(raw)


def _ask_limit(prompt: str, default: int) -> int:
    raw = question(f"{prompt} [{default}]: ", False).strip()
    return parse_int(raw, default) if raw else default


def _ask_status_filter() -> str:
    return question(
        "Filter by status (blank for all, e.g. new / contacted / proposal_ready): ",
        False,
    ).strip()


def main() -> None:
    agent = WebsiteSalesAgent()

    while True:
        try:
            choice = _show_menu()
        except ValueError as exc:
            warning(f"Invalid input: {exc}", False)
            continue

        if choice == 1:
            try:
                leads = agent.discover_leads()
                success(f"Lead discovery complete. Total stored leads: {len(leads)}")
            except Exception as exc:
                error(f"Lead discovery failed: {exc}")
        elif choice == 2:
            agent.show_leads(
                limit=_ask_limit("How many leads should be shown?", 20),
                status_filter=_ask_status_filter(),
            )
        elif choice == 3:
            try:
                agent.generate_briefs(
                    limit=_ask_limit("How many briefs should be generated?", 10),
                    status_filter=_ask_status_filter(),
                )
            except Exception as exc:
                error(f"Proposal generation failed: {exc}")
        elif choice == 4:
            try:
                agent.export_call_sheet()
            except Exception as exc:
                error(f"Could not export call sheet: {exc}")
        elif choice == 5:
            agent.show_leads(limit=15)
            lead_id = question("Lead ID: ", False).strip()
            if not lead_id:
                warning("Lead ID is required.", False)
                continue

            info(f"Available statuses: {', '.join(LEAD_STATUSES)}", False)
            status = question("New status: ", False).strip()
            if status not in LEAD_STATUSES:
                warning("Invalid status selected.", False)
                continue

            notes = question("Notes (optional): ", False).strip()
            agent.update_status(lead_id=lead_id, status=status, notes=notes)
        elif choice == 6:
            try:
                agent.generate_build_packages(
                    limit=_ask_limit("How many won-lead build packages should be generated?", 10),
                    status_filter="won",
                )
            except Exception as exc:
                error(f"Build package generation failed: {exc}")
        elif choice == 7:
            try:
                dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.py")
                subprocess.Popen([sys.executable, dashboard_path])
                success("Dashboard launched at http://127.0.0.1:5055", False)
            except Exception as exc:
                error(f"Could not launch dashboard: {exc}")
        elif choice == 8:
            success("Quitting.", False)
            sys.exit(0)
        else:
            warning("Invalid option selected.", False)


if __name__ == "__main__":
    print_banner()

    if get_first_time_running():
        info(
            "First run detected. Copy config.example.json to config.json and tune your Tanzania lead settings.",
            False,
        )

    assert_folder_structure()
    main()
