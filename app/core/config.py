"""Limites locais de entrada e diretório de trabalho."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APEX_", extra="ignore")

    data_dir: Path = Path("data")
    max_upload_bytes: int = 200 * 1024 * 1024
    heartbeat_timeout_seconds: int = 30

    @property
    def database_path(self) -> Path:
        return self.data_dir / "jobs.sqlite"


def get_settings() -> Settings:
    return Settings()
