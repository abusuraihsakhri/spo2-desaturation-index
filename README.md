# SpO₂ Desaturation Index (ODI)

Calculate the oxygen desaturation index, percent of readings below saturation thresholds, and SpO₂ summary statistics from regularly sampled oximetry recordings.

The **browser application** is available in `index.html` and runs entirely client-side. It accepts CSV recordings, displays a trace and the first 50 completed events, and exports a JSON report containing all detected events.

## Method and limitations

- **ODI** = completed desaturation events / recording duration in hours.
- An event starts after a drop of at least the selected threshold (default **3 percentage points**) from the maximum of the **preceding 100 samples**.
- The event ends only when SpO₂ returns to within **1 percentage point** of its initial baseline. Dips that never recover before the recording ends are not counted.
- **T90, T88 and T85** are percentages of samples below 90%, 88% and 85%. Percentages represent fractions of recording time only when the sampling interval is constant.
- The time denominator is **total recorded time**, not estimated sleep time. The algorithm does not identify sleep, apnea/hypopnea, motion artifacts or poor signal quality.
- Python utilities also provide an SpO₂/FiO₂ ratio and a **rough, piecewise PaO₂ estimate**, which is particularly unreliable near full saturation. Do not use the PaO₂ estimate in place of an arterial blood gas.

**Research/educational prototype.** The event detector is not validated against manually scored polysomnography or an applicable device-specific ODI algorithm. Results must not be used independently for diagnosis, severity staging, treatment or patient safety decisions. A selected 3% threshold does not establish AASM-compliant hypopnea scoring.

## Browser application

Serve the repository root from a local web server (or use the GitHub Pages deployment once verified):

```bash
python -m http.server 8001
# Open http://localhost:8001/
```

Upload a UTF-8 CSV containing a numeric `spo2` column, and optionally a `time_sec` column with elapsed seconds. The file must be regularly sampled. Without a time column, enter the sampling rate in Hz. Blank, out-of-range, non-finite and irregularly timestamped measurements are rejected. Files are limited to 5 MB and 150,000 samples in the browser. Use **Load demonstration** for synthetic test data (one hour, eight recovered dips).

**Privacy:** The browser processes CSV input in local memory; no recording is uploaded and the application makes no network requests during processing. Files are not persisted in browser storage. Downloaded JSON reports remain on the user's device. As with all browser applications, access only through a trusted deployment.

## Python CLI

Python 3.10 or newer:

```bash
python -m pip install -r requirements.txt
python cli.py odi --events 10 --hours 8
python cli.py sf --spo2 96 --fio2 0.21
python cli.py estimate-pao2 --spo2 95
python cli.py analyze sample_data/sample_recording.csv --spo2-col spo2
python cli.py analyze data.csv --time-col time_sec --threshold 4 -o summary.csv
```

The core `spo2_odi.py` functions use only the Python standard library. The API requires the dependencies in `requirements.txt`. Timestamp input must be strictly increasing and evenly spaced (1% tolerance); resample irregular recordings before analysis. Existing input is not overwritten.

## Local API and container

```bash
# Only needed for supervisor audit operations; use a unique key per installation.
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python cli.py serve --host 127.0.0.1 --port 8000
```

Use `POST /api/odi` with a JSON body:

```json
{"spo2_values":[96,96,92,91,95,96],"sampling_interval_sec":1,"threshold_pct":3}
```

Other endpoints include `GET /health`, `GET /metrics` (JSON), and optional demonstration supervisor endpoints `POST /api/audit`, `POST /api/chat`, `GET /api/audit/logs`. The supervisor workers and chat adapter are **generic/mock demonstrations**, not clinically validated reasoning or an external language-model integration. The regex-based PHI guard detects only a subset of identifier formats; do not treat it as de-identification or HIPAA compliance. Audit HMAC signatures are held **in memory only**, so the trail is not durable across restarts.

For Docker Compose, set `AUDIT_SECRET_KEY` in a local `.env` file (excluded from version control):

```bash
printf 'AUDIT_SECRET_KEY=%s\n' "$(python -c 'import secrets; print(secrets.token_hex(32))')" > .env
docker compose up --build
```

## Tests

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
node --test web/app.test.js
docker build -t spo2-odi .
```

CI tests Python 3.10–3.13, the browser calculations and the Docker build. Deployment uses a separate GitHub Pages workflow. The static calculator does not need Pyodide, Python server processes, credentials, or a JavaScript package installation.

## License

[MIT](LICENSE).
