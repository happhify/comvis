"""
Test untuk EmployeeClassifier._convert_to_status - inti logic yang
menentukan apakah crop dianggap "verified" (Hadi) atau "unknown".

Model YOLO asli tidak di-load (butuh file .pt + waktu lama) - instance
dibuat lewat __new__ lalu atribut threshold diisi manual, karena
_convert_to_status hanya bergantung pada threshold, bukan model.
"""
import pytest

from src.classifier import EmployeeClassifier


def make_classifier(verified_threshold=0.97, unknown_threshold=0.70, min_margin=0.40):
    clf = EmployeeClassifier.__new__(EmployeeClassifier)
    clf.verified_threshold = verified_threshold
    clf.unknown_threshold = unknown_threshold
    clf.min_margin = min_margin
    return clf


def test_verified_when_all_conditions_met():
    clf = make_classifier()
    status = clf._convert_to_status(pred_label="hadi", confidence=0.98, margin=0.5)
    assert status == "verified"


def test_unknown_when_label_is_not_hadi():
    clf = make_classifier()
    status = clf._convert_to_status(pred_label="unknown", confidence=0.99, margin=0.9)
    assert status == "unknown"


def test_unknown_when_confidence_below_threshold():
    clf = make_classifier(verified_threshold=0.97)
    status = clf._convert_to_status(pred_label="hadi", confidence=0.70, margin=0.9)
    assert status == "unknown"


def test_unknown_when_margin_below_minimum():
    clf = make_classifier(min_margin=0.40)
    status = clf._convert_to_status(pred_label="hadi", confidence=0.99, margin=0.10)
    assert status == "unknown"


def test_boundary_confidence_exactly_at_threshold_is_verified():
    clf = make_classifier(verified_threshold=0.97, min_margin=0.40)
    status = clf._convert_to_status(pred_label="hadi", confidence=0.97, margin=0.40)
    assert status == "verified"


def test_boundary_just_below_threshold_is_unknown():
    clf = make_classifier(verified_threshold=0.97)
    status = clf._convert_to_status(pred_label="hadi", confidence=0.9699999, margin=0.9)
    assert status == "unknown"


@pytest.mark.parametrize("reason", ["empty_crop", "no_result", "no_probs", "prediction_error"])
def test_unknown_result_helper_always_returns_unknown_status(reason):
    clf = make_classifier()
    result = clf._unknown_result(reason)
    assert result["status"] == "unknown"
    assert result["raw_label"] == reason
    assert result["confidence"] == 0.0


def test_predict_returns_unknown_for_empty_crop():
    clf = make_classifier()
    result = clf.predict(None)
    assert result["status"] == "unknown"
    assert result["raw_label"] == "empty_crop"
