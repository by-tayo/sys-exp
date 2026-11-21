"""Tests for net_observer.py's IsolationForest-based anomaly detector."""

from net_observer import NetworkObserver


def test_detect_before_training_returns_not_trained():
    observer = NetworkObserver(training_samples=5)
    detected, reason = observer.detect(10, 20, 30)
    assert detected is False
    assert reason == "Model not trained yet"


def test_training_threshold_triggers_fit():
    observer = NetworkObserver(training_samples=3)
    assert observer.trained is False
    observer.add_training_sample(1, 1, 1)
    observer.add_training_sample(1, 1, 1)
    assert observer.trained is False
    observer.add_training_sample(1, 1, 1)
    assert observer.trained is True


def test_detect_flags_outlier_after_training():
    # Fixed, slightly-jittered samples around a steady baseline (CPU/memory/
    # network readings are never bit-for-bit identical in practice). Training
    # IsolationForest on truly identical points is degenerate — every feature
    # has zero variance, so no split can separate "normal" from anything else
    # and even a wildly different point scores as an inlier. These literal
    # values were generated once from a seeded RNG and pinned here so the
    # test is fully deterministic.
    observer = NetworkObserver(training_samples=20)
    jittered_samples = [
        [12.54, 19.07, 1001.64],
        [10.61, 18.42, 1000.1],
        [10.0, 16.49, 1050.88],
        [10.9, 18.75, 991.42],
        [10.76, 19.48, 987.86],
        [7.82, 21.11, 1006.19],
        [10.41, 16.95, 1082.53],
        [10.23, 19.23, 1101.45],
        [9.93, 17.1, 979.74],
        [6.57, 22.1, 979.18],
        [8.89, 22.14, 917.45],
        [10.8, 15.87, 966.89],
        [8.19, 22.92, 1088.31],
        [9.51, 21.68, 991.0],
        [10.85, 18.49, 914.58],
        [7.3, 20.77, 1112.38],
        [10.4, 18.95, 1095.6],
        [10.36, 20.2, 1012.63],
        [9.8, 19.38, 928.25],
        [10.75, 19.81, 1059.65],
    ]
    for cpu, memory, network in jittered_samples:
        observer.add_training_sample(cpu, memory, network)
    assert observer.trained is True

    detected, reason = observer.detect(10.0, 20.0, 1000.0)
    assert detected is False
    assert reason == "Normal behavior"

    detected, reason = observer.detect(99.0, 99.0, 999_999_999.0)
    assert detected is True
    assert reason == "Anomalous system behavior detected"


def test_save_and_load_round_trip(tmp_path):
    observer = NetworkObserver(training_samples=3)
    observer.add_training_sample(1, 2, 3)
    observer.add_training_sample(4, 5, 6)
    observer.add_training_sample(7, 8, 9)
    assert observer.trained is True

    path = tmp_path / "model.joblib"
    observer.save(path)
    assert path.exists()

    loaded = NetworkObserver.load(path)
    assert loaded.trained is True
    assert loaded.training_data == observer.training_data
    assert loaded.training_samples == 3


def test_load_missing_file_returns_fresh_observer(tmp_path):
    path = tmp_path / "does-not-exist.joblib"
    observer = NetworkObserver.load(path)
    assert observer.trained is False
    assert observer.training_data == []


def test_load_corrupted_file_returns_fresh_observer(tmp_path):
    path = tmp_path / "corrupt.joblib"
    path.write_bytes(b"not a valid joblib file")
    observer = NetworkObserver.load(path)
    assert observer.trained is False
