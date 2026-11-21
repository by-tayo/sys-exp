"""Shared pytest fixtures for the sys-exp test suite."""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def model_path(tmp_path_factory) -> Path:
    """Shared, session-scoped location for the persisted anomaly model."""
    return tmp_path_factory.mktemp("sys-exp-tests") / "model.joblib"


@pytest.fixture(scope="session")
def main_module(model_path):
    """Import `main` exactly once for the whole test session.

    Prometheus's default CollectorRegistry is a process-global singleton, so
    re-importing `main` per test would re-register the same Gauges and raise
    "Duplicated timeseries in CollectorRegistry". Importing once here means
    the module-level `detector` persists across tests too; see
    `fresh_detector` for how individual tests get a clean model state.
    """
    os.environ["SYS_EXP_MODEL_PATH"] = str(model_path)
    import main

    return main


@pytest.fixture
def fresh_detector(main_module, model_path):
    """Remove any persisted model file so the next lifespan startup (i.e.
    the next `TestClient(main_module.app)` context) loads a fresh, untrained
    detector instead of one left over from a previous test."""
    if model_path.exists():
        model_path.unlink()
    yield
