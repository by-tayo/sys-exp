"""
config.py — runtime configuration via environment variables.

All settings have defaults that preserve the exporter's original zero-config
behavior (port 8000, in-memory-first anomaly model, INFO logging). Override
any of them with an SYS_EXP_-prefixed environment variable, e.g.
SYS_EXP_PORT=9000 or SYS_EXP_LOG_LEVEL=DEBUG.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYS_EXP_", protected_namespaces=())

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: _LogLevel = "INFO"
    # Path the IsolationForest anomaly model (and its training buffer) is
    # persisted to / loaded from, so it survives exporter restarts.
    model_path: str = "data/model.joblib"
    # Number of samples collected before the anomaly model trains for the
    # first time. Matches the exporter's original hardcoded threshold.
    anomaly_training_samples: int = Field(default=50, ge=2)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        """Accept any case (SYS_EXP_LOG_LEVEL=debug) but reject real typos."""
        if isinstance(value, str):
            return value.upper()
        return value


@lru_cache
def get_settings() -> Settings:
    """Build (and cache) the process-wide Settings instance.

    Deliberately deferred rather than built at import time: a module-level
    `settings = Settings()` would read environment variables the moment
    anything merely imports `config` (e.g. to reach the `Settings` class for
    testing), which can race with code that sets SYS_EXP_* env vars just
    before importing `main` (see tests/conftest.py). Call `get_settings()`
    at the point of use instead; it resolves env vars on first call only.
    """
    return Settings()
