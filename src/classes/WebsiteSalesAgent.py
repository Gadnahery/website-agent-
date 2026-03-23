import csv
import glob
import hashlib
import os
import platform
import re
import subprocess
import zipfile
from io import BytesIO
from typing import Callable
from urllib.parse import urlparse

import requests
from prettytable import PrettyTable

from cache import (
    get_call_sheet_path,
    get_scraper_input_path,
    get_scraper_results_path,
    load_leads,
    update_lead,
    upsert_leads,
)
from config import (
    get_build_package_output_dir,
    get_city_geos,
    get_country,
    get_google_maps_scraper_zip_url,
    get_minimum_rating,
    get_minimum_review_count,
    get_must_have_phone,
    get_outreach_angle,
    get_proposal_output_dir,
    get_require_missing_website,
    get_scraper_concurrency,
    get_scraper_depth,
    get_scraper_fast_mode,
    get_scraper_geo,
    get_scraper_lang,
    get_scraper_radius,
    get_scraper_timeout,
    get_service_offer_name,
    get_service_package_price_range,
    get_service_stack,
    get_service_turnaround_days,
    get_target_currency,
    get_target_cities,
    get_target_niches,
    get_target_queries,
    get_verbose,
)
from llm_provider import generate_text, get_active_model, is_ollama_available
from status import info, success, warning
from utils import (
    current_timestamp,
    normalize_business_name,
    normalize_phone,
    normalize_text,
    parse_float,
    parse_int,
    slugify,
)

HIGH_VALUE_KEYWORDS = {
    "hotel": 34,
    "resort": 34,
    "lodge": 32,
    "guest house": 26,
    "camp": 26,
    "safari": 32,
    "tour": 28,
    "travel": 20,
    "apartment": 16,
    "villa": 22,
    "clinic": 18,
    "dent": 18,
    "hospital": 18,
    "law": 16,
    "attorney": 16,
    "real estate": 20,
    "property": 18,
    "school": 14,
    "academy": 14,
}

SOCIAL_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "wa.me",
    "whatsapp.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
}

MARKETPLACE_DOMAINS = {
    "booking.com",
    "tripadvisor.com",
    "airbnb.com",
    "expedia.com",
    "hotels.com",
    "jiji.co.tz",
}

WEBSITE_BUILDER_DOMAINS = {
    "business.site",
    "sites.google.com",
    "wixsite.com",
    "weebly.com",
    "yolasite.com",
    "site123.me",
    "webnode.page",
    "jimdosite.com",
    "ueniweb.com",
    "blogspot.com",
    "linktr.ee",
    "beacons.ai",
    "taplink.cc",
}

CITY_PRIORITY_BONUSES = {
    "zanzibar": 16,
    "arusha": 14,
    "dar es salaam": 12,
    "moshi": 12,
    "bagamoyo": 10,
    "mwanza": 8,
}


class WebsiteSalesAgent:
    def __init__(
        self,
        logger: Callable[[str, str], None] | None = None,
        runtime_profile: dict[str, object] | None = None,
    ) -> None:
        profile = runtime_profile or {}
        self.country = self._profile_text(profile, "country", get_country())
        self.target_cities = self._profile_list(profile, "target_cities", get_target_cities())
        self.target_niches = self._profile_list(profile, "target_niches", get_target_niches())
        self.target_queries = self._profile_list(
            profile, "target_queries", get_target_queries()
        )
        self.city_geos = self._profile_city_geos(profile.get("city_geos"))
        self.must_have_phone = self._profile_bool(
            profile, "must_have_phone", get_must_have_phone()
        )
        self.require_missing_website = self._profile_bool(
            profile, "require_missing_website", get_require_missing_website()
        )
        self.minimum_review_count = self._profile_int(
            profile, "minimum_review_count", get_minimum_review_count()
        )
        self.minimum_rating = self._profile_float(
            profile, "minimum_rating", get_minimum_rating()
        )
        self.scraper_timeout = self._profile_int(
            profile, "scraper_timeout", get_scraper_timeout()
        )
        self.scraper_depth = self._profile_int(profile, "scraper_depth", get_scraper_depth())
        self.scraper_concurrency = self._profile_int(
            profile, "scraper_concurrency", get_scraper_concurrency()
        )
        self.scraper_fast_mode = self._profile_bool(
            profile, "scraper_fast_mode", get_scraper_fast_mode()
        )
        self.scraper_geo = self._profile_text(profile, "scraper_geo", get_scraper_geo())
        self.scraper_lang = self._profile_text(profile, "scraper_lang", get_scraper_lang())
        self.scraper_radius = self._profile_int(
            profile, "scraper_radius", get_scraper_radius()
        )
        self.verbose = get_verbose()
        self.logger = logger
        self._scraper_flags: set[str] | None = None

    def _scraper_source_marker_path(self) -> str:
        return f"{self._binary_path()}.source-url"

    def _read_scraper_source_marker(self) -> str:
        marker_path = self._scraper_source_marker_path()
        if not os.path.exists(marker_path):
            return ""

        with open(marker_path, "r", encoding="utf-8") as file:
            return file.read().strip()

    def _write_scraper_source_marker(self, value: str) -> None:
        with open(self._scraper_source_marker_path(), "w", encoding="utf-8") as file:
            file.write(str(value).strip())

    def _scraper_release_asset_url(self, source_url: str) -> str:
        match = re.search(
            r"github\.com/gosom/google-maps-scraper/archive/refs/tags/(?P<tag>v[\w.\-]+)\.zip",
            source_url,
            flags=re.IGNORECASE,
        )
        if not match:
            return ""

        tag = match.group("tag")
        version = tag.removeprefix("v")
        system = platform.system().lower()
        asset_name = ""

        if system == "windows":
            asset_name = f"google_maps_scraper-{version}-windows-amd64.exe"
        elif system == "linux":
            asset_name = f"google_maps_scraper-{version}-linux-amd64"
        elif system == "darwin":
            asset_name = f"google_maps_scraper-{version}-darwin-amd64"

        if not asset_name:
            return ""

        return (
            f"https://github.com/gosom/google-maps-scraper/releases/download/{tag}/{asset_name}"
        )

    def _download_binary(self, url: str) -> None:
        self._info("Downloading google-maps-scraper binary...", False)
        response = requests.get(url, timeout=240)
        response.raise_for_status()

        with open(self._binary_path(), "wb") as file:
            file.write(response.content)

        os.chmod(self._binary_path(), os.stat(self._binary_path()).st_mode | 0o755)
        self._scraper_flags = None

    def _should_refresh_scraper(self, source_url: str) -> bool:
        if not os.path.exists(self._binary_path()):
            return True
        if not source_url:
            return False
        return self._read_scraper_source_marker() != source_url

    def _profile_text(self, profile: dict[str, object], key: str, default: str) -> str:
        value = profile.get(key, default)
        return str(value).strip() or default

    def _profile_list(
        self, profile: dict[str, object], key: str, default: list[str]
    ) -> list[str]:
        has_override = key in profile
        value = profile.get(key, default)
        if not isinstance(value, list):
            return list(default)

        items: list[str] = []
        for item in value:
            cleaned = str(item).strip()
            if cleaned and cleaned not in items:
                items.append(cleaned)
        if items or has_override:
            return items
        return list(default)

    def _profile_bool(
        self, profile: dict[str, object], key: str, default: bool
    ) -> bool:
        value = profile.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _profile_int(self, profile: dict[str, object], key: str, default: int) -> int:
        return parse_int(profile.get(key, default), default)

    def _profile_float(
        self, profile: dict[str, object], key: str, default: float
    ) -> float:
        return parse_float(profile.get(key, default), default)

    def _profile_city_geos(self, value: object) -> dict[str, str]:
        geos = dict(get_city_geos())
        if not isinstance(value, dict):
            return geos

        for city, geo in value.items():
            city_name = str(city).strip().lower()
            geo_value = str(geo).strip()
            if city_name and geo_value:
                geos[city_name] = geo_value
        return geos

    def _emit(self, level: str, message: str, show_marker: bool = True) -> None:
        if self.logger is not None:
            self.logger(level, message)

        if level == "success":
            success(message, show_marker)
        elif level == "warning":
            warning(message, show_marker)
        else:
            info(message, show_marker)

    def _info(self, message: str, show_marker: bool = True) -> None:
        self._emit("info", message, show_marker)

    def _success(self, message: str, show_marker: bool = True) -> None:
        self._emit("success", message, show_marker)

    def _warning(self, message: str, show_marker: bool = True) -> None:
        self._emit("warning", message, show_marker)

    def _run_command(
        self,
        command: list[str],
        cwd: str | None = None,
        timeout: int | None = None,
    ) -> None:
        if self.logger is None:
            subprocess.run(command, cwd=cwd, check=True, timeout=timeout)
            return

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        try:
            assert process.stdout is not None
            for line in process.stdout:
                cleaned = line.strip()
                if cleaned:
                    self.logger("process", cleaned)
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            raise

        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command)

    def _find_scraper_dir(self) -> str:
        candidates = sorted(glob.glob("google-maps-scraper-*"))
        for candidate in candidates:
            if os.path.isdir(candidate) and os.path.exists(
                os.path.join(candidate, "go.mod")
            ):
                return candidate
        return ""

    def _scraper_binary_name(self) -> str:
        return (
            "google-maps-scraper.exe"
            if platform.system() == "Windows"
            else "google-maps-scraper"
        )

    def _binary_path(self) -> str:
        return os.path.join(os.getcwd(), self._scraper_binary_name())

    def _run(self, command: list[str], cwd: str | None = None) -> None:
        if self.verbose:
            self._info(f'Running: {" ".join(command)}', False)
        self._run_command(command, cwd=cwd)

    def _scraper_supported_flags(self) -> set[str]:
        if self._scraper_flags is not None:
            return self._scraper_flags

        try:
            result = subprocess.run(
                [self._binary_path(), "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
            output = f"{result.stdout}\n{result.stderr}"
        except Exception:
            self._scraper_flags = set()
            return self._scraper_flags

        flags = set(re.findall(r"(?m)^\s+-(\w[\w-]*)", output))
        self._scraper_flags = flags
        return flags

    def _ensure_scraper(self) -> None:
        source_url = get_google_maps_scraper_zip_url()
        if not self._should_refresh_scraper(source_url):
            return

        if not source_url:
            raise RuntimeError("google_maps_scraper is not configured in config.json")

        release_asset_url = self._scraper_release_asset_url(source_url)
        if release_asset_url:
            self._download_binary(release_asset_url)
            self._write_scraper_source_marker(source_url)
            return

        scraper_dir = self._find_scraper_dir()
        if not scraper_dir:
            self._info("Downloading google-maps-scraper...", False)
            response = requests.get(source_url, timeout=120)
            response.raise_for_status()

            archive = zipfile.ZipFile(BytesIO(response.content))
            for member in archive.namelist():
                if ".." in member or member.startswith("/"):
                    self._warning(f"Skipping suspicious archive path: {member}")
                    continue
                archive.extract(member)

            scraper_dir = self._find_scraper_dir()

        if not scraper_dir:
            raise RuntimeError("Could not locate the extracted google-maps-scraper folder.")

        self._run(["go", "mod", "download"], cwd=scraper_dir)
        self._run(["go", "build"], cwd=scraper_dir)

        built_binary = os.path.join(scraper_dir, self._scraper_binary_name())
        if not os.path.exists(built_binary):
            raise RuntimeError(f"Expected scraper binary at {built_binary}")

        os.replace(built_binary, self._binary_path())
        os.chmod(self._binary_path(), os.stat(self._binary_path()).st_mode | 0o755)
        self._write_scraper_source_marker(source_url)
        self._scraper_flags = None

    def build_queries(self) -> list[str]:
        if self.target_queries:
            return [self._compose_query("", query) for query in self.target_queries]

        queries = []
        for niche in self.target_niches:
            for city in self.target_cities:
                queries.append(self._compose_query(niche, city))
        return queries

    def _compose_query(self, niche: str, location: str) -> str:
        niche_text = str(niche).strip()
        location_text = str(location).strip()
        if not niche_text:
            query = location_text
        elif " in " in niche_text.lower():
            query = niche_text
        else:
            query = f"{niche_text} in {location_text}"

        lowered = query.lower()
        if self.country and self.country.lower() not in lowered:
            query = f"{query}, {self.country}"

        return query.strip(" ,")

    def _write_queries_file(self, queries: list[str]) -> str:
        input_path = get_scraper_input_path()
        with open(input_path, "w", encoding="utf-8") as file:
            file.write("\n".join(queries))
            file.write("\n")
        return input_path

    def _results_path(self, suffix: str = "") -> str:
        base_path = get_scraper_results_path()
        if not suffix:
            return base_path

        root, extension = os.path.splitext(base_path)
        safe_suffix = slugify(suffix, max_length=40)
        return f"{root}-{safe_suffix}{extension or '.csv'}"

    def _query_geo(self, query: str) -> str:
        lowered = query.lower()
        for city, geo in self.city_geos.items():
            if city in lowered:
                return geo
        return ""

    def _scrape_batches(self, queries: list[str]) -> list[tuple[str, list[str], str]]:
        if not self.scraper_fast_mode:
            return [("all", queries, self.scraper_geo)]

        configured_geo = self.scraper_geo
        if configured_geo:
            return [("all", queries, configured_geo)]

        grouped: dict[str, list[str]] = {}
        for query in queries:
            geo = self._query_geo(query)
            if not geo:
                raise RuntimeError(
                    "scraper_fast_mode requires either `scraper_geo` or matching `city_geos` entries in config.json."
                )
            grouped.setdefault(geo, []).append(query)

        batches = []
        for geo, batch_queries in grouped.items():
            batches.append((batch_queries[0], batch_queries, geo))
        return batches

    def _run_scraper(self, queries: list[str], geo: str = "", results_suffix: str = "") -> str:
        self._ensure_scraper()
        input_path = self._write_queries_file(queries)
        results_path = self._results_path(results_suffix)
        supported_flags = self._scraper_supported_flags()

        args = [
            self._binary_path(),
            "-input",
            input_path,
            "-results",
            results_path,
            "-depth",
            str(self.scraper_depth),
            "-c",
            str(self.scraper_concurrency),
            "-lang",
            self.scraper_lang,
            "-exit-on-inactivity",
            f"{int(self.scraper_timeout)}s",
        ]

        if "radius" in supported_flags:
            args.extend(["-radius", str(self.scraper_radius)])
        elif self.scraper_radius:
            self._warning(
                "This scraper build does not support -radius; continuing without a radius override.",
                False,
            )

        if geo and "geo" in supported_flags:
            args.extend(["-geo", geo])
        elif geo:
            self._warning(
                "This scraper build does not support -geo; continuing without geo targeting.",
                False,
            )

        if self.scraper_fast_mode and "fast-mode" in supported_flags:
            args.append("-fast-mode")
        elif self.scraper_fast_mode:
            self._warning(
                "This scraper build does not support -fast-mode; continuing in standard mode.",
                False,
            )

        self._info(
            f"Running Google Maps scraper for {len(queries)} query(s)"
            + (f" near {geo}" if geo else "")
            + (" in fast mode" if self.scraper_fast_mode else "")
            + "...",
            False,
        )
        self._run_command(args, timeout=self.scraper_timeout + 120)

        if not os.path.exists(results_path):
            raise FileNotFoundError(f"Expected scraper results at {results_path}")

        return results_path

    def _pick(self, row: dict[str, str], *keys: str) -> str:
        lowered = {str(key).strip().lower(): value for key, value in row.items()}
        for key in keys:
            value = lowered.get(key.lower())
            if value not in (None, ""):
                return str(value).strip()
        return ""

    def _domain(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc.lower().replace("www.", "")

    def _matches_domain_group(self, domain: str, patterns: set[str]) -> bool:
        if not domain:
            return False
        return any(domain == pattern or domain.endswith(f".{pattern}") for pattern in patterns)

    def _website_status(self, website: str) -> str:
        domain = self._domain(website)
        if not website or not domain:
            return "missing"
        if self._matches_domain_group(domain, SOCIAL_DOMAINS):
            return "social_only"
        if self._matches_domain_group(domain, MARKETPLACE_DOMAINS):
            return "marketplace_only"
        if self._matches_domain_group(domain, WEBSITE_BUILDER_DOMAINS):
            return "website_builder_only"
        return "website_present"

    def _is_missing_website(self, website: str) -> bool:
        return self._website_status(website) in {
            "missing",
            "social_only",
            "marketplace_only",
            "website_builder_only",
        }

    def _infer_city(self, address: str, query: str) -> str:
        haystack = f"{address} {query}".lower()
        for city in self.target_cities:
            if city.lower() in haystack:
                return city
        query_location = self._query_location(query)
        if query_location:
            return query_location
        return self.country

    def _query_location(self, query: str) -> str:
        lowered = normalize_text(query)
        if " in " not in lowered:
            return ""

        location = lowered.split(" in ", 1)[1]
        if self.country:
            country_value = normalize_text(self.country)
            if location.endswith(f", {country_value}"):
                location = location[: -(len(country_value) + 2)]
            elif location.endswith(country_value):
                location = location[: -len(country_value)]
        return location.strip(" ,").title()

    def _query_category(self, query: str) -> str:
        text = str(query).strip()
        lowered = text.lower()
        marker = " in "
        index = lowered.find(marker)
        if index >= 0:
            text = text[:index]
        return text.strip(" ,").title()

    def _city_priority_bonus(self, city: str) -> tuple[int, list[str]]:
        haystack = city.lower()
        for name, bonus in CITY_PRIORITY_BONUSES.items():
            if name in haystack:
                return bonus, [f"{city} is a strong commercial or tourism market"]
        return 0, []

    def _market_signal_bonus(
        self, title: str, category: str, website_status: str, review_count: int
    ) -> tuple[int, list[str]]:
        haystack = f"{title} {category}".lower()
        score = 0
        reasons: list[str] = []

        tourism_keywords = (
            "hotel",
            "resort",
            "lodge",
            "guest house",
            "camp",
            "safari",
            "tour",
        )

        is_tourism = any(keyword in haystack for keyword in tourism_keywords)

        if is_tourism and website_status == "marketplace_only":
            score += 16
            reasons.append(
                "Relies on marketplace visibility, which makes direct-booking websites easier to pitch"
            )

        if is_tourism and review_count >= 25:
            score += 10
            reasons.append("Tourism demand is already validated by reviews")

        if "whatsapp" in haystack or "call" in haystack:
            score += 4
            reasons.append("Looks suitable for a call-first conversion website")

        return score, reasons

    def _looks_high_value(self, title: str, category: str) -> tuple[int, list[str]]:
        haystack = f"{title} {category}".lower()
        score = 0
        reasons = []

        for keyword, bonus in HIGH_VALUE_KEYWORDS.items():
            if keyword in haystack:
                score = max(score, bonus)
                reasons = [f"Fits a higher-value niche ({keyword})"]

        if not reasons:
            reasons = ["Business type could still be sellable with the right pitch"]
            score = 8

        return score, reasons

    def _score_lead(
        self,
        title: str,
        category: str,
        city: str,
        phone: str,
        website_status: str,
        review_count: int,
        review_rating: float,
        has_description: bool,
    ) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []

        niche_score, niche_reasons = self._looks_high_value(title, category)
        score += niche_score
        reasons.extend(niche_reasons)

        city_score, city_reasons = self._city_priority_bonus(city)
        score += city_score
        reasons.extend(city_reasons)

        if phone:
            score += 20
            reasons.append("Phone number available for cold calling")

        if website_status == "missing":
            score += 28
            reasons.append("No website listed")
        elif website_status == "social_only":
            score += 18
            reasons.append("Only social links found, no owned website")
        elif website_status == "marketplace_only":
            score += 16
            reasons.append("Depends on marketplace listings instead of an owned website")
        elif website_status == "website_builder_only":
            score += 12
            reasons.append("Uses a weak builder or link page instead of a strong owned website")

        if review_count >= 75:
            score += 18
            reasons.append("Strong review volume suggests steady demand")
        elif review_count >= 20:
            score += 12
            reasons.append("Healthy review count suggests the business is active")
        elif review_count >= 5:
            score += 6
            reasons.append("Some reviews already signal market traction")

        if review_rating >= 4.6:
            score += 12
            reasons.append("Very strong review rating")
        elif review_rating >= 4.2:
            score += 8
            reasons.append("Good review rating")
        elif review_rating >= 3.8:
            score += 4
            reasons.append("Acceptable review rating")

        if has_description:
            score += 4
            reasons.append("Profile has enough detail to personalize outreach")

        market_score, market_reasons = self._market_signal_bonus(
            title=title,
            category=category,
            website_status=website_status,
            review_count=review_count,
        )
        score += market_score
        reasons.extend(market_reasons)

        return score, reasons

    def _query_from_input_id(self, input_id: str, queries: list[str]) -> str:
        index = parse_int(input_id, -1)
        if 0 <= index < len(queries):
            return queries[index]
        if 1 <= index <= len(queries):
            return queries[index - 1]
        if len(queries) == 1:
            return queries[0]
        return ""

    def _lead_id(self, title: str, phone: str, address: str) -> str:
        fingerprint = "|".join(
            [normalize_business_name(title), phone.strip(), normalize_text(address)]
        )
        return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]

    def _lead_cluster_key(
        self, title: str, phone: str, address: str, city: str, website: str
    ) -> str:
        if phone:
            return f"phone:{phone}"

        normalized_name = normalize_business_name(title)
        normalized_city = normalize_text(city)
        normalized_domain = self._domain(website)

        if normalized_name and normalized_domain:
            return f"name-domain:{normalized_name}|{normalized_domain}"
        if normalized_name and normalized_city:
            return f"name-city:{normalized_name}|{normalized_city}"
        return f"name-address:{normalized_name}|{normalize_text(address)}"

    def _merge_duplicate(
        self,
        current: dict[str, object],
        incoming: dict[str, object],
    ) -> dict[str, object]:
        current_queries = [
            item
            for item in [str(query).strip() for query in current.get("matched_queries", [])]
            if item
        ]
        incoming_queries = [
            item
            for item in [str(query).strip() for query in incoming.get("matched_queries", [])]
            if item
        ]
        merged_queries = list(dict.fromkeys(current_queries + incoming_queries))

        current_names = [
            item
            for item in [str(name).strip() for name in current.get("duplicate_names", [])]
            if item
        ]
        incoming_names = [
            item
            for item in [str(name).strip() for name in incoming.get("duplicate_names", [])]
            if item
        ]
        merged_names = list(dict.fromkeys(current_names + incoming_names))

        if int(incoming.get("score", 0)) > int(current.get("score", 0)):
            primary = dict(incoming)
            secondary = current
        else:
            primary = dict(current)
            secondary = incoming

        duplicate_count = int(current.get("duplicate_count", 1)) + int(
            incoming.get("duplicate_count", 1)
        )
        reason_tail = [
            item
            for item in [str(reason).strip() for reason in secondary.get("score_reasons", [])]
            if item
        ]
        score_reasons = list(
            dict.fromkeys(
                [str(reason).strip() for reason in primary.get("score_reasons", []) if str(reason).strip()]
                + reason_tail
            )
        )[:6]

        primary["duplicate_count"] = duplicate_count
        primary["duplicate_names"] = merged_names
        primary["matched_queries"] = merged_queries
        primary["score_reasons"] = score_reasons

        if not str(primary.get("phone", "")).strip():
            primary["phone"] = str(secondary.get("phone", "")).strip()
        if str(primary.get("website_status")) == "missing" and str(
            secondary.get("website", "")
        ).strip():
            primary["website"] = str(secondary.get("website", "")).strip()
            primary["website_status"] = str(secondary.get("website_status", "missing"))
        if not str(primary.get("description", "")).strip():
            primary["description"] = str(secondary.get("description", "")).strip()
        if not str(primary.get("maps_link", "")).strip():
            primary["maps_link"] = str(secondary.get("maps_link", "")).strip()

        return primary

    def _normalize_lead(
        self, row: dict[str, str], query: str
    ) -> dict[str, str | int | float | list[str]]:
        title = self._pick(row, "title", "name")
        category = self._pick(row, "category")
        if not category:
            category = self._query_category(query)
        address = self._pick(row, "complete_address", "address")
        website = self._pick(row, "website")
        phone = normalize_phone(self._pick(row, "phone"))
        description = self._pick(row, "descriptions", "description")
        review_count = parse_int(self._pick(row, "review_count"), 0)
        review_rating = parse_float(self._pick(row, "review_rating"), 0.0)
        link = self._pick(row, "link", "maps_link")
        city = self._infer_city(address, query)

        website_status = self._website_status(website)
        score, reasons = self._score_lead(
            title=title,
            category=category,
            city=city,
            phone=phone,
            website_status=website_status,
            review_count=review_count,
            review_rating=review_rating,
            has_description=bool(description),
        )

        return {
            "id": self._lead_id(title, phone, address),
            "business_name": title,
            "normalized_business_name": normalize_business_name(title),
            "category": category,
            "city": city,
            "country": self.country,
            "address": address,
            "phone": phone,
            "website": website,
            "website_status": website_status,
            "review_count": review_count,
            "review_rating": review_rating,
            "maps_link": link,
            "description": description,
            "source_query": query,
            "matched_queries": [query] if query else [],
            "score": score,
            "score_reasons": reasons[:5],
            "duplicate_count": 1,
            "duplicate_names": [title] if title else [],
            "status": "new",
            "notes": "",
            "proposal_path": "",
            "build_package_path": "",
            "created_at": current_timestamp(),
            "updated_at": current_timestamp(),
        }

    def _passes_filters(self, lead: dict[str, object]) -> bool:
        if self.must_have_phone and not str(lead.get("phone", "")).strip():
            return False

        if self.require_missing_website and not self._is_missing_website(
            str(lead.get("website", ""))
        ):
            return False

        review_count = int(lead.get("review_count", 0))
        review_rating = float(lead.get("review_rating", 0.0))
        has_review_signal = review_count > 0 or review_rating > 0

        if has_review_signal or not self.scraper_fast_mode:
            if review_count < self.minimum_review_count:
                return False

            if review_rating < self.minimum_rating:
                return False

        return True

    def discover_leads(self) -> list[dict[str, object]]:
        queries = self.build_queries()
        if not queries:
            raise RuntimeError("No target queries could be built from config.json")

        self._success(f"Prepared {len(queries)} search queries.")
        deduped_leads: dict[str, dict[str, object]] = {}
        raw_row_count = 0
        qualified_row_count = 0

        for label, batch_queries, geo in self._scrape_batches(queries):
            results_path = self._run_scraper(
                batch_queries,
                geo=geo,
                results_suffix=label if len(queries) != len(batch_queries) else "",
            )

            with open(results_path, "r", encoding="utf-8", errors="ignore") as file:
                raw_rows = list(csv.DictReader(file))

            raw_row_count += len(raw_rows)
            for row in raw_rows:
                query = self._query_from_input_id(
                    self._pick(row, "input_id"), batch_queries
                )
                lead = self._normalize_lead(row, query)

                if not lead["business_name"]:
                    continue
                if not self._passes_filters(lead):
                    continue
                qualified_row_count += 1
                cluster_key = self._lead_cluster_key(
                    str(lead["business_name"]),
                    str(lead.get("phone", "")),
                    str(lead.get("address", "")),
                    str(lead.get("city", "")),
                    str(lead.get("website", "")),
                )
                existing = deduped_leads.get(cluster_key)
                if existing is None:
                    deduped_leads[cluster_key] = dict(lead)
                else:
                    deduped_leads[cluster_key] = self._merge_duplicate(existing, lead)

        if raw_row_count == 0:
            self._warning("The scraper returned no rows.")
            return []

        normalized_leads = list(deduped_leads.values())
        stored = upsert_leads(normalized_leads)
        duplicate_total = qualified_row_count - len(normalized_leads)
        self._success(
            f"Saved {len(normalized_leads)} qualified leads."
            + (f" Merged {duplicate_total} duplicates." if duplicate_total > 0 else "")
        )
        return stored

    def get_leads(self, status_filter: str = "") -> list[dict[str, object]]:
        leads = load_leads()
        if status_filter:
            leads = [lead for lead in leads if lead.get("status") == status_filter]
        return sorted(
            leads,
            key=lambda item: (item.get("score", 0), item.get("review_count", 0)),
            reverse=True,
        )

    def show_leads(self, limit: int = 20, status_filter: str = "") -> None:
        leads = self.get_leads(status_filter=status_filter)[:limit]
        if not leads:
            self._warning("No leads found for that filter.", False)
            return

        table = PrettyTable()
        table.field_names = [
            "ID",
            "Business",
            "City",
            "Category",
            "Phone",
            "Website",
            "Score",
            "Status",
        ]

        for lead in leads:
            table.add_row(
                [
                    lead["id"],
                    str(lead["business_name"])[:28],
                    lead["city"],
                    str(lead["category"])[:20],
                    lead["phone"],
                    lead["website_status"],
                    lead["score"],
                    lead["status"],
                ]
            )

        print(table)

    def _suggested_pages(self, lead: dict[str, object]) -> list[str]:
        category = str(lead.get("category", "")).lower()

        if any(term in category for term in ["hotel", "resort", "lodge", "guest", "camp"]):
            return [
                "Home",
                "Rooms and Rates",
                "Gallery",
                "Amenities",
                "Location and Nearby Attractions",
                "Reviews",
                "Contact / WhatsApp / Call CTA",
            ]

        if any(term in category for term in ["tour", "travel", "safari"]):
            return [
                "Home",
                "Tour Packages",
                "Why Book Direct",
                "Gallery",
                "Testimonials",
                "FAQ",
                "Contact / WhatsApp / Call CTA",
            ]

        return [
            "Home",
            "Services",
            "About",
            "Gallery",
            "Reviews",
            "Contact / WhatsApp / Call CTA",
        ]

    def _package_price_anchor(self, lead: dict[str, object]) -> str:
        configured = get_service_package_price_range().strip()
        if configured:
            return configured

        review_count = int(lead.get("review_count", 0))
        score = int(lead.get("score", 0))
        currency = get_target_currency()

        if score >= 95 or review_count >= 100:
            return f"{currency} 1,800-{currency} 3,500"
        if score >= 75 or review_count >= 40:
            return f"{currency} 1,200-{currency} 2,500"
        return f"{currency} 700-{currency} 1,500"

    def _fallback_build_package(self, lead: dict[str, object]) -> str:
        business_name = str(lead["business_name"])
        category = str(lead["category"] or "business")
        city = str(lead["city"])
        pages = "\n".join(f"- {page}" for page in self._suggested_pages(lead))
        features = "\n".join(f"- {item}" for item in get_service_stack())
        reasons = "\n".join(f"- {reason}" for reason in lead["score_reasons"])
        price_anchor = self._package_price_anchor(lead)

        return f"""# Build Package: {business_name}

## Project Summary
- Client: {business_name}
- Category: {category}
- City: {city}, {self.country}
- Phone: {lead["phone"]}
- Google Maps: {lead["maps_link"]}
- Current website status: {lead["website_status"]}

## Why They Bought
{reasons}

## Business Goal
Launch a mobile-first website that turns search traffic, Maps traffic, phone calls, and WhatsApp inquiries into direct bookings or direct leads without over-relying on third-party platforms.

## Recommended Sitemap
{pages}

## Recommended Features
{features}
- Sticky mobile call button
- Sticky WhatsApp CTA
- Review and trust section above the fold
- Photo-driven hero section
- Simple inquiry form

## Content Needed From Client
- Logo or business name styling preference
- Best phone and WhatsApp number
- Photos of property, staff, tours, or rooms
- Price range or package/rate information
- Best testimonials or review excerpts
- Exact location and Google Maps pin

## Suggested Offer and Scope
- Offer: {get_service_offer_name()}
- Delivery target: {get_service_turnaround_days()} days
- Price anchor: {price_anchor}

## Build Brief
Design a conversion-focused website for {business_name}, a {category.lower()} business in {city}, {self.country}. Emphasize trust, fast mobile loading, strong local positioning, click-to-call, WhatsApp conversion, clear pricing or inquiry cues, and a premium but approachable hospitality/tourism feel.

## Developer Handoff Prompt
Build a polished production-ready website for {business_name}. Use a mobile-first layout, strong CTA hierarchy, trust signals from reviews, clear location context, direct call and WhatsApp actions, and page sections tailored to a {category.lower()} in {city}, {self.country}. Keep the CMS/content model simple so the owner can update photos, prices, packages, testimonials, and contact details later.
"""

    def _generate_build_package_body(self, lead: dict[str, object]) -> str:
        model = get_active_model()
        if not model or not is_ollama_available():
            return self._fallback_build_package(lead)

        prompt = f"""
Create a markdown build package for a won web design lead.

Business name: {lead["business_name"]}
Category: {lead["category"]}
City: {lead["city"]}, {self.country}
Phone: {lead["phone"]}
Website status: {lead["website_status"]}
Review rating: {lead["review_rating"]}
Review count: {lead["review_count"]}
Google Maps link: {lead["maps_link"]}
Reasons the lead scored well: {", ".join(lead["score_reasons"])}
Offer: {get_service_offer_name()}
Turnaround: {get_service_turnaround_days()} days
Suggested features: {", ".join(get_service_stack())}
Price anchor: {self._package_price_anchor(lead)}

Return markdown with these exact sections:
1. Project Summary
2. Why They Bought
3. Business Goal
4. Recommended Sitemap
5. Recommended Features
6. Content Needed From Client
7. Suggested Offer and Scope
8. Build Brief
9. Developer Handoff Prompt

Make it practical, commercially sharp, and specific to hospitality/tourism when relevant.
"""

        try:
            content = generate_text(prompt, model_name=model)
            if content.strip():
                return f"# Build Package: {lead['business_name']}\n\n{content.strip()}"
        except Exception as exc:
            self._warning(
                f"Falling back to template build package for {lead['business_name']}: {exc}"
            )

        return self._fallback_build_package(lead)

    def _fallback_brief(self, lead: dict[str, object]) -> str:
        business_name = str(lead["business_name"])
        city = str(lead["city"])
        category = str(lead["category"] or "business")
        reasons = "\n".join(f"- {reason}" for reason in lead["score_reasons"])
        service_stack = "\n".join(f"- {item}" for item in get_service_stack())
        package_range = get_service_package_price_range() or "custom quote"

        return f"""# Website Opportunity Brief: {business_name}

## Lead Snapshot
- Business: {business_name}
- Category: {category}
- City: {city}, {self.country}
- Phone: {lead["phone"]}
- Website status: {lead["website_status"]}
- Review rating: {lead["review_rating"]} ({lead["review_count"]} reviews)
- Maps link: {lead["maps_link"]}

## Why This Lead Looks Valuable
{reasons}

## Recommended Website Direction
Build a mobile-first website focused on trust, direct calls, WhatsApp contact, and easy conversion for people researching {category.lower()} options in {city}. The message should make the business look established and easy to contact within 10 seconds.

## Suggested Pages
- Home
- About / Story
- Services or Rooms
- Gallery
- Testimonials / Reviews
- Contact / WhatsApp / Call CTA

## Suggested Features
{service_stack}

## Visual Direction
- Clean hospitality-style layout with strong hero photography
- Warm, trustworthy color palette with local context
- Sticky call / WhatsApp buttons on mobile
- Social proof above the fold

## Sales Angle
{get_outreach_angle()}

## Discovery Questions For The Prospect
- What kind of customers do you want more of right now?
- Do most people call you directly, walk in, or find you through Google Maps?
- Do you want more direct bookings or inquiries without depending on third-party platforms?
- Do you already have photos, pricing, and testimonials we can use?

## Offer Structure
- Offer: {get_service_offer_name()}
- Typical turnaround: {get_service_turnaround_days()} days
- Price range: {package_range}

## Build Handoff Prompt
Create a production-ready, mobile-first marketing website for {business_name}, a {category.lower()} in {city}, {self.country}. Prioritize trust, clear calls-to-action, click-to-call, WhatsApp contact, strong hero imagery, review-driven social proof, and a simple lead capture/contact flow.
"""

    def _generate_brief_body(self, lead: dict[str, object]) -> str:
        model = get_active_model()
        if not model or not is_ollama_available():
            return self._fallback_brief(lead)

        prompt = f"""
Create a concise markdown website strategy brief for a sales prospect.

Business name: {lead["business_name"]}
Category: {lead["category"]}
City: {lead["city"]}, {self.country}
Phone: {lead["phone"]}
Website status: {lead["website_status"]}
Rating: {lead["review_rating"]} from {lead["review_count"]} reviews
Business description: {lead["description"]}
Why we are pitching: {", ".join(lead["score_reasons"])}
Offer: {get_service_offer_name()}
Turnaround days: {get_service_turnaround_days()}
Service stack: {", ".join(get_service_stack())}
Outreach angle: {get_outreach_angle()}
Price range: {get_service_package_price_range()}

Return markdown with these exact sections:
1. Lead Snapshot
2. Opportunity Summary
3. Recommended Site Structure
4. Feature List
5. Visual Direction
6. Call Opening Script
7. Discovery Questions
8. Build Handoff Prompt

Make it practical and sales-ready. Assume the business currently lacks a proper owned website.
"""

        try:
            content = generate_text(prompt, model_name=model)
            if content.strip():
                return (
                    f"# Website Opportunity Brief: {lead['business_name']}\n\n"
                    f"{content.strip()}"
                )
        except Exception as exc:
            self._warning(
                f"Falling back to template brief for {lead['business_name']}: {exc}"
            )

        return self._fallback_brief(lead)

    def generate_briefs(self, limit: int = 10, status_filter: str = "") -> list[str]:
        leads = [
            lead
            for lead in self.get_leads(status_filter=status_filter)
            if lead.get("status") not in {"won", "lost", "do_not_call"}
        ][:limit]

        if not leads:
            self._warning("No eligible leads found for proposal generation.", False)
            return []

        generated_paths = []
        for lead in leads:
            filename = f"{slugify(str(lead['business_name']))}-{lead['id']}.md"
            file_path = os.path.join(get_proposal_output_dir(), filename)
            body = self._generate_brief_body(lead)

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(body.strip() + "\n")

            update_lead(
                str(lead["id"]),
                proposal_path=file_path,
                status="proposal_ready",
                updated_at=current_timestamp(),
            )
            generated_paths.append(file_path)
            self._success(f'Wrote proposal brief to "{file_path}"')

        return generated_paths

    def generate_build_packages(
        self, limit: int = 10, status_filter: str = "won"
    ) -> list[str]:
        leads = self.get_leads(status_filter=status_filter)[:limit]
        if not leads:
            self._warning("No eligible won leads found for build package generation.", False)
            return []

        generated_paths = []
        for lead in leads:
            filename = f"{slugify(str(lead['business_name']))}-{lead['id']}-build.md"
            file_path = os.path.join(get_build_package_output_dir(), filename)
            body = self._generate_build_package_body(lead)

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(body.strip() + "\n")

            update_lead(
                str(lead["id"]),
                build_package_path=file_path,
                updated_at=current_timestamp(),
            )
            generated_paths.append(file_path)
            self._success(f'Wrote build package to "{file_path}"')

        return generated_paths

    def generate_build_package_for_lead(self, lead_id: str) -> str | None:
        matching = [lead for lead in self.get_leads() if str(lead.get("id")) == lead_id]
        if not matching:
            self._warning("Lead ID not found for build package generation.", False)
            return None

        lead = matching[0]
        filename = f"{slugify(str(lead['business_name']))}-{lead['id']}-build.md"
        file_path = os.path.join(get_build_package_output_dir(), filename)
        body = self._generate_build_package_body(lead)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(body.strip() + "\n")

        update_lead(
            str(lead["id"]),
            build_package_path=file_path,
            updated_at=current_timestamp(),
        )
        self._success(f'Wrote build package to "{file_path}"')
        return file_path

    def export_call_sheet(self) -> str:
        leads = [
            lead
            for lead in self.get_leads()
            if lead.get("status") not in {"won", "lost", "do_not_call"}
        ]
        if not leads:
            raise RuntimeError("No leads available to export.")

        path = get_call_sheet_path()
        with open(path, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "id",
                    "business_name",
                    "city",
                    "category",
                    "phone",
                    "website_status",
                    "review_rating",
                    "review_count",
                    "score",
                    "status",
                    "quick_pitch",
                    "proposal_path",
                    "build_package_path",
                    "maps_link",
                ]
            )

            for lead in leads:
                writer.writerow(
                    [
                        lead["id"],
                        lead["business_name"],
                        lead["city"],
                        lead["category"],
                        lead["phone"],
                        lead["website_status"],
                        lead["review_rating"],
                        lead["review_count"],
                        lead["score"],
                        lead["status"],
                        "; ".join(lead["score_reasons"]),
                        lead["proposal_path"],
                        lead.get("build_package_path", ""),
                        lead["maps_link"],
                    ]
                )

        self._success(f'Exported call sheet to "{path}"')
        return path

    def update_status(
        self, lead_id: str, status: str, notes: str = ""
    ) -> dict[str, object] | None:
        payload = {
            "status": status,
            "updated_at": current_timestamp(),
        }
        if notes:
            payload["notes"] = notes
        if status == "contacted":
            payload["last_contacted_at"] = current_timestamp()

        updated = update_lead(lead_id, **payload)
        if updated:
            if status == "won" and not str(updated.get("build_package_path", "")).strip():
                self.generate_build_package_for_lead(lead_id)
            self._success(f"Updated {lead_id} to {status}.")
        else:
            self._warning("Lead ID not found.", False)
        return updated
