/**
 * 바로변환 환율 계산 순수 함수 모듈 (ES module, DOM 접근 금지).
 *
 * rates 형태: { USD: 1385.2, JPY: 9.42, ... }
 * 값 의미: 외화 1단위 = KRW 몇 원 (JPY 는 1엔 기준).
 * rates 가 null 이거나 값이 유효하지 않으면 모든 함수가 null 을 반환한다
 * (프론트에서 "준비 중" 처리).
 */

/** 통화별 표시 소수 자리 (min/max fraction digits). */
const FRACTION_DIGITS = Object.freeze({
  USD: Object.freeze({ min: 2, max: 2 }),
  EUR: Object.freeze({ min: 2, max: 2 }),
  GBP: Object.freeze({ min: 2, max: 2 }),
  CNY: Object.freeze({ min: 2, max: 2 }),
  THB: Object.freeze({ min: 2, max: 2 }),
  JPY: Object.freeze({ min: 0, max: 2 }),
});

const DEFAULT_FRACTION = Object.freeze({ min: 0, max: 2 });

/** 유한한 숫자인지 검사한다. */
function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

/** rates 에서 currency 의 KRW 환산 환율을 꺼낸다. 유효하지 않으면 null. */
function getRate(currency, rates) {
  if (rates === null || typeof rates !== "object") return null;
  const rate = rates[currency];
  if (!isFiniteNumber(rate) || rate <= 0) return null;
  return rate;
}

/**
 * 외화 금액을 KRW 로 변환한다.
 * @returns {number|null} 변환 결과. 입력이 유효하지 않으면 null.
 */
export function toKRW(amount, currency, rates) {
  const rate = getRate(currency, rates);
  if (rate === null || !isFiniteNumber(amount)) return null;
  return amount * rate;
}

/**
 * KRW 금액을 외화로 변환한다.
 * @returns {number|null} 변환 결과. 입력이 유효하지 않으면 null.
 */
export function fromKRW(krw, currency, rates) {
  const rate = getRate(currency, rates);
  if (rate === null || !isFiniteNumber(krw)) return null;
  return krw / rate;
}

/**
 * KRW 금액을 "1,385" 형태(정수, 천 단위 콤마)로 포맷한다.
 * @returns {string|null}
 */
export function fmtKRW(n) {
  if (!isFiniteNumber(n)) return null;
  return new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

/**
 * 외화 금액을 통화별 소수 자리 규칙으로 포맷한다 (JPY 0~2, USD 등 2 고정).
 * @returns {string|null}
 */
export function fmtForeign(n, currency) {
  if (!isFiniteNumber(n) || typeof currency !== "string") return null;
  const digits = FRACTION_DIGITS[currency] || DEFAULT_FRACTION;
  return new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: digits.min,
    maximumFractionDigits: digits.max,
  }).format(n);
}
