"""Lee la configuración de 01-TOOLS/telegram/.env y 01-TOOLS/google/.env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    owner_id: int
    owner_email: str
    whisper_model: str
    data_dir: Path
    google_client_secret: Path
    google_token: Path


def _values(base: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for tool in ("telegram", "google"):
        env_file = base / "01-TOOLS" / tool / ".env"
        if env_file.exists():
            values.update({k: v for k, v in dotenv_values(env_file).items() if v})
    # Las variables del sistema tienen prioridad sobre los archivos.
    values.update({k: v for k, v in os.environ.items() if v})
    return values


def _require(values: dict[str, str], name: str, where: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ConfigError(f"Falta {name} en {where}. Mira el README de esa carpeta.")
    return value


def load_google_paths(base: Path) -> tuple[Path, Path]:
    values = _values(base)
    keys = base / "01-TOOLS" / "google" / "keys"
    client_secret = Path(values.get("GOOGLE_CLIENT_SECRET_FILE", keys / "client_secret.json"))
    token = Path(values.get("GOOGLE_TOKEN_FILE", keys / "token.json"))
    return client_secret, token


def load_settings(base: Path) -> Settings:
    values = _values(base)
    telegram_env = "01-TOOLS/telegram/.env"
    token = _require(values, "TELEGRAM_BOT_TOKEN", telegram_env)
    owner_raw = _require(values, "OWNER_TELEGRAM_ID", telegram_env)
    if not owner_raw.isdigit():
        raise ConfigError("OWNER_TELEGRAM_ID tiene que ser un número (tu número de Telegram).")
    email = _require(values, "OWNER_EMAIL", "01-TOOLS/google/.env")
    client_secret, google_token = load_google_paths(base)
    return Settings(
        telegram_token=token,
        owner_id=int(owner_raw),
        owner_email=email,
        whisper_model=values.get("WHISPER_MODEL", "small"),
        data_dir=Path(values.get("DATA_DIR", base / "data")),
        google_client_secret=client_secret,
        google_token=google_token,
    )
