"""scripts/fetch_rates.py 단위 테스트 (네트워크 불필요)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_rates  # noqa: E402


# EUR 기준 픽스처 (rates 값 = EUR 1유로당 해당 통화).
# KRW per X = KRW/EUR ÷ X/EUR
FIXTURE_KRW_PER_EUR = 1720.12
FIXTURE_PER_EUR = {
    "USD": 1.143,     # 1720.12/1.143   ≈ 1504.92 KRW
    "JPY": 185.02,    # 1720.12/185.02  ≈ 9.2970 KRW
    "CNY": 7.7433,    # 1720.12/7.7433  ≈ 222.14 KRW
    "GBP": 0.85155,   # 1720.12/0.85155 ≈ 2019.99 KRW
    "THB": 38.079,    # 1720.12/38.079  ≈ 45.17 KRW
}


def make_payload(**overrides):
    """frankfurter EUR 기준 응답 픽스처."""
    rates = {"KRW": FIXTURE_KRW_PER_EUR}
    rates.update(FIXTURE_PER_EUR)
    rates.update(overrides)
    return {"amount": 1.0, "base": "EUR", "date": "2026-07-10", "rates": rates}


def expected_krw_per(currency):
    if currency == "EUR":
        return round(FIXTURE_KRW_PER_EUR, fetch_rates.RATE_DECIMALS)
    return round(FIXTURE_KRW_PER_EUR / FIXTURE_PER_EUR[currency],
                 fetch_rates.RATE_DECIMALS)


class ParseRatesTest(unittest.TestCase):
    def test_parses_cross_rates_correctly(self):
        rates = fetch_rates.parse_rates(make_payload())
        for currency in fetch_rates.CURRENCIES:
            self.assertAlmostEqual(rates[currency], expected_krw_per(currency))
        self.assertEqual(set(rates), set(fetch_rates.CURRENCIES))
        for value in rates.values():
            self.assertGreater(value, 0)

    def test_eur_rate_is_krw_per_eur_directly(self):
        rates = fetch_rates.parse_rates(make_payload())
        self.assertAlmostEqual(rates["EUR"], FIXTURE_KRW_PER_EUR)

    def test_rejects_missing_currency(self):
        payload = make_payload()
        del payload["rates"]["THB"]
        with self.assertRaises(ValueError):
            fetch_rates.parse_rates(payload)

    def test_rejects_missing_krw_anchor(self):
        payload = make_payload()
        del payload["rates"]["KRW"]
        with self.assertRaises(ValueError):
            fetch_rates.parse_rates(payload)

    def test_rejects_non_numeric_rate(self):
        with self.assertRaises(ValueError):
            fetch_rates.parse_rates(make_payload(USD="fast"))

    def test_rejects_zero_or_negative_rate(self):
        with self.assertRaises(ValueError):
            fetch_rates.parse_rates(make_payload(JPY=0))
        with self.assertRaises(ValueError):
            fetch_rates.parse_rates(make_payload(JPY=-0.1))

    def test_rejects_payload_without_rates(self):
        with self.assertRaises(ValueError):
            fetch_rates.parse_rates({"base": "KRW"})


class ValidateRatesTest(unittest.TestCase):
    def valid_rates(self):
        return fetch_rates.parse_rates(make_payload())

    def test_accepts_sane_rates(self):
        fetch_rates.validate_rates(self.valid_rates())  # no exception

    def test_rejects_usd_below_band(self):
        rates = self.valid_rates()
        rates["USD"] = 499.99
        with self.assertRaises(ValueError):
            fetch_rates.validate_rates(rates)

    def test_rejects_usd_above_band(self):
        rates = self.valid_rates()
        rates["USD"] = 5000.01
        with self.assertRaises(ValueError):
            fetch_rates.validate_rates(rates)

    def test_rejects_non_positive_value(self):
        rates = self.valid_rates()
        rates["EUR"] = -1.0
        with self.assertRaises(ValueError):
            fetch_rates.validate_rates(rates)


class RunPipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_path = Path(self._tmp.name) / "rates.json"

    def read_data(self):
        return json.loads(self.data_path.read_text(encoding="utf-8"))

    def seed_existing(self, document):
        self.data_path.write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )

    def test_success_writes_valid_document(self):
        with mock.patch.object(fetch_rates, "fetch_payload",
                               return_value=make_payload()):
            result = fetch_rates.run(data_path=self.data_path)
        self.assertEqual(result, "updated")
        document = self.read_data()
        self.assertEqual(document["base"], "KRW")
        self.assertEqual(document["source"], fetch_rates.SOURCE_NAME)
        self.assertIsNotNone(document["updated"])
        self.assertAlmostEqual(document["rates"]["USD"], expected_krw_per("USD"))

    def test_network_failure_preserves_existing_file(self):
        seed = {"updated": None, "source": fetch_rates.SOURCE_NAME,
                "base": "KRW", "rates": None}
        self.seed_existing(seed)
        with mock.patch.object(fetch_rates, "fetch_payload",
                               side_effect=OSError("network down")):
            result = fetch_rates.run(data_path=self.data_path)
        self.assertEqual(result, "failed")
        self.assertEqual(self.read_data(), seed)

    def test_validation_failure_preserves_existing_file(self):
        seed = {"updated": "2026-07-01T07:00:00+09:00",
                "source": fetch_rates.SOURCE_NAME, "base": "KRW",
                "rates": {"USD": 1385.2}}
        self.seed_existing(seed)
        # USD/KRW = 1720.12/10000 ≈ 0.17 원 → 상식 밴드 위반
        with mock.patch.object(fetch_rates, "fetch_payload",
                               return_value=make_payload(USD=10000.0)):
            result = fetch_rates.run(data_path=self.data_path)
        self.assertEqual(result, "failed")
        self.assertEqual(self.read_data(), seed)

    def test_unchanged_rates_skip_write(self):
        with mock.patch.object(fetch_rates, "fetch_payload",
                               return_value=make_payload()):
            self.assertEqual(fetch_rates.run(data_path=self.data_path), "updated")
        before = self.data_path.read_bytes()
        with mock.patch.object(fetch_rates, "fetch_payload",
                               return_value=make_payload()), \
             mock.patch.object(fetch_rates, "write_document") as write_mock:
            result = fetch_rates.run(data_path=self.data_path)
        self.assertEqual(result, "unchanged")
        write_mock.assert_not_called()
        self.assertEqual(self.data_path.read_bytes(), before)

    def test_main_exits_zero_even_on_failure(self):
        with mock.patch.object(fetch_rates, "fetch_payload",
                               side_effect=OSError("boom")), \
             mock.patch.object(fetch_rates, "DEFAULT_DATA_PATH", self.data_path):
            self.assertEqual(fetch_rates.main(), 0)


if __name__ == "__main__":
    unittest.main()
