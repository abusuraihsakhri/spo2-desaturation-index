# Spo2 Desaturation Index

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

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

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`spo2_fio2_ratio()`**: Calculate SpO2/FiO2 ratio (surrogate for PaO2/FiO2).

Normal ~476 when SpO2=100%, FiO2=0.21.

Args:
    spo2: Oxygen saturation percentage (0-100).
    fio2: Fraction of inspired oxygen (0.0-1.0).

Returns:
    S/F ratio.
- **`estimate_pao2_from_spo2()`**: Estimate PaO2 from SpO2 using a clinical approximation of the
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
- **`estimate_pf_ratio_from_spo2()`**: Estimate P/F ratio from SpO2 and FiO2.

Combines Severinghaus estimation with P/F calculation.

Args:
    spo2: Oxygen saturation percentage (0-100).
    fio2: Fraction of inspired oxygen (0.0-1.0).

Returns:
    Estimated P/F ratio.
- **`time_below_threshold()`**: Count samples and percentage of time below an SpO2 threshold.

Args:
    spo2_values: List of SpO2 readings.
    threshold: SpO2 threshold percentage.

Returns:
    Tuple of (count_below, percent_below).
- **`compute_t90()`**: Compute T90: time spent below SpO2 90%.

Args:
    spo2_values: List of SpO2 readings.

Returns:
    Tuple of (count_below_90, percent_below_90).

---

## 📐 Mathematical Formulation & Logic

```text
  """Calculate SpO2/FiO2 ratio (surrogate for PaO2/FiO2).
  """Calculate SpO2 variability metrics.
  """Calculate Oxygen Desaturation Index.
  sf = sub.add_parser("sf", help="Calculate SpO2/FiO2 ratio")
  odi = calculate_odi(args.events, args.hours)
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --input data.csv
```

### Parameter Reference
- `--interactive`: Launch guided terminal interactive wizard.
- `--input <path>`: Evaluate input from JSON or CSV specification.
- `--json`: Output deterministic structured results in JSON format.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `suite_name` | Parameter / observation metric | Required |
| `system_slug` | Parameter / observation metric | Required |
| `standard_reference` | Parameter / observation metric | Required |
| `test_cases` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t spo2-desaturation-index .
docker run -p 8000:8000 spo2-desaturation-index
```
