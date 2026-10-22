import pytest

from notas_voz.config import ConfigError, load_settings


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_loads_settings_from_tool_env_files(tmp_path, monkeypatch):
    for var in ("TELEGRAM_BOT_TOKEN", "OWNER_TELEGRAM_ID", "OWNER_EMAIL", "WHISPER_MODEL"):
        monkeypatch.delenv(var, raising=False)
    write(tmp_path / "01-TOOLS/telegram/.env", "TELEGRAM_BOT_TOKEN=abc\nOWNER_TELEGRAM_ID=42\n")
    write(tmp_path / "01-TOOLS/google/.env", "OWNER_EMAIL=yo@example.com\n")
    s = load_settings(tmp_path)
    assert s.telegram_token == "abc"
    assert s.owner_id == 42
    assert s.owner_email == "yo@example.com"
    assert s.whisper_model == "small"
    assert s.data_dir == tmp_path / "data"
    assert s.google_client_secret == tmp_path / "01-TOOLS/google/keys/client_secret.json"
    assert s.google_token == tmp_path / "01-TOOLS/google/keys/token.json"


def test_missing_value_gives_clear_spanish_error(tmp_path, monkeypatch):
    for var in ("TELEGRAM_BOT_TOKEN", "OWNER_TELEGRAM_ID", "OWNER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    write(tmp_path / "01-TOOLS/telegram/.env", "OWNER_TELEGRAM_ID=42\n")
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        load_settings(tmp_path)


def test_owner_id_must_be_a_number(tmp_path, monkeypatch):
    for var in ("TELEGRAM_BOT_TOKEN", "OWNER_TELEGRAM_ID", "OWNER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    write(tmp_path / "01-TOOLS/telegram/.env", "TELEGRAM_BOT_TOKEN=a\nOWNER_TELEGRAM_ID=yo\n")
    write(tmp_path / "01-TOOLS/google/.env", "OWNER_EMAIL=yo@example.com\n")
    with pytest.raises(ConfigError, match="número"):
        load_settings(tmp_path)
