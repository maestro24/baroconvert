"""바로변환 환율 수집 스크립트.

frankfurter.app (ECB 고시 환율) 에서 EUR 기준 환율을 1회 호출로 수집하고,
크로스 레이트(KRW/EUR ÷ X/EUR)를 계산해 "외화 1단위 = KRW 몇 원" 형태로
data/rates.json 에 기록한다.

EUR 기준을 쓰는 이유: KRW 기준(from=KRW) 응답은 0.0005 처럼 유효숫자가
1~2자리로 잘려 역수 계산 시 1% 이상의 오차가 생긴다. ECB 원본은 EUR
기준이라 from=EUR 응답이 유효숫자 5자리 내외로 가장 정밀하다.

절대 깨지지 않는 원칙:
- 표준 라이브러리만 사용 (urllib, json)
- 수집/파싱/검증 실패 시: 기존 rates.json 유지, stderr 로그, exit 0
- 검증을 통과한 실데이터만 기록 (가짜 환율 금지)
- 기존 데이터와 동일하면 파일 미기록
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_URL = "https://api.frankfurter.app/latest?from=EUR&to=KRW,USD,JPY,CNY,GBP,THB"
CURRENCIES = ("USD", "JPY", "EUR", "CNY", "GBP", "THB")
SOURCE_NAME = "frankfurter.app (ECB)"
BASE_CURRENCY = "KRW"
USER_AGENT = "baroconvert-rates-bot/1.0 (+https://github.com/baroconvert)"
TIMEOUT_SECONDS = 15
RATE_DECIMALS = 4

# 상식 밴드: USD/KRW 가 이 범위를 벗어나면 데이터 자체를 불신하고 거부한다.
USD_KRW_MIN = 500.0
USD_KRW_MAX = 5000.0

KST = timezone(timedelta(hours=9))

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "rates.json"


def fetch_payload(url=API_URL, timeout=TIMEOUT_SECONDS):
    """API 를 호출해 JSON payload(dict) 를 반환한다. 실패 시 예외 발생."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("API payload is not a JSON object")
    return payload


def _require_positive_number(raw_rates, currency):
    value = raw_rates.get(currency)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"rate for {currency} is missing or not numeric: {value!r}")
    if value <= 0:
        raise ValueError(f"rate for {currency} is not positive: {value!r}")
    return float(value)


def parse_rates(payload):
    """frankfurter 응답(EUR 기준)에서 '외화 1단위 = KRW 몇 원' 딕셔너리를 만든다.

    payload["rates"]["KRW"] = EUR 1유로당 KRW,
    payload["rates"][X]     = EUR 1유로당 외화 X
    이므로 KRW per X = rates["KRW"] / rates[X] (EUR 자신은 rates["KRW"]).
    """
    raw_rates = payload.get("rates")
    if not isinstance(raw_rates, dict):
        raise ValueError("payload has no 'rates' object")

    krw_per_eur = _require_positive_number(raw_rates, "KRW")

    converted = {}
    for currency in CURRENCIES:
        if currency == "EUR":
            converted[currency] = round(krw_per_eur, RATE_DECIMALS)
            continue
        per_eur = _require_positive_number(raw_rates, currency)
        converted[currency] = round(krw_per_eur / per_eur, RATE_DECIMALS)
    return converted


def validate_rates(rates):
    """모든 값이 양수인지, USD/KRW 가 상식 밴드 안인지 검증한다. 실패 시 예외."""
    for currency in CURRENCIES:
        value = rates.get(currency)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"validated rate for {currency} is not numeric: {value!r}")
        if value <= 0:
            raise ValueError(f"validated rate for {currency} is not positive: {value!r}")

    usd = rates["USD"]
    if not (USD_KRW_MIN <= usd <= USD_KRW_MAX):
        raise ValueError(
            f"USD/KRW {usd} is outside sanity band [{USD_KRW_MIN}, {USD_KRW_MAX}]"
        )


def load_existing(data_path):
    """기존 rates.json 을 읽는다. 없거나 깨져 있으면 None 을 반환한다."""
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            document = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    return document


def build_document(rates, now=None):
    """스키마에 맞는 rates.json 문서를 만든다."""
    timestamp = (now or datetime.now(KST)).isoformat(timespec="seconds")
    return {
        "updated": timestamp,
        "source": SOURCE_NAME,
        "base": BASE_CURRENCY,
        "rates": rates,
    }


def write_document(document, data_path):
    data_path = Path(data_path)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
        f.write("\n")


def run(url=API_URL, data_path=DEFAULT_DATA_PATH, now=None):
    """수집 파이프라인 본체.

    반환값: "updated" | "unchanged" | "failed"
    어떤 경우에도 예외를 밖으로 던지지 않는다 (기존 파일 보존).
    """
    try:
        payload = fetch_payload(url)
        rates = parse_rates(payload)
        validate_rates(rates)
    except Exception as error:  # noqa: BLE001 - 어떤 실패든 기존 파일을 보존한다
        print(f"[fetch_rates] fetch failed, keeping existing rates.json: {error}",
              file=sys.stderr)
        return "failed"

    existing = load_existing(data_path)
    if existing is not None and existing.get("rates") == rates:
        print("[fetch_rates] rates unchanged, skipping write", file=sys.stderr)
        return "unchanged"

    try:
        write_document(build_document(rates, now=now), data_path)
    except OSError as error:
        print(f"[fetch_rates] write failed: {error}", file=sys.stderr)
        return "failed"

    print(f"[fetch_rates] rates updated: {rates}", file=sys.stderr)
    return "updated"


def main():
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
