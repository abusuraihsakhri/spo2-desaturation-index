"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {parseCsv, parseSeries, analyze, exampleCsv} = require("./app.js");

test("parses quoted headers, Windows newlines, and quoted field values", () => {
  assert.deepEqual(parseCsv('"spo2","time_sec"\r\n"95","0"\r\n"92","1"\r\n'), [
    ["spo2", "time_sec"], ["95", "0"], ["92", "1"]
  ]);
});

test("calculates synthetic example ODI from completed recovery events", () => {
  const recording = parseSeries(exampleCsv(), "spo2", "time_sec", 1);
  const result = analyze(recording.values, recording.interval, 3);
  assert.equal(result.sample_count, 3600);
  assert.equal(result.event_count, 8);
  assert.equal(result.odi, 8);
  assert.equal(result.events[0].depth, 5);
});

test("ignores sub-threshold dips and unrecovered final dips", () => {
  const values = [...Array(100).fill(96), ...Array(20).fill(94),
    ...Array(100).fill(96), ...Array(20).fill(91)];
  const result = analyze(values, 1, 3);
  assert.equal(result.event_count, 0);
});

test("rejects nonphysiological values and invalid sampling settings", () => {
  assert.throws(() => analyze([95, NaN], 1), /Invalid SpO/);
  assert.throws(() => analyze([95], 0), /Sampling interval/);
  assert.throws(() => analyze([95], 1, -3), /threshold/);
  assert.throws(() => parseSeries("spo2\n-1", "spo2", "", 1), /Invalid SpO/);
  assert.throws(() => parseSeries("spo2\n", "spo2", "", 1), /at least one/);
});

test("rejects missing cells, time regression, and irregular samples", () => {
  assert.throws(() => parseSeries("time,spo2\n0,95\n1,\n", "spo2", "time", 1), /Missing SpO/);
  assert.throws(() => parseSeries("time,spo2\n0,95\n1,96\n0.5,95", "spo2", "time", 1), /strictly/);
  assert.throws(() => parseSeries("time,spo2\n0,95\n1,96\n3,95", "spo2", "time", 1), /Irregular/);
});

test("recovers exactly at baseline minus one percentage point", () => {
  const values = [...Array(110).fill(96), ...Array(8).fill(91), 95, 96];
  const result = analyze(values, 1, 3);
  assert.equal(result.event_count, 1);
  assert.equal(result.events[0].duration_sec, 8);
});
