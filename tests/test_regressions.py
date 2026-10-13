"""Regression tests for input validation, CSV alignment and audit integrity."""
import csv
import math
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.base import AuditTrail
from spo2_odi import (
    analyze_spo2_recording,
    calculate_odi,
    detect_desaturation_events,
    estimate_pf_ratio_from_spo2,
    main,
    process_csv,
    spo2_fio2_ratio,
)


@pytest.mark.parametrize("bad", [-1.0, 101.0, float("nan"), float("inf")])
def test_rejects_bad_spo2(bad):
    with pytest.raises(ValueError):
        analyze_spo2_recording([95.0, bad])
    with pytest.raises(ValueError):
        spo2_fio2_ratio(bad, 0.21)


@pytest.mark.parametrize("bad", [0, -0.1, 1.1, float("nan"), float("inf")])
def test_rejects_bad_fio2(bad):
    with pytest.raises(ValueError):
        spo2_fio2_ratio(95, bad)
    with pytest.raises(ValueError):
        estimate_pf_ratio_from_spo2(95, bad)


def test_rejects_bad_odi_or_intervals():
    with pytest.raises(ValueError):
        calculate_odi(-1, 2)
    with pytest.raises(ValueError):
        calculate_odi(1, float("nan"))
    with pytest.raises(ValueError):
        detect_desaturation_events([95], sampling_interval_sec=0)
    with pytest.raises(ValueError):
        analyze_spo2_recording([95], threshold_pct=0)
    with pytest.raises(ValueError):
        analyze_spo2_recording([95], sampling_interval_sec=float("inf"))


def test_csv_rejects_irregular_or_missing_timestamps(tmp_path):
    source = tmp_path / "recording.csv"
    output = tmp_path / "summary.csv"
    source.write_text("time,spo2\n0,96\n1,92\n3,96\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Irregular"):
        process_csv(str(source), str(output), time_col="time")
    source.write_text("time,spo2\n0,96\n1,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing SpO2"):
        process_csv(str(source), str(output), time_col="time")
    assert not output.exists()


def test_csv_valid_produces_summary_and_preserves_input(tmp_path):
    source = tmp_path / "recording.csv"
    output = tmp_path / "summary.csv"
    source.write_text("time,spo2\n0,96\n1,92\n2,96\n", encoding="utf-8")
    assert process_csv(str(source), str(output), time_col="time") == 1
    with output.open(newline="", encoding="utf-8") as f:
        summary = next(csv.DictReader(f))
    assert int(summary["total_samples"]) == 3
    with pytest.raises(ValueError, match="differ"):
        process_csv(str(source), str(source))


def test_audit_signatures_and_chain_detect_tampering():
    trail = AuditTrail(secret_key="test-audit-secret")
    trail.log("test", "supervisor", "FIRST", {"task_id": "TASK-1"})
    trail.log("test", "supervisor", "SECOND", {"task_id": "TASK-2"})
    assert trail.verify_integrity()
    external = trail.get_trail()
    external[0]["event_type"] = "TAMPER"
    assert trail.verify_integrity()
    trail.logs[0]["event_type"] = "TAMPER"
    assert not trail.verify_integrity()


def test_audit_detects_replaced_signature():
    trail = AuditTrail(secret_key="test-audit-secret")
    trail.log("test", "supervisor", "FIRST", {})
    trail.logs[0]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()


def test_serve_launches_fastapi():
    with patch("uvicorn.run") as run:
        assert main(["serve", "--host", "127.0.0.1", "--port", "9090"]) == 0
    run.assert_called_once()
    args, kwargs = run.call_args
    assert kwargs["port"] == 9090
