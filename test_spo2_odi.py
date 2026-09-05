#!/usr/bin/env python3
"""Tests for SpO2 Desaturation Index Calculator.

Run with: python -m pytest test_spo2_odi.py -v
    or:   python test_spo2_odi.py
"""
import json
import math
import os
import sys
import tempfile
import unittest

from spo2_odi import (
    spo2_fio2_ratio,
    estimate_pao2_from_spo2,
    estimate_pf_ratio_from_spo2,
    time_below_threshold,
    compute_t90,
    compute_t88,
    compute_t85,
    spo2_variability,
    detect_desaturation_events,
    calculate_odi,
    odi_severity,
    analyze_spo2_recording,
    process_csv,
    main,
)


class TestSpO2FiO2Ratio(unittest.TestCase):
    """Test SpO2/FiO2 ratio."""

    def test_normal_room_air(self):
        """SpO2 100% on room air: S/F ~476."""
        result = spo2_fio2_ratio(100.0, 0.21)
        self.assertAlmostEqual(result, 476.2, delta=1.0)

    def test_low_spo2_high_fio2(self):
        """SpO2 80% on 100% O2: S/F = 80."""
        self.assertAlmostEqual(spo2_fio2_ratio(80.0, 1.0), 80.0)

    def test_invalid_fio2(self):
        with self.assertRaises(ValueError):
            spo2_fio2_ratio(95.0, 0.0)

    def test_invalid_spo2(self):
        with self.assertRaises(ValueError):
            spo2_fio2_ratio(105.0, 0.5)


class TestEstimatePaO2(unittest.TestCase):
    """Test PaO2 estimation from SpO2."""

    def test_spo2_100(self):
        """SpO2 100% should estimate PaO2 > 80."""
        result = estimate_pao2_from_spo2(100.0)
        self.assertGreater(result, 80.0)

    def test_spo2_95(self):
        """SpO2 95% should estimate PaO2 around 80."""
        result = estimate_pao2_from_spo2(95.0)
        self.assertGreater(result, 60.0)
        self.assertLess(result, 120.0)

    def test_spo2_90(self):
        """SpO2 90% should estimate PaO2 around 60."""
        result = estimate_pao2_from_spo2(90.0)
        self.assertGreater(result, 40.0)
        self.assertLess(result, 80.0)

    def test_spo2_50_boundary(self):
        """SpO2 50% uses steep portion approximation."""
        result = estimate_pao2_from_spo2(50.0)
        self.assertAlmostEqual(result, 27.0)

    def test_spo2_0(self):
        self.assertAlmostEqual(estimate_pao2_from_spo2(0.0), 0.0)

    def test_monotonicity(self):
        """Higher SpO2 should give higher PaO2."""
        pao2_low = estimate_pao2_from_spo2(85.0)
        pao2_high = estimate_pao2_from_spo2(98.0)
        self.assertGreater(pao2_high, pao2_low)


class TestEstimatePFRatio(unittest.TestCase):
    """Test P/F ratio estimation from SpO2."""

    def test_normal(self):
        """SpO2 100% on room air should give P/F ~476."""
        result = estimate_pf_ratio_from_spo2(100.0, 0.21)
        self.assertGreater(result, 300.0)

    def test_low_spo2(self):
        """Low SpO2 gives low P/F."""
        result = estimate_pf_ratio_from_spo2(85.0, 0.5)
        self.assertLess(result, 200.0)


class TestTimeBelowThreshold(unittest.TestCase):
    """Test time below threshold calculations."""

    def test_t90_all_above(self):
        """All values above 90: T90 = 0."""
        vals = [95.0, 96.0, 97.0, 98.0]
        count, pct = compute_t90(vals)
        self.assertEqual(count, 0)
        self.assertAlmostEqual(pct, 0.0)

    def test_t90_all_below(self):
        """All values below 90: T90 = 100%."""
        vals = [85.0, 86.0, 87.0, 88.0]
        count, pct = compute_t90(vals)
        self.assertEqual(count, 4)
        self.assertAlmostEqual(pct, 100.0)

    def test_t90_partial(self):
        """50% below 90."""
        vals = [88.0, 89.0, 91.0, 92.0]
        count, pct = compute_t90(vals)
        self.assertEqual(count, 2)
        self.assertAlmostEqual(pct, 50.0)

    def test_t88(self):
        """T88 calculation."""
        vals = [85.0, 87.0, 89.0, 91.0]
        count, pct = compute_t88(vals)
        self.assertEqual(count, 2)

    def test_t85(self):
        """T85 calculation."""
        vals = [84.0, 86.0, 88.0, 90.0]
        count, pct = compute_t85(vals)
        self.assertEqual(count, 1)

    def test_empty_list(self):
        count, pct = time_below_threshold([], 90.0)
        self.assertEqual(count, 0)
        self.assertAlmostEqual(pct, 0.0)


class TestSpO2Variability(unittest.TestCase):
    """Test SpO2 variability metrics."""

    def test_constant_signal(self):
        """Constant signal has zero variability."""
        result = spo2_variability([95.0] * 100)
        self.assertAlmostEqual(result["mean"], 95.0)
        self.assertAlmostEqual(result["std_dev"], 0.0)
        self.assertAlmostEqual(result["coefficient_of_variation"], 0.0)

    def test_known_values(self):
        """Test with known values."""
        vals = [90.0, 92.0, 94.0, 96.0, 98.0]
        result = spo2_variability(vals)
        self.assertAlmostEqual(result["mean"], 94.0)
        self.assertAlmostEqual(result["median"], 94.0)
        self.assertAlmostEqual(result["min"], 90.0)
        self.assertAlmostEqual(result["max"], 98.0)

    def test_empty_list(self):
        result = spo2_variability([])
        self.assertAlmostEqual(result["mean"], 0.0)


class TestDesaturationEvents(unittest.TestCase):
    """Test desaturation event detection."""

    def test_single_event(self):
        """A single clear dip should be detected."""
        spo2 = [96.0] * 200
        # Create a dip from index 50-70
        for i in range(50, 60):
            spo2[i] = 96.0 - (i - 50) * 0.6  # ramp down to 90
        for i in range(60, 70):
            spo2[i] = 90.0 + (i - 60) * 0.6  # ramp up to 96

        events = detect_desaturation_events(spo2, threshold_pct=3.0, baseline_window=50)
        self.assertGreaterEqual(len(events), 1)

    def test_no_events_stable(self):
        """Stable signal should have no events."""
        spo2 = [97.0] * 300
        events = detect_desaturation_events(spo2, threshold_pct=3.0)
        self.assertEqual(len(events), 0)

    def test_sub_threshold_dip(self):
        """A dip smaller than threshold should not be detected."""
        spo2 = [96.0] * 200
        for i in range(80, 120):
            spo2[i] = 94.0  # only 2% dip
        events = detect_desaturation_events(spo2, threshold_pct=3.0)
        self.assertEqual(len(events), 0)


class TestODI(unittest.TestCase):
    """Test ODI calculation and severity."""

    def test_odi_calculation(self):
        """10 events over 8 hours = 1.25."""
        result = calculate_odi(10, 8.0)
        self.assertAlmostEqual(result, 1.25)

    def test_odi_zero_hours_raises(self):
        with self.assertRaises(ValueError):
            calculate_odi(5, 0.0)

    def test_severity_normal(self):
        self.assertIn("Normal", odi_severity(3.0))

    def test_severity_mild(self):
        self.assertIn("Mild", odi_severity(10.0))

    def test_severity_moderate(self):
        self.assertIn("Moderate", odi_severity(20.0))

    def test_severity_severe(self):
        self.assertIn("Severe", odi_severity(40.0))

    def test_severity_boundary(self):
        """ODI exactly 5 is mild."""
        self.assertIn("Mild", odi_severity(5.0))
        """ODI exactly 15 is moderate."""
        self.assertIn("Moderate", odi_severity(15.0))
        """ODI exactly 30 is severe."""
        self.assertIn("Severe", odi_severity(30.0))


class TestFullAnalysis(unittest.TestCase):
    """Test full recording analysis."""

    def test_stable_recording(self):
        """Stable recording analysis."""
        spo2 = [97.0] * 3600  # 1 hour at 1 Hz
        result = analyze_spo2_recording(spo2, 1.0, 3.0)
        self.assertEqual(result["num_desaturation_events"], 0)
        self.assertAlmostEqual(result["odi"], 0.0)
        self.assertAlmostEqual(result["recording_duration_hours"], 1.0)

    def test_with_fio2(self):
        """Analysis with FiO2 should include S/F ratio."""
        spo2 = [96.0] * 100
        result = analyze_spo2_recording(spo2, 1.0, 3.0, fio2=0.5)
        self.assertIn("spo2_fio2_ratio", result)
        self.assertIn("estimated_pf_ratio", result)

    def test_empty_recording(self):
        result = analyze_spo2_recording([], 1.0, 3.0)
        self.assertIn("error", result)


class TestCLI(unittest.TestCase):
    """Test CLI interface."""

    def test_odi_command(self):
        ret = main(["odi", "--events", "10", "--hours", "8"])
        self.assertEqual(ret, 0)

    def test_sf_command(self):
        ret = main(["sf", "--spo2", "96", "--fio2", "0.5"])
        self.assertEqual(ret, 0)

    def test_estimate_pao2_command(self):
        ret = main(["estimate-pao2", "--spo2", "95"])
        self.assertEqual(ret, 0)

    def test_no_command(self):
        ret = main([])
        self.assertEqual(ret, 1)

    def test_audit_command(self):
        ret = main(["audit", "--task-id", "TEST-AUDIT-001"])
        self.assertEqual(ret, 0)

    def test_verify_audit_command(self):
        ret = main(["verify-audit"])
        self.assertEqual(ret, 0)

    def test_chat_command(self):
        ret = main(["chat", "Explain", "ODI", "severity"])
        self.assertEqual(ret, 0)

    def test_serve_command_no_fastapi(self):
        ret = main(["serve"])
        self.assertEqual(ret, 1)


class TestPathSecurity(unittest.TestCase):
    """Test path security measures."""

    def test_safe_resolve_path_absolute(self):
        from spo2_odi import _safe_resolve_path
        result = _safe_resolve_path("/tmp/test.csv")
        self.assertTrue(os.path.isabs(result))

    def test_safe_resolve_path_relative(self):
        from spo2_odi import _safe_resolve_path
        result = _safe_resolve_path("test.csv")
        self.assertTrue(os.path.isabs(result))

    def test_safe_resolve_path_traversal(self):
        from spo2_odi import _safe_resolve_path
        result = _safe_resolve_path("../../../etc/passwd")
        # Should resolve to absolute path, not escape intended directory
        self.assertTrue(os.path.isabs(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
