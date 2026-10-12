"""Limites locais de entrada."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APEX_", extra="ignore")

    max_upload_bytes: int = 200 * 1024 * 1024


def get_settings() -> Settings:
    return Settings()
