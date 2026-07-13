/**
 * Tests for the baroconvert JS engine (js/convert.js).
 *
 * Run from the project root (after the Python suite, which generates the
 * cross-check fixture):
 *     python -m unittest discover tests && node tests/convert.test.mjs
 */

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import assert from "node:assert/strict";

import { buildUnitIndex, convert, formatResult, setData } from "../js/convert.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const DATA = JSON.parse(readFileSync(join(ROOT, "data", "units.json"), "utf-8"));
const CROSS_CHECK_PATH = join(HERE, "fixtures", "cross_check.json");

setData(DATA);

const REL_TOL = 1e-9;
const ROUND_TRIP_SAMPLES = [0.5, 1, 3.7, 42, 1234.5];

let passed = 0;
let failed = 0;
const failures = [];

function test(name, fn) {
  try {
    fn();
    passed += 1;
  } catch (err) {
    failed += 1;
    failures.push({ name, message: err.message });
  }
}

function assertClose(actual, expected, tol, label) {
  assert.ok(actual !== null && actual !== undefined, `${label}: got null`);
  const err = Math.abs(actual - expected);
  const limit = tol * Math.max(1, Math.abs(expected));
  assert.ok(
    err <= limit,
    `${label}: got ${actual}, want ${expected} (err ${err} > ${limit})`
  );
}

// ---------------------------------------------------------------- known values
const KNOWN_CASES = [
  [1, "ft", "cm", 30.48],
  [5.5, "ft", "cm", 167.64],
  [1, "in", "cm", 2.54],
  [1, "pyeong", "m2", 3.305785],
  [1, "gal", "l", 3.785411784],
  [1, "geun", "g", 600],
  [1, "don", "g", 3.75],
  [1, "lb", "kg", 0.45359237],
  [1, "mi", "km", 1.609344],
  [1, "yd", "m", 0.9144],
  [1, "cup", "ml", 240],
  [1, "tbsp", "ml", 15],
  [1, "tsp", "ml", 5],
  [1, "acre", "m2", 4046.8564224],
  [1, "nyang", "g", 37.5],
  [100, "f", "c", 37.77777777777778],
  [0, "c", "f", 32],
  [32, "f", "c", 0],
  [100, "c", "f", 212],
  [0, "c", "k", 273.15],
  [36.5, "c", "f", 97.7],
];

for (const [value, from, to, expected] of KNOWN_CASES) {
  test(`known: ${value} ${from} -> ${to}`, () => {
    assertClose(convert(value, from, to), expected, REL_TOL, `${value} ${from}->${to}`);
  });
}

test("known: 1 oz -> g high precision", () => {
  const result = convert(1, "oz", "g");
  assert.ok(result !== null);
  assert.ok(Math.abs(result - 28.349523125) < 1e-6);
});

// ------------------------------------------------------------------ round trip
test("round trip: every unit pair in every category", () => {
  for (const [catKey, cat] of Object.entries(DATA.categories)) {
    const units = Object.keys(cat.units);
    for (const a of units) {
      for (const b of units) {
        if (a === b) continue;
        for (const x of ROUND_TRIP_SAMPLES) {
          const forward = convert(x, a, b);
          assert.ok(forward !== null, `${catKey}: ${a}->${b} returned null`);
          const back = convert(forward, b, a);
          assertClose(back, x, REL_TOL, `${catKey}: round trip ${x} ${a}<->${b}`);
        }
      }
    }
  }
});

// ---------------------------------------------------------- invalid conversions
test("cross-category conversion returns null", () => {
  const cases = [
    [1, "kg", "m"], [1, "m", "kg"], [1, "c", "l"],
    [1, "pyeong", "cm"], [1, "gal", "g"], [100, "f", "km"],
  ];
  for (const [value, from, to] of cases) {
    assert.equal(convert(value, from, to), null, `${from}->${to} should be null`);
  }
});

test("unknown units return null", () => {
  assert.equal(convert(1, "nope", "cm"), null);
  assert.equal(convert(1, "cm", "nope"), null);
});

test("invalid values return null", () => {
  assert.equal(convert(NaN, "ft", "cm"), null);
  assert.equal(convert(Infinity, "ft", "cm"), null);
  assert.equal(convert("5", "ft", "cm"), null);
  assert.equal(convert(null, "ft", "cm"), null);
  assert.equal(convert(true, "ft", "cm"), null);
});

test("data can be passed per call instead of setData", () => {
  assertClose(convert(1, "ft", "cm", DATA), 30.48, REL_TOL, "explicit data arg");
});

// ---------------------------------------------------------------- formatResult
const FORMAT_CASES = [
  [30.48, "30.48"],
  [167.64, "167.64"],
  [1609.344, "1,609.344"],
  [1234567.89, "1,234,567.89"],
  [1000000, "1,000,000"],
  [0.123456789, "0.123457"],
  [0.1, "0.1"],
  [0, "0"],
  [1e-7, "0"],
  [-1234.5, "-1,234.5"],
  [-1e-7, "0"],
  [3.75, "3.75"],
  [37.77777777777778, "37.777778"],
];

for (const [value, expected] of FORMAT_CASES) {
  test(`format: ${value} -> "${expected}"`, () => {
    assert.equal(formatResult(value), expected);
  });
}

test("format: invalid inputs", () => {
  assert.equal(formatResult(null), "");
  assert.equal(formatResult(undefined), "");
  assert.equal(formatResult(NaN), "");
  assert.equal(formatResult(Infinity), "");
});

// -------------------------------------------------------------- data integrity
test("integrity: required categories and >=30 units", () => {
  for (const cat of ["length", "weight", "temperature", "area", "volume"]) {
    assert.ok(DATA.categories[cat], `missing category ${cat}`);
  }
  const total = Object.values(DATA.categories)
    .reduce((n, cat) => n + Object.keys(cat.units).length, 0);
  assert.ok(total >= 30, `only ${total} units defined`);
});

test("integrity: base units exist and are identity", () => {
  for (const [catKey, cat] of Object.entries(DATA.categories)) {
    assert.ok(cat.units[cat.base], `${catKey}: base '${cat.base}' not defined`);
    const baseDef = cat.units[cat.base];
    if (baseDef.affine) {
      assert.equal(baseDef.affine.a, 1);
      assert.equal(baseDef.affine.b, 0);
    } else {
      assert.equal(baseDef.factor, 1, `${catKey}: base factor must be 1`);
    }
  }
});

test("integrity: unit definitions valid, codes globally unique", () => {
  buildUnitIndex(DATA); // throws on duplicate codes
  for (const [catKey, cat] of Object.entries(DATA.categories)) {
    for (const [unitKey, def] of Object.entries(cat.units)) {
      const label = `${catKey}.${unitKey}`;
      assert.ok(def.nameKo, `${label}: missing nameKo`);
      assert.ok(def.symbol, `${label}: missing symbol`);
      if (def.affine) {
        assert.ok(Number.isFinite(def.affine.a), `${label}: bad affine.a`);
        assert.ok(Number.isFinite(def.affine.b), `${label}: bad affine.b`);
        assert.notEqual(def.affine.a, 0, `${label}: affine.a is 0`);
      } else {
        assert.ok(Number.isFinite(def.factor), `${label}: bad factor`);
        assert.ok(def.factor > 0, `${label}: factor must be > 0`);
      }
    }
  }
});

test("integrity: pairs reference defined same-category units, non-empty values", () => {
  const index = buildUnitIndex(DATA);
  assert.ok(DATA.pairs.length >= 30, `too few pairs (${DATA.pairs.length})`);
  for (const pair of DATA.pairs) {
    const label = `pair ${pair.from}->${pair.to}`;
    assert.ok(index.has(pair.from), `${label}: unknown from unit`);
    assert.ok(index.has(pair.to), `${label}: unknown to unit`);
    assert.equal(
      index.get(pair.from).category,
      index.get(pair.to).category,
      `${label}: units in different categories`
    );
    assert.ok(Array.isArray(pair.values) && pair.values.length > 0,
      `${label}: empty values`);
    for (const v of pair.values) {
      assert.ok(typeof v === "number" && Number.isFinite(v),
        `${label}: non-numeric value ${v}`);
    }
  }
});

// -------------------------------------------------- Python <-> JS cross check
test("cross check: JS matches Python fixture for all pair/value combos", () => {
  assert.ok(
    existsSync(CROSS_CHECK_PATH),
    `missing ${CROSS_CHECK_PATH} — run "python -m unittest discover tests" first`
  );
  const fixture = JSON.parse(readFileSync(CROSS_CHECK_PATH, "utf-8"));
  const tol = fixture.tolerance ?? REL_TOL;
  assert.ok(fixture.combos.length > 300, "unexpectedly few cross-check combos");
  for (const combo of fixture.combos) {
    const result = convert(combo.value, combo.from, combo.to);
    assertClose(result, combo.expected, tol,
      `cross ${combo.value} ${combo.from}->${combo.to}`);
  }
  console.log(`  cross-check combos verified: ${fixture.combos.length}`);
});

// ---------------------------------------------------------------------- report
console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
  for (const f of failures) {
    console.error(`FAIL: ${f.name}\n  ${f.message}`);
  }
  process.exit(1);
}
