from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any, Callable

from config import (
    get_google_drive_enabled,
    get_google_drive_folder_id,
    get_google_drive_service_account_file,
    get_google_drive_service_account_json,
)


class DriveSync:
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self, logger: Callable[[str, str], None] | None = None) -> None:
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        if self.logger is not None:
            self.logger(level, message)

    def status(self) -> dict[str, Any]:
        enabled = get_google_drive_enabled()
        folder_id = get_google_drive_folder_id()
        service_account_json = get_google_drive_service_account_json()
        service_account_file = get_google_drive_service_account_file()

        issues: list[str] = []
        if not enabled:
            return {
                "enabled": False,
                "ready": False,
                "folder_id": folder_id,
                "message": "Drive sync is disabled.",
            }

        if not folder_id:
            issues.append("Missing GOOGLE_DRIVE_FOLDER_ID.")

        if not service_account_json and not service_account_file:
            issues.append(
                "Missing Google Drive credentials. Set GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON or GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE."
            )

        try:
            from google.oauth2 import service_account  # noqa: F401
            from googleapiclient.discovery import build  # noqa: F401
            from googleapiclient.http import MediaFileUpload  # noqa: F401
        except ImportError:
            issues.append(
                "Google Drive libraries are not installed. Run pip install -r requirements.txt."
            )

        return {
            "enabled": True,
            "ready": not issues,
            "folder_id": folder_id,
            "message": "Google Drive sync ready." if not issues else " ".join(issues),
        }

    def _credentials(self) -> Any:
        from google.oauth2 import service_account

        raw_json = get_google_drive_service_account_json()
        service_account_file = get_google_drive_service_account_file()

        if raw_json:
            info = json.loads(raw_json)
            return service_account.Credentials.from_service_account_info(
                info, scopes=self.SCOPES
            )

        if service_account_file:
            return service_account.Credentials.from_service_account_file(
                service_account_file, scopes=self.SCOPES
            )

        raise RuntimeError("Google Drive credentials are not configured.")

    def _service(self) -> Any:
        from googleapiclient.discovery import build

        return build("drive", "v3", credentials=self._credentials(), cache_discovery=False)

    def _find_existing_file(self, service: Any, folder_id: str, name: str) -> str:
        safe_name = name.replace("'", "\\'")
        query_parts = [f"name = '{safe_name}'", "trashed = false"]
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")

        response = (
            service.files()
            .list(
                q=" and ".join(query_parts),
                spaces="drive",
                fields="files(id, name)",
                pageSize=1,
            )
            .execute()
        )
        files = list(response.get("files", []))
        if not files:
            return ""
        return str(files[0].get("id", ""))

    def upload_file(self, file_path: str | Path) -> dict[str, Any]:
        status = self.status()
        if not status.get("ready"):
            raise RuntimeError(str(status.get("message", "Drive sync is not ready.")))

        from googleapiclient.http import MediaFileUpload

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        folder_id = str(status.get("folder_id", ""))
        service = self._service()
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        media = MediaFileUpload(str(path), mimetype=mime_type, resumable=False)
        existing_id = self._find_existing_file(service, folder_id, path.name)

        if existing_id:
            self._log("info", f"Updating Google Drive file for {path.name}")
            payload = (
                service.files()
                .update(
                    fileId=existing_id,
                    media_body=media,
                    body={"name": path.name},
                    fields="id, name, webViewLink, webContentLink",
                )
                .execute()
            )
        else:
            self._log("info", f"Uploading {path.name} to Google Drive")
            metadata: dict[str, Any] = {"name": path.name}
            if folder_id:
                metadata["parents"] = [folder_id]
            payload = (
                service.files()
                .create(
                    body=metadata,
                    media_body=media,
                    fields="id, name, webViewLink, webContentLink",
                )
                .execute()
            )

        return {
            "id": str(payload.get("id", "")),
            "name": str(payload.get("name", path.name)),
            "path": str(path),
            "web_view_link": str(payload.get("webViewLink", "")),
            "web_content_link": str(payload.get("webContentLink", "")),
        }
