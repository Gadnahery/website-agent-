# Configuration

Create `config.json` in the project root by copying `config.example.json`.

## Key Fields

- `country`: country you are targeting. Default is `Tanzania`.
- `target_cities`: cities to combine with each niche.
- `target_niches`: default ICP categories to search.
- `target_queries`: optional direct search queries. If this is filled, the app uses these instead of building niche + city combinations.
- `must_have_phone`: keeps only businesses that have a phone number.
- `require_missing_website`: keeps only leads that do not appear to have an owned website.
- `minimum_review_count`: minimum Google review count to keep a lead.
- `minimum_rating`: minimum Google rating to keep a lead.
- `google_maps_scraper`: ZIP URL for the scraper source.
- `scraper_timeout`: scraping timeout in seconds.
- `scraper_depth`: scraper depth flag.
- `scraper_concurrency`: scraper concurrency flag.
- `scraper_fast_mode`: enables the scraper's fast mode. This is more reliable in restricted environments, but it needs coordinates.
- `scraper_geo`: optional global coordinates in `lat,lng` format used for all queries in fast mode.
- `scraper_radius`: search radius in meters.
- `scraper_lang`: Google Maps language code.
- `city_geos`: optional map of city names to `lat,lng` coordinates. Use this when fast mode should run one batch per city.
- `service_offer_name`: the offer you are pitching.
- `service_package_price_range`: used in generated proposal briefs.
- `service_turnaround_days`: used in generated proposal briefs.
- `target_currency`: used when the agent has to infer a price anchor.
- `service_stack`: the features/services you typically sell.
- `outreach_angle`: short positioning statement used in proposal briefs.
- `proposal_output_dir`: where generated website briefs are stored.
- `build_package_output_dir`: where won-lead build packages are stored.
- `google_drive_enabled`: enables optional Google Drive uploads for generated exports.
- `google_drive_folder_id`: Drive folder ID used by the dashboard sync flow.
- `google_drive_service_account_file`: optional local path to a service account JSON file. In deployment, prefer environment variables instead.
- `ollama_base_url`: local Ollama URL.
- `ollama_model`: optional model name. Leave blank if you want template-only briefs.

## Environment Overrides

These are useful for deployment:

- `MPRINTER_DATA_DIR`: root folder for `.mp`, proposals, and build packages
- `MPRINTER_PROPOSAL_OUTPUT_DIR`: override proposal output directory
- `MPRINTER_BUILD_PACKAGE_OUTPUT_DIR`: override build package directory
- `GOOGLE_DRIVE_ENABLED`
- `GOOGLE_DRIVE_FOLDER_ID`
- `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`

## Dashboard Runtime Inputs

The dashboard can now override search settings per run without editing `config.json`.

Examples:

- locations: `Dar es Salaam`, `Arusha`, `Mwanza`
- business types: `salon`, `event hall`, `restaurant`
- direct queries: `salons in Mikocheni, Dar es Salaam`

If you provide direct queries, the agent runs those directly. Otherwise it combines the entered locations and business types into search queries.

## Example

```json
{
  "verbose": true,
  "country": "Tanzania",
  "target_cities": ["Dar es Salaam", "Arusha", "Zanzibar"],
  "target_niches": ["hotel", "resort", "lodge", "tour operator"],
  "target_queries": [],
  "must_have_phone": true,
  "require_missing_website": true,
  "minimum_review_count": 5,
  "minimum_rating": 3.8,
  "google_maps_scraper": "https://github.com/gosom/google-maps-scraper/archive/refs/tags/v1.11.0.zip",
  "scraper_timeout": 300,
  "scraper_depth": 1,
  "scraper_concurrency": 2,
  "scraper_fast_mode": false,
  "scraper_geo": "",
  "scraper_radius": 10000,
  "scraper_lang": "en",
  "city_geos": {
    "Arusha": "-3.3869,36.6830",
    "Dar es Salaam": "-6.7924,39.2083",
    "Zanzibar": "-6.1659,39.2026"
  },
  "service_offer_name": "Website design and launch package",
  "service_package_price_range": "$800-$2,500",
  "service_turnaround_days": 10,
  "target_currency": "USD",
  "service_stack": [
    "Mobile-first website design",
    "Click-to-call and WhatsApp buttons",
    "Lead form or booking inquiry form"
  ],
  "outreach_angle": "You help local Tanzania businesses turn Maps visibility and phone calls into direct bookings and better trust.",
  "proposal_output_dir": "proposals",
  "build_package_output_dir": "build-packages",
  "google_drive_enabled": false,
  "google_drive_folder_id": "",
  "google_drive_service_account_file": "",
  "ollama_base_url": "http://127.0.0.1:11434",
  "ollama_model": ""
}
```
