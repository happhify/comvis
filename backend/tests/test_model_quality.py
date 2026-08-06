import csv

from app import model_quality


# ============================================================
# read_thresholds
# ============================================================

def test_read_thresholds_missing_file_returns_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(model_quality, "CONFIG_PATH", tmp_path / "nope.yaml")
    assert model_quality.read_thresholds() == {"available": False}


def test_read_thresholds_reads_values_from_yaml(tmp_path, monkeypatch):
    config_path = tmp_path / "camera.yaml"
    config_path.write_text(
        "recognition:\n"
        "  verified_threshold: 0.97\n"
        "  unknown_threshold: 0.7\n"
        "  min_margin: 0.4\n"
        "detection:\n"
        "  confidence_threshold: 0.35\n"
        "realtime:\n"
        "  recognition_interval: 10\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(model_quality, "CONFIG_PATH", config_path)

    result = model_quality.read_thresholds()

    assert result["available"] is True
    assert result["verified_threshold"] == 0.97
    assert result["detection_confidence"] == 0.35
    assert result["recognition_interval"] == 10


# ============================================================
# read_negative_test / read_positive_test
# ============================================================

def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_read_negative_test_missing_file_returns_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(model_quality, "NEGATIVE_SUMMARY", tmp_path / "nope.csv")
    assert model_quality.read_negative_test() == {"available": False}


def test_read_negative_test_uses_last_row(tmp_path, monkeypatch):
    path = tmp_path / "negative.csv"
    header = ["generated_at", "target_label", "total_detection_rows",
              "total_verified_target", "false_positive_candidate",
              "false_positive_rate", "evaluation_status",
              "log_start_time", "log_end_time"]
    write_csv(path, header, [
        ["2026-08-01 00:00:00", "hadi", "100", "0", "0", "0.0", "done", "t0", "t1"],
        ["2026-08-05 00:00:00", "hadi", "200", "0", "3", "0.015", "done", "t2", "t3"],
    ])
    monkeypatch.setattr(model_quality, "NEGATIVE_SUMMARY", path)

    result = model_quality.read_negative_test()

    assert result["available"] is True
    assert result["generated_at"] == "2026-08-05 00:00:00"  # baris terakhir, bukan pertama
    assert result["false_positive_candidate"] == 3


def test_read_positive_test_missing_file_returns_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(model_quality, "POSITIVE_SUMMARY", tmp_path / "nope.csv")
    assert model_quality.read_positive_test() == {"available": False}


# ============================================================
# build_verdict
# ============================================================

def test_verdict_crit_when_false_positive_and_positive_test_not_done(monkeypatch):
    monkeypatch.setattr(model_quality, "POSITIVE_TEST_DONE", False)
    verdict = model_quality.build_verdict(
        negative={"available": True, "false_positive_candidate": 2},
        positive={"available": False},
    )
    assert verdict["level"] == "crit"


def test_verdict_warn_when_positive_test_not_done_and_no_false_positive(monkeypatch):
    monkeypatch.setattr(model_quality, "POSITIVE_TEST_DONE", False)
    verdict = model_quality.build_verdict(
        negative={"available": True, "false_positive_candidate": 0},
        positive={"available": False},
    )
    assert verdict["level"] == "warn"


def test_verdict_crit_when_positive_test_done_but_false_positive_found(monkeypatch):
    monkeypatch.setattr(model_quality, "POSITIVE_TEST_DONE", True)
    verdict = model_quality.build_verdict(
        negative={"available": True, "false_positive_candidate": 1},
        positive={"available": True},
    )
    assert verdict["level"] == "crit"


def test_verdict_ok_when_positive_test_done_and_no_false_positive(monkeypatch):
    monkeypatch.setattr(model_quality, "POSITIVE_TEST_DONE", True)
    verdict = model_quality.build_verdict(
        negative={"available": True, "false_positive_candidate": 0},
        positive={"available": True},
    )
    assert verdict["level"] == "ok"


def test_verdict_treats_unavailable_negative_test_as_no_false_positive(monkeypatch):
    monkeypatch.setattr(model_quality, "POSITIVE_TEST_DONE", True)
    verdict = model_quality.build_verdict(
        negative={"available": False},
        positive={"available": True},
    )
    assert verdict["level"] == "ok"


# ============================================================
# get_model_quality - integrasi ringan
# ============================================================

def test_get_model_quality_reports_positive_test_done_flag(monkeypatch, tmp_path):
    monkeypatch.setattr(model_quality, "POSITIVE_TEST_DONE", False)
    monkeypatch.setattr(model_quality, "CONFIG_PATH", tmp_path / "nope.yaml")
    monkeypatch.setattr(model_quality, "NEGATIVE_SUMMARY", tmp_path / "nope.csv")
    monkeypatch.setattr(model_quality, "POSITIVE_SUMMARY", tmp_path / "nope.csv")

    result = model_quality.get_model_quality()

    assert result["positive_test_done"] is False
    assert result["thresholds"]["available"] is False
    assert result["verdict"]["level"] == "warn"
