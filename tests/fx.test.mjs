// js/fx.js 단위 테스트 (node tests/fx.test.mjs 로 실행, 네트워크 불필요).
import assert from "node:assert/strict";
import { toKRW, fromKRW, fmtKRW, fmtForeign } from "../js/fx.js";

const RATES = {
  USD: 1385.2,
  JPY: 9.42,
  EUR: 1495.1,
  CNY: 190.3,
  GBP: 1750.4,
  THB: 39.8,
};

let passed = 0;
function test(name, fn) {
  fn();
  passed += 1;
  console.log(`ok - ${name}`);
}

// --- 변환 ---
test("toKRW converts USD to KRW", () => {
  assert.equal(toKRW(100, "USD", RATES), 138520);
});

test("fromKRW converts KRW to USD", () => {
  assert.ok(Math.abs(fromKRW(138520, "USD", RATES) - 100) < 1e-9);
});

test("roundtrip toKRW -> fromKRW is identity", () => {
  for (const currency of Object.keys(RATES)) {
    const amount = 123.45;
    const back = fromKRW(toKRW(amount, currency, RATES), currency, RATES);
    assert.ok(Math.abs(back - amount) < 1e-9, `roundtrip failed for ${currency}`);
  }
});

test("roundtrip fromKRW -> toKRW is identity", () => {
  const krw = 50000;
  for (const currency of Object.keys(RATES)) {
    const back = toKRW(fromKRW(krw, currency, RATES), currency, RATES);
    assert.ok(Math.abs(back - krw) < 1e-6, `roundtrip failed for ${currency}`);
  }
});

// --- null rates / 무효 입력 처리 ---
test("null rates return null (준비 중)", () => {
  assert.equal(toKRW(100, "USD", null), null);
  assert.equal(fromKRW(100, "USD", null), null);
});

test("unknown currency returns null", () => {
  assert.equal(toKRW(100, "XYZ", RATES), null);
  assert.equal(fromKRW(100, "XYZ", RATES), null);
});

test("invalid amounts return null", () => {
  assert.equal(toKRW(NaN, "USD", RATES), null);
  assert.equal(toKRW("100", "USD", RATES), null);
  assert.equal(fromKRW(Infinity, "USD", RATES), null);
});

test("non-positive or invalid rate values return null", () => {
  assert.equal(toKRW(100, "USD", { USD: 0 }), null);
  assert.equal(toKRW(100, "USD", { USD: -5 }), null);
  assert.equal(toKRW(100, "USD", { USD: "1385" }), null);
});

// --- 포맷 ---
test("fmtKRW formats with commas, no decimals", () => {
  assert.equal(fmtKRW(1385.2), "1,385");
  assert.equal(fmtKRW(1234567), "1,234,567");
  assert.equal(fmtKRW(0), "0");
});

test("fmtKRW returns null for invalid input", () => {
  assert.equal(fmtKRW(null), null);
  assert.equal(fmtKRW(NaN), null);
  assert.equal(fmtKRW("100"), null);
});

test("fmtForeign formats USD with 2 fixed decimals", () => {
  assert.equal(fmtForeign(1234.5, "USD"), "1,234.50");
  assert.equal(fmtForeign(10, "USD"), "10.00");
});

test("fmtForeign formats JPY with 0~2 decimals", () => {
  assert.equal(fmtForeign(1000, "JPY"), "1,000");
  assert.equal(fmtForeign(1000.5, "JPY"), "1,000.5");
  assert.equal(fmtForeign(1000.555, "JPY"), "1,000.56");
});

test("fmtForeign returns null for invalid input", () => {
  assert.equal(fmtForeign(NaN, "USD"), null);
  assert.equal(fmtForeign(100, 42), null);
  assert.equal(fmtForeign(null, "USD"), null);
});

console.log(`\n${passed} tests passed`);
