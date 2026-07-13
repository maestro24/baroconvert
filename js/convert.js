/**
 * baroconvert conversion engine (JavaScript, ES module).
 *
 * Mirror of scripts/conversions.py — the two engines MUST behave identically.
 * No DOM, no fetch: the units database is injected via setData(data) or passed
 * per call as the 4th argument of convert(). In the browser, load
 * data/units.json (JSON import or inline) and call setData() once.
 *
 * Data contract (data/units.json):
 *   - Linear unit:  toBase(v) = v * factor,   fromBase(v) = v / factor
 *   - Affine unit:  toBase(v) = a * v + b,    fromBase(v) = (v - b) / a
 *     (when "affine" is present, "factor" is ignored)
 */

let defaultData = null;

/**
 * Inject the units database (parsed content of data/units.json).
 * @param {object} data
 */
export function setData(data) {
  if (!data || typeof data !== "object" || !data.categories) {
    throw new Error("setData: invalid units data");
  }
  defaultData = data;
}

/**
 * Map unit code -> { category, def }. Unit codes are globally unique.
 * @param {object} data
 * @returns {Map<string, {category: string, def: object}>}
 */
export function buildUnitIndex(data) {
  const index = new Map();
  for (const [catKey, cat] of Object.entries(data.categories)) {
    for (const [unitKey, unitDef] of Object.entries(cat.units)) {
      if (index.has(unitKey)) {
        throw new Error(`duplicate unit code across categories: ${unitKey}`);
      }
      index.set(unitKey, { category: catKey, def: unitDef });
    }
  }
  return index;
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function toBase(value, unitDef) {
  if (unitDef.affine) {
    return unitDef.affine.a * value + unitDef.affine.b;
  }
  return value * unitDef.factor;
}

function fromBase(value, unitDef) {
  if (unitDef.affine) {
    return (value - unitDef.affine.b) / unitDef.affine.a;
  }
  return value / unitDef.factor;
}

/**
 * Convert value between two units. Returns null when conversion is impossible:
 * non-numeric/non-finite value, unknown unit codes, or units belonging to
 * different categories.
 *
 * @param {number} value
 * @param {string} fromUnit
 * @param {string} toUnit
 * @param {object} [data] optional units database (defaults to setData() value)
 * @returns {number|null}
 */
export function convert(value, fromUnit, toUnit, data) {
  if (!isFiniteNumber(value)) {
    return null;
  }
  const db = data || defaultData;
  if (!db) {
    throw new Error("convert: no units data — call setData() or pass data");
  }
  const index = buildUnitIndex(db);
  const from = index.get(fromUnit);
  const to = index.get(toUnit);
  if (!from || !to) {
    return null;
  }
  if (from.category !== to.category) {
    return null;
  }
  return fromBase(toBase(value, from.def), to.def);
}

/**
 * Format a numeric result for display.
 *
 * Rules (identical to scripts/conversions.py format_result):
 *   - null / undefined / non-finite -> ""
 *   - round to at most 6 decimal places
 *   - strip trailing zeros in the fraction
 *   - thousands separators (commas) in the integer part
 *   - never emit "-0"
 *
 * @param {number|null|undefined} value
 * @returns {string}
 */
export function formatResult(value) {
  if (!isFiniteNumber(value)) {
    return "";
  }
  const text = Math.abs(value).toFixed(6);
  const [intPartRaw, fracRaw] = text.split(".");
  const fracPart = fracRaw.replace(/0+$/, "");
  const grouped = intPartRaw.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const out = grouped + (fracPart ? `.${fracPart}` : "");
  const negative = value < 0 && out !== "0";
  return negative ? `-${out}` : out;
}
