#!/usr/bin/env python3
"""
SpO2 Desaturation Index (ODI) Calculator
==========================================
Real clinical calculators for pulse oximetry analysis:

- SpO2/FiO2 ratio (surrogate for P/F ratio)
    Normal ~476 when SpO2=100%, FiO2=0.21
- Estimated PaO2 from SpO2 (Severinghaus equation approximation)
- Oxygen Desaturation Index (ODI): desaturation events per hour
    Normal: < 5 events/hour
    Mild: 5-15
    Moderate: 15-30
    Severe: > 30
- Time below SpO2 thresholds (T90, T88, T85)
- SpO2 variability metrics (mean, SD, coefficient of variation)

Stdlib only. Author: Dr. Abu Suraih Sakhri. License: MIT.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_spo2_samples(values: List[float]) -> None:
    for i, value in enumerate(values):
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError(f"SpO2 sample at index {i} must be finite and within [0, 100]")


# ---------------------------------------------------------------------------
# Core SpO2 calculations
# ---------------------------------------------------------------------------

def spo2_fio2_ratio(spo2: float, fio2: float) -> float:
    """Calculate SpO2/FiO2 ratio (surrogate for PaO2/FiO2).

    Normal ~476 when SpO2=100%, FiO2=0.21.

    Args:
        spo2: Oxygen saturation percentage (0-100).
        fio2: Fraction of inspired oxygen (0.0-1.0).

    Returns:
        S/F ratio.
    """
    if not math.isfinite(fio2) or not 0 < fio2 <= 1:
        raise ValueError("FiO2 must be finite and within (0, 1]")
    _validate_spo2_samples([spo2])
    return spo2 / fio2


def estimate_pao2_from_spo2(spo2: float) -> float:
    """Estimate PaO2 from SpO2 using a clinical approximation of the
    oxyhemoglobin dissociation curve (Severinghaus-derived).

    Piecewise linear approximation based on standard curve data points:
        SpO2 90% -> PaO2 ~60 mmHg
        SpO2 95% -> PaO2 ~80 mmHg
        SpO2 100% -> PaO2 ~100 mmHg

    For SpO2 < 90%, uses the steep portion of the curve.

    Args:
        spo2: Oxygen saturation percentage (0-100).

    Returns:
        Estimated PaO2 in mmHg.
    """
    _validate_spo2_samples([spo2])
    if spo2 >= 90.0:
        # Flat portion: PaO2 ~60 at SpO2 90, ~100 at SpO2 100
        return 60.0 + (spo2 - 90.0) * 4.0
    elif spo2 >= 80.0:
        return 44.0 + (spo2 - 80.0) * 1.6
    elif spo2 >= 70.0:
        return 37.0 + (spo2 - 70.0) * 0.7
    elif spo2 >= 50.0:
        return 27.0 + (spo2 - 50.0) * 0.5
    else:
        return max(0.0, spo2 * 0.4)


def estimate_pf_ratio_from_spo2(spo2: float, fio2: float) -> float:
    """Estimate P/F ratio from SpO2 and FiO2.

    Combines Severinghaus estimation with P/F calculation.

    Args:
        spo2: Oxygen saturation percentage (0-100).
        fio2: Fraction of inspired oxygen (0.0-1.0).

    Returns:
        Estimated P/F ratio.
    """
    pao2 = estimate_pao2_from_spo2(spo2)
    if not math.isfinite(fio2) or not 0 < fio2 <= 1:
        raise ValueError("FiO2 must be finite and within (0, 1]")
    return pao2 / fio2


# ---------------------------------------------------------------------------
# Time below threshold analysis
# ---------------------------------------------------------------------------

def time_below_threshold(spo2_values: List[float], threshold: float) -> Tuple[int, float]:
    """Count samples and percentage of time below an SpO2 threshold.

    Args:
        spo2_values: List of SpO2 readings.
        threshold: SpO2 threshold percentage.

    Returns:
        Tuple of (count_below, percent_below).
    """
    if not math.isfinite(threshold) or not 0 <= threshold <= 100:
        raise ValueError("Threshold must be finite and within [0, 100]")
    _validate_spo2_samples(spo2_values)
    if not spo2_values:
        return 0, 0.0
    count = sum(1 for s in spo2_values if s < threshold)
    return count, (count / len(spo2_values)) * 100.0


def compute_t90(spo2_values: List[float]) -> Tuple[float, float]:
    """Compute T90: time spent below SpO2 90%.

    Args:
        spo2_values: List of SpO2 readings.

    Returns:
        Tuple of (count_below_90, percent_below_90).
    """
    return time_below_threshold(spo2_values, 90.0)


def compute_t88(spo2_values: List[float]) -> Tuple[float, float]:
    """Compute T88: time spent below SpO2 88%."""
    return time_below_threshold(spo2_values, 88.0)


def compute_t85(spo2_values: List[float]) -> Tuple[float, float]:
    """Compute T85: time spent below SpO2 85%."""
    return time_below_threshold(spo2_values, 85.0)


# ---------------------------------------------------------------------------
# SpO2 variability metrics
# ---------------------------------------------------------------------------

def spo2_variability(spo2_values: List[float]) -> Dict[str, float]:
    """Calculate SpO2 variability metrics.

    Args:
        spo2_values: List of SpO2 readings.

    Returns:
        Dict with mean, median, std_dev, min, max, coefficient_of_variation.
    """
    _validate_spo2_samples(spo2_values)
    if not spo2_values:
        return {"mean": 0.0, "median": 0.0, "std_dev": 0.0,
                "min": 0.0, "max": 0.0, "coefficient_of_variation": 0.0}

    n = len(spo2_values)
    mean = sum(spo2_values) / n
    sorted_vals = sorted(spo2_values)
    if n % 2 == 0:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
    else:
        median = sorted_vals[n // 2]

    variance = sum((x - mean) ** 2 for x in spo2_values) / n
    std_dev = math.sqrt(variance)
    cv = (std_dev / mean * 100.0) if mean > 0 else 0.0

    return {
        "mean": round(mean, 2),
        "median": round(median, 2),
        "std_dev": round(std_dev, 2),
        "min": round(min(spo2_values), 2),
        "max": round(max(spo2_values), 2),
        "coefficient_of_variation": round(cv, 2),
    }


# ---------------------------------------------------------------------------
# Desaturation event detection
# ---------------------------------------------------------------------------

def detect_desaturation_events(
    spo2_values: List[float],
    sampling_interval_sec: float = 1.0,
    threshold_pct: float = 3.0,
    baseline_window: int = 100,
    min_recovery_pct: float = 1.0,
) -> List[Dict[str, Any]]:
    """Detect desaturation events from SpO2 time series.

    A desaturation event is scored when SpO2 drops by >= threshold_pct
    from a rolling baseline (max SpO2 in preceding baseline_window samples)
    and then recovers to within min_recovery_pct of baseline.

    Args:
        spo2_values: List of SpO2 readings (sequential, evenly spaced).
        sampling_interval_sec: Seconds between samples (default 1.0).
        threshold_pct: Drop threshold in % SpO2 (default 3.0, exploratory threshold).
        baseline_window: Number of samples for rolling baseline (default 100).
        min_recovery_pct: Recovery margin below baseline (default 1.0).

    Returns:
        List of event dicts with start_idx, end_idx, nadir_idx,
        baseline_spo2, nadir_spo2, depth, duration_sec.
    """
    if not math.isfinite(sampling_interval_sec) or sampling_interval_sec <= 0:
        raise ValueError("Sampling interval must be finite and positive")
    if not math.isfinite(threshold_pct) or not 0 < threshold_pct <= 100:
        raise ValueError("Desaturation threshold must be finite and within (0, 100]")
    if not isinstance(baseline_window, int) or baseline_window < 1:
        raise ValueError("Baseline window must be a positive integer")
    if not math.isfinite(min_recovery_pct) or not 0 <= min_recovery_pct < threshold_pct:
        raise ValueError("Recovery margin must be finite, nonnegative, and less than threshold")
    _validate_spo2_samples(spo2_values)
    n = len(spo2_values)
    if n == 0:
        return []

    events: List[Dict[str, Any]] = []
    in_event = False
    event_start = 0
    frozen_baseline = 0.0
    nadir_val = 0.0
    nadir_idx = 0

    for i in range(n):
        # Compute rolling baseline (max in preceding window)
        start = max(0, i - baseline_window)
        window = spo2_values[start:i]
        baseline = max(window) if window else spo2_values[i]

        if not in_event:
            if spo2_values[i] <= baseline - threshold_pct:
                in_event = True
                event_start = i
                frozen_baseline = baseline
                nadir_val = spo2_values[i]
                nadir_idx = i
        else:
            if spo2_values[i] < nadir_val:
                nadir_val = spo2_values[i]
                nadir_idx = i

            # Check recovery
            if spo2_values[i] >= frozen_baseline - min_recovery_pct:
                events.append({
                    "start_idx": event_start,
                    "end_idx": i,
                    "nadir_idx": nadir_idx,
                    "start_time_sec": event_start * sampling_interval_sec,
                    "end_time_sec": i * sampling_interval_sec,
                    "duration_sec": (i - event_start) * sampling_interval_sec,
                    "baseline_spo2": round(frozen_baseline, 1),
                    "nadir_spo2": round(nadir_val, 1),
                    "depth": round(frozen_baseline - nadir_val, 1),
                })
                in_event = False

    return events


# ---------------------------------------------------------------------------
# ODI calculation
# ---------------------------------------------------------------------------

def calculate_odi(
    num_events: int,
    recording_hours: float,
) -> float:
    """Calculate Oxygen Desaturation Index.

    ODI = number of desaturation events / hours of recording

    Args:
        num_events: Number of desaturation events detected.
        recording_hours: Total recording time in hours.

    Returns:
        ODI (events/hour).
    """
    if not isinstance(num_events, int) or isinstance(num_events, bool) or num_events < 0:
        raise ValueError("Event count must be a nonnegative integer")
    if not math.isfinite(recording_hours) or recording_hours <= 0:
        raise ValueError("Recording duration must be finite and positive")
    return num_events / recording_hours


def odi_severity(odi: float) -> str:
    """Classify ODI severity.

    Args:
        odi: Oxygen Desaturation Index.

    Returns:
        Severity category string.
    """
    if not math.isfinite(odi) or odi < 0:
        raise ValueError("ODI must be finite and nonnegative")
    if odi < 5:
        return "Normal (< 5 events/hour)"
    elif odi < 15:
        return "Mild (5 to <15 events/hour)"
    elif odi < 30:
        return "Moderate (15 to <30 events/hour)"
    else:
        return "Severe (>=30 events/hour)"


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def analyze_spo2_recording(
    spo2_values: List[float],
    sampling_interval_sec: float = 1.0,
    threshold_pct: float = 3.0,
    fio2: Optional[float] = None,
) -> Dict[str, Any]:
    """Complete SpO2 recording analysis.

    Args:
        spo2_values: List of SpO2 readings.
        sampling_interval_sec: Seconds between samples.
        threshold_pct: Desaturation threshold (%).
        fio2: FiO2 if known (for S/F ratio calculation).

    Returns:
        Dict with all computed metrics.
    """
    if not spo2_values:
        return {"error": "No SpO2 data provided"}
    _validate_spo2_samples(spo2_values)
    if not math.isfinite(sampling_interval_sec) or sampling_interval_sec <= 0:
        raise ValueError("Sampling interval must be finite and positive")
    if fio2 is not None and (not math.isfinite(fio2) or not 0 < fio2 <= 1):
        raise ValueError("FiO2 must be finite and within (0, 1]")

    n = len(spo2_values)
    total_seconds = n * sampling_interval_sec
    recording_hours = total_seconds / 3600.0

    # Variability
    variability = spo2_variability(spo2_values)

    # Time below thresholds
    t90_count, t90_pct = compute_t90(spo2_values)
    t88_count, t88_pct = compute_t88(spo2_values)
    t85_count, t85_pct = compute_t85(spo2_values)

    # Desaturation events
    events = detect_desaturation_events(
        spo2_values, sampling_interval_sec, threshold_pct,
    )

    # ODI
    odi = calculate_odi(len(events), recording_hours) if recording_hours > 0 else 0.0

    result: Dict[str, Any] = {
        "total_samples": n,
        "recording_duration_sec": round(total_seconds, 1),
        "recording_duration_hours": round(recording_hours, 2),
        "sampling_interval_sec": sampling_interval_sec,
        "desaturation_threshold_pct": threshold_pct,
        "variability": variability,
        "t90": {"count": t90_count, "percent": round(t90_pct, 2)},
        "t88": {"count": t88_count, "percent": round(t88_pct, 2)},
        "t85": {"count": t85_count, "percent": round(t85_pct, 2)},
        "num_desaturation_events": len(events),
        "odi": round(odi, 1),
        "odi_severity": odi_severity(odi),
        "events": events[:50],  # limit output for large recordings
    }

    # S/F ratio if FiO2 known
    if fio2 is not None:
        mean_spo2 = variability["mean"]
        result["spo2_fio2_ratio"] = round(spo2_fio2_ratio(mean_spo2, fio2), 1)
        result["estimated_pf_ratio"] = round(estimate_pf_ratio_from_spo2(mean_spo2, fio2), 1)
        result["estimated_pao2"] = round(estimate_pao2_from_spo2(mean_spo2), 1)

    return result


# ---------------------------------------------------------------------------
# CSV processing
# ---------------------------------------------------------------------------

def _safe_resolve_path(path_str: str) -> str:
    """Normalize a local CLI file path (not a filesystem sandbox)."""
    import os.path
    resolved = os.path.realpath(os.path.abspath(path_str))
    return resolved


def process_csv(input_path: str, output_path: str, spo2_col: str = "spo2",
                time_col: Optional[str] = None, sampling_rate: float = 1.0,
                threshold: float = 3.0, fio2: Optional[float] = None) -> int:
    """Read an evenly sampled CSV and write a single-row analysis summary.

    Time values, when supplied, are elapsed seconds and must be increasing
    at a constant interval (within a 1% tolerance). Missing readings and
    timestamp/SpO2 mismatches are rejected rather than silently realigned.
    """
    input_path = _safe_resolve_path(input_path)
    output_path = _safe_resolve_path(output_path)
    if input_path == output_path:
        raise ValueError("Output path must differ from input path")
    if not math.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError("Sampling rate must be finite and positive")

    spo2_values: List[float] = []
    time_values: List[float] = []
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or spo2_col not in reader.fieldnames:
            raise ValueError(f"Missing SpO2 column: {spo2_col}")
        if time_col and time_col not in reader.fieldnames:
            raise ValueError(f"Missing time column: {time_col}")
        for line, row in enumerate(reader, start=2):
            val = row.get(spo2_col)
            if val is None or not str(val).strip():
                raise ValueError(f"Missing SpO2 value at CSV row {line}")
            try:
                spo2_values.append(float(val))
            except ValueError as exc:
                raise ValueError(f"Invalid SpO2 value at CSV row {line}") from exc
            if time_col:
                tv = row.get(time_col)
                if tv is None or not str(tv).strip():
                    raise ValueError(f"Missing time value at CSV row {line}")
                try:
                    time_values.append(float(tv))
                except ValueError as exc:
                    raise ValueError(f"Invalid time value at CSV row {line}") from exc

    sampling_interval = 1.0 / sampling_rate
    if time_values and any(not math.isfinite(t) for t in time_values):
        raise ValueError("Times must be finite")
    if len(time_values) >= 2:
        intervals = [b - a for a, b in zip(time_values, time_values[1:])]
        if any(dt <= 0 for dt in intervals):
            raise ValueError("Times must be strictly increasing")
        sampling_interval = sum(intervals) / len(intervals)
        if any(abs(dt - sampling_interval) > sampling_interval * 0.01 for dt in intervals):
            raise ValueError("Irregular timestamps are not supported; resample before analysis")

    result = analyze_spo2_recording(spo2_values, sampling_interval, threshold, fio2)
    if "error" in result:
        raise ValueError(result["error"])

    summary = {k: v for k, v in result.items() if k != "events"}
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spo2_odi",
        description="SpO2 Desaturation Index Calculator — ODI, T90, variability, S/F ratio.",
    )
    sub = p.add_subparsers(dest="cmd")

    # Analyze CSV
    a = sub.add_parser("analyze", help="Analyze SpO2 recording from CSV")
    a.add_argument("input", help="Input CSV path")
    a.add_argument("--spo2-col", default="spo2", help="SpO2 column name")
    a.add_argument("--time-col", default=None, help="Time column name")
    a.add_argument("--sampling-rate", type=float, default=1.0, help="Sampling rate (Hz)")
    a.add_argument("--threshold", type=float, default=3.0, help="Desaturation threshold (%%)")
    a.add_argument("--fio2", type=float, default=None, help="FiO2 (0.0-1.0)")
    a.add_argument("-o", "--output", default=None, help="Output summary CSV")

    # Quick ODI
    q = sub.add_parser("odi", help="Quick ODI calculation")
    q.add_argument("--events", type=int, required=True, help="Number of desaturation events")
    q.add_argument("--hours", type=float, required=True, help="Recording duration (hours)")

    # S/F ratio
    sf = sub.add_parser("sf", help="Calculate SpO2/FiO2 ratio")
    sf.add_argument("--spo2", type=float, required=True, help="SpO2 (%%)")
    sf.add_argument("--fio2", type=float, required=True, help="FiO2 (0.0-1.0)")

    # Estimate PaO2
    ep = sub.add_parser("estimate-pao2", help="Estimate PaO2 from SpO2")
    ep.add_argument("--spo2", type=float, required=True, help="SpO2 (%%)")

    # Audit - log an audit event
    audit = sub.add_parser("audit", help="Log an audit event")
    audit.add_argument("--task-id", required=True, help="Task identifier for the audit event")

    # Chat - interactive LLM query
    chat = sub.add_parser("chat", help="Query the LLM reasoning adapter")
    chat.add_argument("query", nargs="+", help="Query text for the LLM")

    # Verify audit trail integrity
    sub.add_parser("verify-audit", help="Verify HMAC-SHA256 audit trail integrity")

    # Serve - start FastAPI web server
    serve = sub.add_parser("serve", help="Start FastAPI web server")
    serve.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    serve.add_argument("--port", type=int, default=8000, help="Port to bind to")

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "analyze":
        import os.path
        root, _ext = os.path.splitext(args.input)
        out = args.output or root + "_summary.csv"
        n = process_csv(args.input, out, args.spo2_col, args.time_col,
                        args.sampling_rate, args.threshold, args.fio2)
        print(f"Analysis complete -> {out}")
        return 0

    if args.cmd == "odi":
        odi = calculate_odi(args.events, args.hours)
        print(json.dumps({
            "odi": round(odi, 1),
            "severity": odi_severity(odi),
            "events": args.events,
            "hours": args.hours,
        }, indent=2))
        return 0

    if args.cmd == "sf":
        sf = spo2_fio2_ratio(args.spo2, args.fio2)
        est_pf = estimate_pf_ratio_from_spo2(args.spo2, args.fio2)
        print(json.dumps({
            "spo2_fio2_ratio": round(sf, 1),
            "estimated_pf_ratio": round(est_pf, 1),
        }, indent=2))
        return 0

    if args.cmd == "estimate-pao2":
        pao2 = estimate_pao2_from_spo2(args.spo2)
        print(json.dumps({"spo2": args.spo2, "estimated_pao2": round(pao2, 1)}, indent=2))
        return 0

    if args.cmd == "audit":
        from agents.base import AuditLogger
        entry = AuditLogger.log(
            actor="cli",
            actor_tier="operator",
            event_type="MANUAL_AUDIT",
            details={"task_id": args.task_id}
        )
        print(json.dumps(entry, indent=2))
        return 0

    if args.cmd == "chat":
        from agents.llm_factory import LLMFactory
        llm = LLMFactory.create("mock")
        query = " ".join(args.query)
        response = llm.invoke(query)
        print(json.dumps({"query": query, "response": response}, indent=2))
        return 0

    if args.cmd == "verify-audit":
        from agents.base import AuditLogger
        valid = AuditLogger.verify_integrity()
        trail = AuditLogger.get_trail()
        print(json.dumps({
            "integrity_valid": valid,
            "trail_length": len(trail),
        }, indent=2))
        return 0

    if args.cmd == "serve":
        try:
            import uvicorn
            from agents.api import app
        except ImportError as exc:
            print("Server dependencies missing. Install requirements.txt.", file=sys.stderr)
            return 1
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
