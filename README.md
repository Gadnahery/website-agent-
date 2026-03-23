# Tanzania Website Sales Agent

This repo is now focused on one thing: finding Tanzania businesses that are good website prospects, keeping the ones that have phone numbers and no proper website, and generating proposal briefs so the only manual step is outreach and, if the lead agrees, build.

## What It Does

- Builds Google Maps search queries from Tanzania cities and niches
- Accepts runtime search targets from the dashboard, including custom locations, business types, and direct search phrases
- Runs the `gosom/google-maps-scraper` binary locally
- Filters for leads with a phone number and no owned website
- Scores leads by niche fit, reviews, and likely ability to pay
- Stores the pipeline locally in `.mp/website_leads.json`
- Generates website strategy briefs in `proposals/`
- Generates won-lead build packages in `build-packages/`
- Exports a cold-calling sheet in `.mp/call_sheet.csv`
- Optionally syncs CSVs and generated files to Google Drive

## Default ICP

The default config is tuned for hospitality and tourism leads:

- Hotels
- Resorts
- Lodges
- Guest houses
- Safari lodges
- Tour operators

You can expand this by editing `target_niches` or providing direct `target_queries` in `config.json`.

## Setup

### PowerShell (Windows)

```powershell
.\scripts\setup_local.ps1
.\venv\Scripts\Activate.ps1
python src\main.py
```

Dashboard mode:

```powershell
.\venv\Scripts\python.exe src\dashboard.py
```

Deployment-friendly environment variables are listed in `.env.example`.

The dashboard now lets you enter:

- target locations like `Dar es Salaam`, `Arusha`, or specific neighborhoods
- business types like `salons`, `halls`, `clinics`, or `lodges`
- direct queries like `event halls in Kariakoo, Dar es Salaam`
- one-tap presets like Dar salons, Dar halls, and neighborhood searches

### Bash

```bash
bash scripts/setup_local.sh
source venv/bin/activate
python src/main.py
```

Manual setup also works:

1. Copy `config.example.json` to `config.json`
2. Install Python 3.12 if you want the safest target version
3. Create a virtual environment
4. Install dependencies with `pip install -r requirements.txt`
5. Install Go so the scraper can be built
6. Optionally install Ollama and set `ollama_model` if you want AI-written proposal briefs

## Run

```text
Windows: .\venv\Scripts\python.exe src\main.py
Panel:   http://127.0.0.1:5055
Bash:    ./venv/bin/python src/main.py
```

## Main Workflow

1. Discover Tanzania website leads
2. Review saved leads
3. Generate website proposal briefs
4. Export call sheet
5. Update lead status
6. Generate build packages for won leads

## Important Notes

- "Likely to pay" is a heuristic, not a guarantee
- Businesses with only social or marketplace links are treated as missing a proper owned website
- Proposal generation works without Ollama, but it falls back to a template brief
- Marking a lead as `won` auto-generates a build package if one does not already exist
- The scraper depends on the external Google Maps scraper project and on Google Maps not blocking the job
- If broad searches hang, enable `scraper_fast_mode` and set `scraper_geo` or `city_geos` in `config.json`

## Docs

- [Configuration](docs/Configuration.md)
- [Workflow](docs/TanzaniaWebsiteAgent.md)
- [Deployment](docs/Deployment.md)
- [Roadmap](docs/Roadmap.md)
