# SpO2 Desaturation Index Calculator

Real clinical calculators for pulse oximetry analysis. Stdlib-only Python.

## Calculators

| Calculator | Description | Reference |
|:-----------|:------------|:----------|
| **SpO2/FiO2 Ratio** | Surrogate for P/F ratio (normal ~476 on room air) | Rice et al., Chest 2005 |
| **PaO2 from SpO2** | Severinghaus equation approximation | Oxyhemoglobin dissociation curve |
| **ODI** | Desaturation events ≥3% drop per hour | AASM scoring criteria |
| **ODI Severity** | Normal <5, Mild 5-15, Moderate 15-30, Severe >30 | Clinical thresholds |
| **T90/T88/T85** | Time below SpO2 thresholds | Sleep medicine |
| **SpO2 Variability** | Mean, SD, CV, min, max | Signal analysis |
| **Event Detection** | Rolling baseline, threshold drop, recovery | AASM-style |

## Quick Start

```bash
# Analyze SpO2 recording from CSV
python spo2_odi.py analyze recording.csv --threshold 3.0 --fio2 0.5

# Quick ODI calculation
python spo2_odi.py odi --events 15 --hours 8

# SpO2/FiO2 ratio
python spo2_odi.py sf --spo2 96 --fio2 0.5

# Estimate PaO2 from SpO2
python spo2_odi.py estimate-pao2 --spo2 95
```

## Python API

```python
from spo2_odi import (
    spo2_fio2_ratio, estimate_pao2_from_spo2, calculate_odi,
    odi_severity, analyze_spo2_recording, detect_desaturation_events,
)

# S/F ratio
sf = spo2_fio2_ratio(96.0, 0.5)  # 192.0

# Estimate PaO2
pao2 = estimate_pao2_from_spo2(95.0)  # ~83 mmHg

# Full recording analysis
result = analyze_spo2_recording(spo2_values, sampling_interval_sec=1.0, threshold_pct=3.0)
# odi, odi_severity, t90, variability, events, ...
```

## Tests

```bash
python -m pytest test_spo2_odi.py -v
```

## License

MIT
