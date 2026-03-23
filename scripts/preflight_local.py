#!/usr/bin/env python3
import importlib.util
import json
import os
import shutil
import sys
import urllib.request


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")


def ok(message: str) -> None:
    print(f"[OK] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def url_status(url: str, timeout: int = 10) -> int | None:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return getattr(response, "status", None)


def main() -> int:
    if not os.path.exists(CONFIG_PATH):
        fail(f"Missing config file: {CONFIG_PATH}")
        return 1

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        cfg = json.load(file)

    failures = 0

    missing_packages = [
        package
        for package in ("requests", "termcolor", "prettytable", "ollama")
        if importlib.util.find_spec(package) is None
    ]
    if missing_packages:
        fail(
            "Missing Python packages: "
            + ", ".join(missing_packages)
            + ". Install them with `venv\\Scripts\\python.exe -m pip install -r requirements.txt` "
            + "or `venv/bin/python -m pip install -r requirements.txt`."
        )
        failures += 1
    else:
        ok("Required Python packages are installed")

    country = str(cfg.get("country", "")).strip()
    if country:
        ok(f"country={country}")
    else:
        fail("country is empty")
        failures += 1

    niches = cfg.get("target_niches", [])
    queries = cfg.get("target_queries", [])
    if niches or queries:
        ok("At least one niche/query source is configured")
    else:
        fail("Both target_niches and target_queries are empty")
        failures += 1

    scraper_binaries = [
        os.path.join(ROOT_DIR, "google-maps-scraper.exe"),
        os.path.join(ROOT_DIR, "google-maps-scraper"),
    ]

    if shutil.which("go"):
        ok("Go is installed")
    elif any(os.path.exists(path) for path in scraper_binaries):
        ok("Local scraper binary is present")
    else:
        fail("Neither Go nor a local google-maps-scraper binary is available")
        failures += 1

    scraper_zip = str(cfg.get("google_maps_scraper", "")).strip()
    if scraper_zip:
        try:
            status = url_status(scraper_zip, timeout=10)
            ok(f"Scraper URL reachable: HTTP {status}")
        except Exception as exc:
            warn(f"Could not reach scraper URL: {exc}")
    else:
        fail("google_maps_scraper is empty")
        failures += 1

    ollama_model = str(cfg.get("ollama_model", "")).strip()
    ollama_base = str(cfg.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
    if ollama_model:
        try:
            status = url_status(f"{ollama_base}/api/tags", timeout=5)
            ok(f"Ollama reachable at {ollama_base}: HTTP {status}")
        except Exception as exc:
            warn(f"Ollama model is configured but server is not reachable: {exc}")
    else:
        warn("ollama_model is blank; proposal generation will use the template brief")

    proposal_dir = os.path.join(ROOT_DIR, str(cfg.get("proposal_output_dir", "proposals")))
    ok(f"proposal_output_dir={proposal_dir}")
    build_package_dir = os.path.join(
        ROOT_DIR, str(cfg.get("build_package_output_dir", "build-packages"))
    )
    ok(f"build_package_output_dir={build_package_dir}")

    if bool(cfg.get("scraper_fast_mode", False)):
        scraper_geo = str(cfg.get("scraper_geo", "")).strip()
        city_geos = cfg.get("city_geos", {})
        if scraper_geo or (isinstance(city_geos, dict) and city_geos):
            ok("Fast scraper mode has coordinates configured")
        else:
            fail("scraper_fast_mode is enabled but scraper_geo/city_geos are empty")
            failures += 1

    if failures:
        print("")
        print(f"Preflight completed with {failures} blocking issue(s).")
        return 1

    print("")
    print("Preflight passed. Local setup looks ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
