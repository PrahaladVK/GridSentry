import numpy as np

from app.metrics import METRIC_KEYS, regression_metrics


def test_perfect_prediction():
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    m = regression_metrics(y, y.copy(), n_features=2)
    assert m["rmse"] == 0.0
    assert m["mae"] == 0.0
    assert m["r2"] == 1.0


def test_known_values():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.0, 2.0, 4.0])
    m = regression_metrics(y_true, y_pred, n_features=1)
    assert m["mse"] == np.float64(1 / 3)
    assert abs(m["rmse"] - np.sqrt(1 / 3)) < 1e-12
    assert abs(m["mae"] - 1 / 3) < 1e-12


def test_empty_input_returns_none_for_every_metric():
    m = regression_metrics(np.array([]), np.array([]), n_features=3)
    assert set(m) == set(METRIC_KEYS)
    assert all(v is None for v in m.values())


def test_constant_target_has_no_r2():
    m = regression_metrics(np.array([2.0, 2.0, 2.0]), np.array([1.0, 2.0, 3.0]), n_features=1)
    assert m["r2"] is None
    assert m["adj_r2"] is None


def test_adjusted_r2_never_exceeds_r2():
    rng = np.random.default_rng(0)
    y = rng.normal(size=200)
    pred = y + rng.normal(0, 0.5, size=200)
    m = regression_metrics(y, pred, n_features=10)
    assert m["adj_r2"] <= m["r2"]


def test_mape_survives_zero_targets():
    m = regression_metrics(np.array([0.0, 1.0]), np.array([0.5, 1.0]), n_features=1)
    assert np.isfinite(m["mape"])
