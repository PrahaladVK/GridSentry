import numpy as np
import pytest

from app.features.engineering import FEATURE_COLUMNS
from app.models import ensemble
from app.models.explain import top_features


@pytest.fixture(scope="module")
def bundle(frame):
    return ensemble.train_ensemble(frame, 1)


def test_blend_weights_form_a_distribution(bundle):
    w = bundle["weights"]
    assert w["gru"] > 0 and w["xgb"] > 0
    assert abs(w["gru"] + w["xgb"] - 1.0) < 1e-9


def test_the_more_accurate_model_gets_the_larger_weight(bundle):
    gru_rmse = bundle["gru"]["metrics"]["rmse"]
    xgb_rmse = bundle["xgb"]["metrics"]["rmse"]
    w = bundle["weights"]
    if gru_rmse < xgb_rmse:
        assert w["gru"] > w["xgb"]
    else:
        assert w["xgb"] >= w["gru"]


def test_blended_metrics_are_scored_on_the_blended_predictions(bundle):
    gru, xgb, w = bundle["gru"], bundle["xgb"], bundle["weights"]
    n = min(len(gru["val_pred"]), len(xgb["val_pred"]))
    blend = w["gru"] * gru["val_pred"][-n:] + w["xgb"] * xgb["val_pred"][-n:]
    expected_rmse = float(np.sqrt(np.mean((xgb["val_true"][-n:] - blend) ** 2)))
    assert abs(bundle["blended_metrics"]["rmse"] - expected_rmse) < 1e-9


def test_prediction_comes_with_an_ordered_interval(bundle, frame):
    out = ensemble.predict(bundle, frame)
    assert out["lower"] <= out["predicted"] <= out["upper"]
    assert out["predicted"] >= 0
    assert out["naive_persistence"] == round(float(frame["total_kwh"].iloc[-1]), 4)
    assert set(out["components"]) == {"gru", "xgb"}


def test_shap_returns_the_top_three_known_features(bundle, frame):
    feats = top_features(bundle["xgb"], frame)
    assert len(feats) == 3
    assert all(f["feature"] in FEATURE_COLUMNS for f in feats)
    magnitudes = [abs(f["impact"]) for f in feats]
    assert magnitudes == sorted(magnitudes, reverse=True)
