"use strict";

/** Local, dependency-free analysis for evenly sampled pulse-oximetry data. */
(function () {
  function assertPositiveFinite(value, label) {
    if (!Number.isFinite(value) || value <= 0) throw new Error(label + " must be finite and positive.");
  }

  function parseCsv(text) {
    if (typeof text !== "string") throw new Error("Invalid CSV input.");
    text = text.replace(/^\uFEFF/, "");
    const rows = [];
    let row = [], field = "", quoted = false, closedQuote = false, atStart = true;
    function endField() {
      row.push(field.trim());
      field = "";
      atStart = true;
      closedQuote = false;
    }
    function endRow() {
      endField();
      if (row.some(value => value !== "")) rows.push(row);
      row = [];
    }
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else { quoted = false; closedQuote = true; }
        } else { field += c; }
      } else if (c === ",") {
        endField();
      } else if (c === "\r" || c === "\n") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        endRow();
      } else if (c === '"' && atStart) {
        quoted = true;
        atStart = false;
      } else {
        if (closedQuote && !/\s/.test(c)) throw new Error("Unexpected text after quoted CSV field.");
        if (c === '"') throw new Error("Unexpected quotation mark in CSV.");
        if (!closedQuote) field += c;
        atStart = false;
      }
    }
    if (quoted) throw new Error("Unclosed quoted CSV field.");
    if (field !== "" || row.length) endRow();
    return rows;
  }

  function parseSeries(text, spo2Column, timeColumn, rateHz) {
    assertPositiveFinite(rateHz, "Sampling rate");
    const rows = parseCsv(text);
    if (rows.length < 2) throw new Error("CSV must contain a header and at least one measurement.");
    const header = rows[0].map(s => s.toLowerCase());
    function find(name) { return header.indexOf(name.trim().toLowerCase()); }
    const sIndex = find(spo2Column);
    if (sIndex < 0) throw new Error("SpO₂ column not found: " + spo2Column);
    const hasTime = Boolean(timeColumn && timeColumn.trim());
    const tIndex = hasTime ? find(timeColumn) : -1;
    if (hasTime && tIndex < 0) throw new Error("Time column not found: " + timeColumn);
    if (rows.length - 1 > 150000) throw new Error("Maximum 150,000 samples supported.");
    const values = [], times = [];
    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      if (row.length !== header.length) throw new Error("CSV column count mismatch at row " + (i + 1));
      if (row[sIndex] === "") throw new Error("Missing SpO₂ at row " + (i + 1));
      const s = Number(row[sIndex]);
      if (!Number.isFinite(s) || s < 0 || s > 100) throw new Error("Invalid SpO₂ at row " + (i + 1) + "; expected 0–100.");
      values.push(s);
      if (hasTime) {
        if (row[tIndex] === "") throw new Error("Missing timestamp at row " + (i + 1));
        const t = Number(row[tIndex]);
        if (!Number.isFinite(t)) throw new Error("Invalid timestamp at row " + (i + 1));
        times.push(t);
      }
    }
    let interval = 1 / rateHz;
    if (times.length > 1) {
      const intervals = [];
      for (let i = 1; i < times.length; i++) {
        const dt = times[i] - times[i - 1];
        if (!Number.isFinite(dt) || dt <= 0) throw new Error("Timestamps must increase strictly.");
        intervals.push(dt);
      }
      interval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      if (intervals.some(dt => Math.abs(dt - interval) > interval * 0.01))
        throw new Error("Irregular timestamps are unsupported. Resample before analysis.");
    }
    return { values, interval };
  }

  function analyze(values, interval = 1, threshold = 3) {
    assertPositiveFinite(interval, "Sampling interval");
    assertPositiveFinite(threshold, "Desaturation threshold");
    if (threshold <= 1 || threshold > 100) throw new Error("Desaturation threshold must exceed the 1% recovery margin and be at most 100%.");
    if (!Array.isArray(values) || !values.length) throw new Error("No SpO₂ measurements.");
    if (values.length > 150000) throw new Error("Maximum 150,000 samples supported.");
    for (let i = 0; i < values.length; i++) {
      if (!Number.isFinite(values[i]) || values[i] < 0 || values[i] > 100)
        throw new Error("Invalid SpO₂ measurement at index " + i);
    }
    const hours = values.length * interval / 3600;
    const events = [];
    // Decreasing queue of prior samples: max of preceding 100 readings.
    const deque = [];
    let event = null;
    let below90 = 0, below88 = 0, below85 = 0, sum = 0, minimum = 100, maximum = 0;
    for (let i = 0; i < values.length; i++) {
      const s = values[i];
      if (s < 90) below90++;
      if (s < 88) below88++;
      if (s < 85) below85++;
      sum += s;
      minimum = Math.min(minimum, s);
      maximum = Math.max(maximum, s);
      while (deque.length && deque[0] <= i - 101) deque.shift();
      const baseline = deque.length ? values[deque[0]] : s;
      if (event === null) {
        if (s <= baseline - threshold)
          event = { start_idx: i, baseline_spo2: baseline, nadir_idx: i, nadir_spo2: s };
      } else {
        if (s < event.nadir_spo2) { event.nadir_spo2 = s; event.nadir_idx = i; }
        if (s >= event.baseline_spo2 - 1) {
          events.push({
            start_idx: event.start_idx, end_idx: i, nadir_idx: event.nadir_idx,
            start_time_sec: event.start_idx * interval, end_time_sec: i * interval,
            duration_sec: (i - event.start_idx) * interval,
            baseline_spo2: Math.round(event.baseline_spo2 * 10) / 10,
            nadir_spo2: Math.round(event.nadir_spo2 * 10) / 10,
            depth: Math.round((event.baseline_spo2 - event.nadir_spo2) * 10) / 10
          });
          event = null;
        }
      }
      while (deque.length && values[deque[deque.length - 1]] <= s) deque.pop();
      deque.push(i);
    }
    return {
      sample_count: values.length, sampling_interval_sec: interval,
      threshold_pct: threshold, recording_hours: hours,
      event_count: events.length, odi: events.length / hours,
      t90_percent: below90 / values.length * 100,
      t88_percent: below88 / values.length * 100,
      t85_percent: below85 / values.length * 100,
      mean_spo2: sum / values.length, min_spo2: minimum, max_spo2: maximum,
      events
    };
  }

  function exampleCsv() {
    const lines = ["time_sec,spo2"];
    for (let i = 0; i < 3600; i++) {
      let s = 96;
      for (let j = 0; j < 8; j++) {
        const start = 200 + j * 400;
        if (i >= start && i < start + 12) s = 91;
      }
      lines.push(i + "," + s);
    }
    return lines.join("\n");
  }

  function drawChart(svg, values) {
    const ns = "http://www.w3.org/2000/svg";
    svg.replaceChildren();
    const pad = 23, width = 720 - 2 * pad, height = 200 - 2 * pad;
    let min = 100, max = 0;
    for (const s of values) { min = Math.min(s, min); max = Math.max(s, max); }
    min = Math.max(0, Math.floor((min - 3) / 5) * 5);
    max = Math.min(100, Math.ceil((max + 3) / 5) * 5);
    if (max === min) { min = Math.max(0, min - 5); max = Math.min(100, max + 5); }
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", pad); line.setAttribute("x2", 720 - pad);
    const y90 = pad + ((max - 90) / (max - min)) * height;
    if (y90 >= pad && y90 <= 200 - pad) {
      line.setAttribute("y1", y90); line.setAttribute("y2", y90);
      line.setAttribute("stroke", "#d97706"); line.setAttribute("stroke-dasharray", "5 5");
      svg.appendChild(line);
    }
    const path = document.createElementNS(ns, "path");
    // Plot a min/max envelope, retaining short dips even for long recordings.
    const buckets = Math.min(values.length, 700);
    const commands = [];
    for (let i = 0; i < buckets; i++) {
      const first = Math.floor(i * values.length / buckets);
      const end = Math.min(values.length, Math.ceil((i + 1) * values.length / buckets));
      let low = 100, high = 0;
      for (let k = first; k < end; k++) {
        low = Math.min(low, values[k]); high = Math.max(high, values[k]);
      }
      const x = pad + (buckets === 1 ? 0 : i * width / (buckets - 1));
      const yLow = pad + (max - low) / (max - min) * height;
      const yHigh = pad + (max - high) / (max - min) * height;
      commands.push((i ? "L" : "M") + x.toFixed(2) + " " + yLow.toFixed(2));
      commands.push("L" + x.toFixed(2) + " " + yHigh.toFixed(2));
    }
    path.setAttribute("d", commands.join(" "));
    path.setAttribute("fill", "none"); path.setAttribute("stroke", "#175cd3");
    path.setAttribute("stroke-width", "2"); path.setAttribute("vector-effect", "non-scaling-stroke");
    svg.appendChild(path);
    return {min, max};
  }

  function init() {
    const el = id => document.getElementById(id);
    let demoText = null, lastReport = null;
    function resetResults() {
      lastReport = null;
      el("results").hidden = true;
      el("empty").hidden = false;
      el("download").hidden = true;
    }
    el("file").addEventListener("change", () => {
      demoText = null;
      resetResults();
      el("source").textContent = el("file").files[0] ? "Selected: " + el("file").files[0].name : "No file selected.";
      el("message").textContent = "";
    });
    el("demo").addEventListener("click", () => {
      resetResults();
      demoText = exampleCsv();
      el("file").value = "";
      el("time-col").value = "time_sec";
      el("spo2-col").value = "spo2";
      el("source").textContent = "Demonstration: 3,600 synthetic 1 Hz readings with eight recovered dips.";
      el("message").textContent = "Demonstration loaded. Choose Analyze recording.";
      el("message").classList.remove("error");
    });
    el("analyze").addEventListener("click", async () => {
      el("message").classList.remove("error");
      el("message").textContent = "Analyzing locally…";
      el("analyze").disabled = true;
      resetResults();
      try {
        const file = el("file").files[0];
        if (!file && demoText === null) throw new Error("Choose a CSV file or load the demonstration.");
        if (file && file.size > 5 * 1024 * 1024) throw new Error("CSV must be at most 5 MB.");
        const text = demoText !== null ? demoText : await file.text();
        const rate = Number(el("hz").value), threshold = Number(el("threshold").value);
        const parsed = parseSeries(text, el("spo2-col").value, el("time-col").value, rate);
        lastReport = analyze(parsed.values, parsed.interval, threshold);
        el("odi").textContent = lastReport.odi.toFixed(2);
        el("events").textContent = lastReport.event_count.toLocaleString();
        el("duration").textContent = lastReport.recording_hours.toFixed(3);
        el("t90").textContent = lastReport.t90_percent.toFixed(2);
        const limits = drawChart(el("chart"), parsed.values);
        el("range").textContent = "Trace range: " + limits.min + "–" + limits.max + "% SpO₂. Dashed line denotes 90%.";
        const rows = el("event-rows");
        rows.replaceChildren();
        for (const event of lastReport.events.slice(0, 50)) {
          const tr = document.createElement("tr");
          for (const v of [event.start_time_sec, event.duration_sec, event.baseline_spo2, event.nadir_spo2, event.depth]) {
            const td = document.createElement("td");
            td.textContent = v.toFixed(1);
            tr.appendChild(td);
          }
          rows.appendChild(tr);
        }
        el("truncated").textContent = lastReport.events.length > 50 ? "Showing the first 50 events. The JSON report contains all events." : lastReport.events.length ? "" : "No recovered desaturation events detected.";
        el("empty").hidden = true; el("results").hidden = false; el("download").hidden = false;
        el("message").textContent = "Analysis complete — processed " + lastReport.sample_count.toLocaleString() + " samples locally.";
      } catch (err) {
        el("message").textContent = err.message || "Analysis failed.";
        el("message").classList.add("error");
      } finally {
        el("analyze").disabled = false;
      }
    });
    el("download").addEventListener("click", () => {
      if (!lastReport) return;
      const blob = new Blob([JSON.stringify(lastReport, null, 2)], {type:"application/json"});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = "spo2-odi-report.json"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1500);
    });
  }

  if (typeof module !== "undefined" && module.exports) module.exports = {parseCsv, parseSeries, analyze, exampleCsv};
  if (typeof document !== "undefined") init();
})();
