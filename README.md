# SpO2 Desaturation Index (ODI) Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)

</div>

---

## Overview

Real clinical calculators for pulse oximetry analysis:

- **SpO2/FiO2 ratio** (surrogate for P/F ratio)
    - Normal ~476 when SpO2=100%, FiO2=0.21
- **Estimated PaO2 from SpO2** (Severinghaus equation approximation)
- **Oxygen Desaturation Index (ODI)**: desaturation events per hour
    - Normal: < 5 events/hour
    - Mild: 5-15
    - Moderate: 15-30
    - Severe: > 30
- **Time below SpO2 thresholds** (T90, T88, T85)
- **SpO2 variability metrics** (mean, SD, coefficient of variation)

Author: Dr. Abu Suraih Sakhri. License: MIT.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/spo2-desaturation-index.git
cd spo2-desaturation-index

# Install dependencies
pip install -r requirements.txt

# Set audit security key (required)
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.hex(32))")
```

---

## CLI Usage

### Analyze a CSV Recording
```bash
python cli.py analyze sample_data/sample_recording.csv --spo2-col spo2
python cli.py analyze data.csv --fio2 0.5 --threshold 3.0 -o output_summary.csv
```

### Quick ODI Calculation
```bash
python cli.py odi --events 10 --hours 8
```

### SpO2/FiO2 Ratio
```bash
python cli.py sf --spo2 96 --fio2 0.21
```

### Estimate PaO2
```bash
python cli.py estimate-pao2 --spo2 95
```

### Audit Operations
```bash
python cli.py audit --task-id "TASK-001"
python cli.py verify-audit
```

### LLM Query (Mock Mode)
```bash
python cli.py chat "Explain ODI severity classification"
```

---

## Core API (Python)

```python
from spo2_odi import (
    spo2_fio2_ratio,
    estimate_pao2_from_spo2,
    calculate_odi,
    odi_severity,
    analyze_spo2_recording,
    detect_desaturation_events,
)

# Calculate S/F ratio
sf = spo2_fio2_ratio(96.0, 0.21)  # ~457.1

# Estimate PaO2
pao2 = estimate_pao2_from_spo2(95.0)  # ~80.0 mmHg

# Full analysis
result = analyze_spo2_recording(
    spo2_values=[96.0, 95.5, 94.0, ...],
    sampling_interval_sec=1.0,
    threshold_pct=3.0,
    fio2=0.21
)
print(result["odi"], result["odi_severity"])
```

---

## Security Features

### Zero-PHI Outbound Interceptor
Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers from outbound data.

```python
from agents.base import PHIGuard, SecurityException

try:
    PHIGuard.assert_no_phi("Patient John Doe MRN-12345")
except SecurityException:
    print("PHI detected and blocked")
```

### HMAC-SHA256 Tamper-Evident Audit Trail
Chained, cryptographically signed logs for every evaluation and state transition.

```python
from agents.base import AuditLogger

entry = AuditLogger.log(
    actor="system",
    actor_tier="supervisor",
    event_type="TASK_COMPLETED",
    details={"task_id": "TASK-001"}
)
# Verify integrity
assert AuditLogger.verify_integrity()
```

**Note:** The `AUDIT_SECRET_KEY` environment variable must be set. Generate a secure key with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Testing

```bash
# Run all tests
python -m pytest -v

# Run specific test files
python -m pytest test_spo2_odi.py -v
python -m pytest tests/ -v

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

---

## Enterprise Multi-Agent Architecture

The project includes a multi-agent supervisor system for clinical decision support:

- **InvariantQCWorker**: Mathematical and protocol boundary auditing
- **SafetyEscalationWorker**: Safety boundary and emergency interlock
- **ProtocolConformanceWorker**: Spec conformance and anomaly triage
- **SystemSupervisor**: Orchestrates multi-worker evaluations with consensus

```python
from agents.supervisor import SystemSupervisor
from agents.models import SystemTaskPayload

supervisor = SystemSupervisor(model_provider="mock")
payload = SystemTaskPayload(
    task_id="TASK-001",
    target_identifier="SPECIMEN-001",
    primary_metric=15.0,
    secondary_metric=4.0,
)
dossier = supervisor.process_task(payload)
```

---

## File Structure

```
spo2-desaturation-index/
├── spo2_odi.py          # Core calculations + CLI
├── cli.py               # CLI entry point
├── enrichment.py        # Enrichment feature engines
├── simulator.py         # High-throughput simulation
├── agents/              # Multi-agent security & audit system
│   ├── base.py          # PHI guard, HMAC audit trail
│   ├── models.py        # Pydantic data models
│   ├── workers.py       # Specialized worker agents
│   ├── supervisor.py    # Orchestrator
│   └── llm_factory.py   # LLM integration (mock)
├── sample_data/         # Sample SpO2 recordings
├── tests/               # Test suite
├── conftest.py          # Pytest configuration
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container build
└── benchmark_dataset.json  # Benchmark test cases
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
