import numpy as np
import pandas as pd

from app.features.engineering import FEATURE_COLUMNS, LAGS, build_features, make_supervised


def test_all_feature_columns_present_and_filled(frame):
    out = build_features(frame)
    assert len(out) == len(frame)
    assert list(FEATURE_COLUMNS) == [c for c in FEATURE_COLUMNS if c in out.columns]
    assert not out[FEATURE_COLUMNS].isna().any().any()


def test_lags_point_at_the_past(frame):
    out = build_features(frame)
    for lag in LAGS:
        i = lag + 5
        assert out.loc[i, f"lag_{lag}"] == frame["total_kwh"].iloc[i - lag]


def test_rolling_stats_exclude_the_current_reading(frame):
    out = build_features(frame)
    i = 200
    window = frame["total_kwh"].iloc[i - 24 : i]
    assert abs(out.loc[i, "roll_mean_24"] - window.mean()) < 1e-12
    assert abs(out.loc[i, "roll_std_24"] - window.std()) < 1e-12


def test_cyclical_hour_encoding_lies_on_the_unit_circle(frame):
    out = build_features(frame)
    radius = out["hour_sin"] ** 2 + out["hour_cos"] ** 2
    assert np.allclose(radius, 1.0)


def test_weekend_flag_matches_calendar(frame):
    out = build_features(frame)
    expected = (out["ts"].dt.dayofweek >= 5).astype(int)
    assert (out["is_weekend"] == expected).all()


def test_input_order_does_not_matter(frame):
    shuffled = frame.sample(frac=1.0, random_state=1)
    a = build_features(frame)
    b = build_features(shuffled)
    pd.testing.assert_frame_equal(a[FEATURE_COLUMNS], b[FEATURE_COLUMNS])


def test_supervised_target_is_the_future_value(frame):
    for h in (1, 24, 168):
        sup = make_supervised(frame, h)
        assert len(sup) == len(frame) - h
        assert sup["target"].iloc[0] == frame["total_kwh"].iloc[h]
        assert (sup["naive_persistence"] == sup["total_kwh"]).all()
