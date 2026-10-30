"""Runtime configuration, read from environment variables only."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: SecretStr = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    s3_endpoint_url: str = Field(alias="S3_ENDPOINT_URL")
    s3_access_key: SecretStr = Field(alias="S3_ACCESS_KEY")
    s3_secret_key: SecretStr = Field(alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="documents", alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    jobs_key: str = Field(default="condo-audit:jobs", alias="PIPELINE_JOBS_KEY")
    max_attempts: int = Field(default=3, alias="PIPELINE_MAX_ATTEMPTS")
    retry_base_seconds: float = Field(default=5.0, alias="PIPELINE_RETRY_BASE_SECONDS")

    ocr_dpi: int = Field(default=300, alias="OCR_DPI")
    ocr_language: str = Field(default="por", alias="OCR_LANGUAGE")

    contracts_path: Path = Field(default=Path("/contracts"), alias="CONTRACTS_PATH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
