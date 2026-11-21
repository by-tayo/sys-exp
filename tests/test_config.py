"""Tests for config.py's environment-driven Settings validation."""

import pytest
from pydantic import ValidationError

from config import Settings


def test_defaults_are_valid():
    settings = Settings()
    assert settings.port == 8000
    assert settings.log_level == "INFO"


def test_rejects_invalid_log_level(monkeypatch):
    monkeypatch.setenv("SYS_EXP_LOG_LEVEL", "NOT_A_LEVEL")
    with pytest.raises(ValidationError):
        Settings()


def test_rejects_out_of_range_port(monkeypatch):
    monkeypatch.setenv("SYS_EXP_PORT", "70000")
    with pytest.raises(ValidationError):
        Settings()


def test_accepts_lowercase_log_level(monkeypatch):
    monkeypatch.setenv("SYS_EXP_LOG_LEVEL", "debug")
    assert Settings().log_level == "DEBUG"
