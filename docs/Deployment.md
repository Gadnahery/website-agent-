# Deployment

## Recommended Setup

For this project, the cleanest deployment path is:

- Frontend/dashboard: serve the current dashboard from the Python backend, or later split a separate frontend onto Vercel
- Backend and scraper worker: deploy on Render using the included `Dockerfile`
- File durability: sync exports to Google Drive so proposal files and CSV sheets are still accessible after redeploys

This works better than putting the scraper on Vercel because discovery jobs are long-running, stateful, and depend on a native binary.

## Quick Render Deploy

1. Push the repo to GitHub
2. Create a new Render Web Service from the repo
3. Choose `Docker` runtime or let Render pick up `render.yaml`
4. Set these environment variables:
   - `MPRINTER_OPEN_BROWSER=0`
   - `MPRINTER_DATA_DIR=/var/data`
   - `GOOGLE_DRIVE_ENABLED=true` if you want Drive sync
   - `GOOGLE_DRIVE_FOLDER_ID=<your folder id>`
   - `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON=<service account json>`
5. Attach a persistent disk mounted at `/var/data`
6. Make sure `config.json` exists in the deployed image with your target defaults
7. Open the deployed URL from your phone

## Google Drive Sync

The dashboard can now upload:

- exported call sheets
- scraper CSVs
- generated proposal briefs
- generated build packages

Drive sync is enabled when:

- `google_drive_enabled` is true in `config.json` or `GOOGLE_DRIVE_ENABLED=true`
- `GOOGLE_DRIVE_FOLDER_ID` is set
- one of these is provided:
  - `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`
  - `GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE`

Recommended approach:

- create a Google Cloud service account
- share the target Google Drive folder with that service account email
- store the service account JSON in a Render environment variable, not in git

## Persistent Files

The app now supports a dedicated data root through `MPRINTER_DATA_DIR`.

Use it so these folders survive redeploys:

- `.mp`
- `proposals`
- `build-packages`

On Render, the included `render.yaml` mounts a persistent disk at `/var/data` and points the app there automatically.

## Vercel

Vercel is a good fit for a future dedicated frontend, but not for the scraping backend itself.

If you later split the app:

- host the UI on Vercel
- point it at a Render API/backend
- keep scraping, file generation, and Drive upload on Render

## Phone Access

Once the backend is deployed, the dashboard is already responsive and can be used directly from a mobile browser.
