"""Google Drive y Gmail con la cuenta del dueño.

Permisos mínimos: `drive.file` (el bot solo ve los archivos que él mismo crea) y
`gmail.send` (solo puede enviar correos, no leerlos).
"""

from __future__ import annotations

import base64
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import Any

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
]
FOLDER_MIME = "application/vnd.google-apps.folder"
DOC_MIME = "application/vnd.google-apps.document"


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class GoogleArchive:
    def __init__(self, drive: Any, root_name: str = "Transcripciones") -> None:
        self._drive = drive
        self._root_name = root_name
        self._root_id: str | None = None

    def _find_or_create_folder(self, name: str, parent: str) -> str:
        query = (
            f"name = '{_quote(name)}' and mimeType = '{FOLDER_MIME}'"
            f" and '{parent}' in parents and trashed = false"
        )
        found = (
            self._drive.files().list(q=query, fields="files(id)", spaces="drive").execute()
        ).get("files", [])
        if found:
            return found[0]["id"]
        body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent]}
        return self._drive.files().create(body=body, fields="id").execute()["id"]

    def ensure_folder(self, name: str) -> str:
        if self._root_id is None:
            self._root_id = self._find_or_create_folder(self._root_name, "root")
        return self._find_or_create_folder(name, self._root_id)

    def save(self, folder_id: str, title: str, text: str, audio_path: Path, audio_mime: str) -> str:
        from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload

        doc = (
            self._drive.files()
            .create(
                body={"name": title, "mimeType": DOC_MIME, "parents": [folder_id]},
                media_body=MediaInMemoryUpload(text.encode("utf-8"), mimetype="text/plain"),
                fields="id,webViewLink",
            )
            .execute()
        )
        extension = audio_path.suffix or mimetypes.guess_extension(audio_mime) or ""
        self._drive.files().create(
            body={"name": f"{title}{extension}", "parents": [folder_id]},
            media_body=MediaFileUpload(str(audio_path), mimetype=audio_mime),
            fields="id",
        ).execute()
        return doc["webViewLink"]


class GmailMailer:
    def __init__(self, gmail: Any) -> None:
        self._gmail = gmail

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        self._gmail.users().messages().send(userId="me", body={"raw": raw}).execute()


def load_credentials(token_path: Path) -> Any:
    """Carga el permiso guardado y lo renueva si ha caducado."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not token_path.exists():
        raise RuntimeError(
            "Falta conectar Google. Ejecuta: uv run notas-voz-conectar-google "
            "(instrucciones en 01-TOOLS/google/README.md)"
        )
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


def build_services(token_path: Path) -> tuple[GoogleArchive, GmailMailer]:
    from googleapiclient.discovery import build

    creds = load_credentials(token_path)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return GoogleArchive(drive), GmailMailer(gmail)


def connect() -> None:
    """Abre el navegador para que el dueño dé permiso a su cuenta de Google (una sola vez)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    from notas_voz.config import load_google_paths

    client_secret, token_path = load_google_paths(Path.cwd())
    if not client_secret.exists():
        raise SystemExit(
            f"No encuentro {client_secret}. Sigue los pasos de 01-TOOLS/google/README.md."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    token_path.chmod(0o600)
    print("OK — Google conectado. Ya puedes arrancar el bot.")


def check() -> None:
    """Prueba la conexión: crea la carpeta raíz en Drive y envía un correo de prueba al dueño."""
    from notas_voz.config import load_settings

    settings = load_settings(Path.cwd())
    archive, mailer = build_services(settings.google_token)
    archive.ensure_folder("Prueba de conexión")
    mailer.send(
        settings.owner_email,
        "Prueba del bot de notas de voz",
        "Si lees esto, el bot ya puede enviarte correos.",
    )
    print("OK — Drive y Gmail funcionan. Revisa tu correo y la carpeta 'Transcripciones' en Drive.")
