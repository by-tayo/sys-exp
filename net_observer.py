"""
net_observer.py — online IsolationForest-based anomaly detector for
CPU/memory/network samples.

The model and its training buffer can be persisted to / loaded from disk
(`save` / `load`) so the exporter doesn't need to relearn "normal" behavior
from scratch after every restart — previously a documented known limitation.
"""

import logging
import threading
from pathlib import Path

import numpy as np
from joblib import dump
from joblib import load as joblib_load
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class NetworkObserver:
    def __init__(self, training_samples: int = 50):
        self.training_samples = training_samples
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42,
        )
        self.trained = False
        self.training_data: list[list[float]] = []
        # FastAPI runs sync route handlers in a threadpool, so concurrent
        # scrapes/API calls can call add_training_sample/detect at the same
        # time; IsolationForest.fit/predict and list mutation aren't
        # thread-safe, so serialize access to the model and its buffer.
        self._lock = threading.Lock()

    def add_training_sample(self, cpu: float, memory: float, network: float) -> None:
        with self._lock:
            self.training_data.append([cpu, memory, network])
            if len(self.training_data) >= self.training_samples:
                self.model.fit(np.array(self.training_data))
                self.trained = True

    def detect(self, cpu: float, memory: float, network: float) -> tuple[bool, str]:
        with self._lock:
            if not self.trained:
                return False, "Model not trained yet"
            prediction = self.model.predict([[cpu, memory, network]])
        if prediction[0] == -1:
            return True, "Anomalous system behavior detected"
        return False, "Normal behavior"

    def save(self, path: str | Path) -> None:
        """Persist the trained model and training buffer to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            dump(
                {
                    "model": self.model,
                    "trained": self.trained,
                    "training_data": self.training_data,
                    "training_samples": self.training_samples,
                },
                path,
            )
        logger.info("Anomaly model saved to %s", path)

    @classmethod
    def load(cls, path: str | Path) -> "NetworkObserver":
        """Load a previously persisted model.

        Returns a fresh, untrained observer if no file exists yet, or if the
        file fails to load (e.g. corrupted or written by an incompatible
        library version) — the exporter should never fail to start because
        of a bad persisted model.
        """
        path = Path(path)
        observer = cls()
        if not path.exists():
            logger.info("No persisted anomaly model found at %s; starting fresh", path)
            return observer
        try:
            state = joblib_load(path)
            observer.model = state["model"]
            observer.trained = state["trained"]
            observer.training_data = state["training_data"]
            observer.training_samples = state.get("training_samples", observer.training_samples)
            logger.info(
                "Loaded persisted anomaly model from %s (trained=%s, samples=%d)",
                path,
                observer.trained,
                len(observer.training_data),
            )
        except Exception:
            logger.exception("Failed to load anomaly model from %s; starting fresh", path)
        return observer
