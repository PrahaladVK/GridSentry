import numpy as np

from app.anomaly.detector import control_chart_flags, detect
from app.anomaly.evaluation import evaluate_detection
from tests.helpers import make_frame


def with_spike(index: int, value: float):
    df = make_frame(500)
    df.loc[index, "total_kwh"] = value
    df.loc[index, "plug_kwh"] = value - df.loc[index, "lighting_kwh"]
    return df


def test_control_chart_flags_an_obvious_spike():
    df = with_spike(400, 2.5)
    flags = control_chart_flags(df["total_kwh"])
    assert bool(flags["flagged"].iloc[400])


def test_control_chart_leaves_quiet_data_mostly_alone():
    flags = control_chart_flags(make_frame(500)["total_kwh"])
    assert flags["flagged"].mean() < 0.02


def test_detect_marks_the_spike_as_an_anomaly_with_a_severity():
    result = detect(with_spike(420, 3.0))
    row = result.iloc[420]
    assert bool(row["is_anomaly"])
    assert row["severity"] in {"medium", "high"}
    assert row["method"] in {"control_chart", "autoencoder", "both"}


def test_detect_is_deterministic():
    df = with_spike(420, 3.0)
    a = detect(df)["is_anomaly"].to_numpy()
    b = detect(df)["is_anomaly"].to_numpy()
    assert np.array_equal(a, b)


def test_evaluation_counts_are_consistent():
    result = evaluate_detection(make_frame(600))
    assert result["n_injected"] >= 3
    assert result["true_positives"] + result["false_negatives"] == result["n_injected"]
    assert 0.0 <= result["precision"] <= 1.0
    assert 0.0 <= result["recall"] <= 1.0
    assert result["recall"] > 0.5


def test_evaluation_handles_empty_input():
    empty = make_frame(5).iloc[0:0]
    result = evaluate_detection(empty)
    assert result["n_injected"] == 0
    assert result["f1"] == 0.0
