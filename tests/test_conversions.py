"""Tests for the baroconvert Python engine (scripts/conversions.py).

Run from the project root:
    python -m unittest discover tests

One test also dumps tests/fixtures/cross_check.json, which the Node test
suite (tests/convert.test.mjs) uses to verify Python/JS engine parity.
"""

import json
import math
import sys
import unittest
from itertools import permutations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import conversions  # noqa: E402
from conversions import build_unit_index, convert, format_result, load_units  # noqa: E402

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
CROSS_CHECK_PATH = FIXTURES_DIR / "cross_check.json"

DATA = load_units()

REL_TOL = 1e-9
ROUND_TRIP_SAMPLES = [0.5, 1, 3.7, 42, 1234.5]


def _assert_close(test, actual, expected, tol=REL_TOL, msg=""):
    test.assertIsNotNone(actual, msg)
    err = abs(actual - expected)
    limit = tol * max(1.0, abs(expected))
    test.assertLessEqual(err, limit, f"{msg}: got {actual}, want {expected} (err {err})")


class TestKnownValues(unittest.TestCase):
    """Accuracy against internationally defined constants."""

    CASES = [
        # (value, from, to, expected, abs-or-rel note handled by tolerance below)
        (1, "ft", "cm", 30.48),
        (5.5, "ft", "cm", 167.64),
        (1, "in", "cm", 2.54),
        (1, "pyeong", "m2", 3.305785),
        (1, "gal", "l", 3.785411784),
        (1, "geun", "g", 600),
        (1, "don", "g", 3.75),
        (1, "lb", "kg", 0.45359237),
        (1, "mi", "km", 1.609344),
        (1, "yd", "m", 0.9144),
        (1, "cup", "ml", 240),
        (1, "tbsp", "ml", 15),
        (1, "tsp", "ml", 5),
        (1, "acre", "m2", 4046.8564224),
        (1, "nyang", "g", 37.5),
        (100, "f", "c", 37.77777777777778),
        (0, "c", "f", 32),
        (32, "f", "c", 0),
        (100, "c", "f", 212),
        (0, "c", "k", 273.15),
        (36.5, "c", "f", 97.7),
    ]

    def test_known_values(self):
        for value, from_u, to_u, expected in self.CASES:
            with self.subTest(f"{value} {from_u} -> {to_u}"):
                _assert_close(self, convert(value, from_u, to_u), expected,
                              msg=f"{value} {from_u}->{to_u}")

    def test_oz_to_g_high_precision(self):
        result = convert(1, "oz", "g")
        self.assertIsNotNone(result)
        self.assertLess(abs(result - 28.349523125), 1e-6)


class TestRoundTrip(unittest.TestCase):
    """convert(convert(x, a, b), b, a) must recover x for every unit pair."""

    def test_all_pairs_round_trip(self):
        for cat_key, cat in DATA["categories"].items():
            for a, b in permutations(cat["units"].keys(), 2):
                for x in ROUND_TRIP_SAMPLES:
                    with self.subTest(f"{cat_key}: {x} {a}<->{b}"):
                        forward = convert(x, a, b)
                        self.assertIsNotNone(forward, f"{a}->{b} returned None")
                        back = convert(forward, b, a)
                        _assert_close(self, back, x, msg=f"round trip {a}<->{b}")


class TestInvalidConversions(unittest.TestCase):
    def test_cross_category_returns_none(self):
        cases = [
            (1, "kg", "m"), (1, "m", "kg"), (1, "c", "l"),
            (1, "pyeong", "cm"), (1, "gal", "g"), (100, "f", "km"),
        ]
        for value, from_u, to_u in cases:
            with self.subTest(f"{from_u}->{to_u}"):
                self.assertIsNone(convert(value, from_u, to_u))

    def test_unknown_units_return_none(self):
        self.assertIsNone(convert(1, "nope", "cm"))
        self.assertIsNone(convert(1, "cm", "nope"))

    def test_invalid_values_return_none(self):
        self.assertIsNone(convert(float("nan"), "ft", "cm"))
        self.assertIsNone(convert(float("inf"), "ft", "cm"))
        self.assertIsNone(convert("5", "ft", "cm"))
        self.assertIsNone(convert(None, "ft", "cm"))
        self.assertIsNone(convert(True, "ft", "cm"))


class TestFormatResult(unittest.TestCase):
    CASES = [
        (30.48, "30.48"),
        (167.64, "167.64"),
        (1609.344, "1,609.344"),
        (1234567.89, "1,234,567.89"),
        (1000000, "1,000,000"),
        (0.123456789, "0.123457"),
        (0.1, "0.1"),
        (0, "0"),
        (1e-07, "0"),
        (-1234.5, "-1,234.5"),
        (-1e-07, "0"),
        (3.75, "3.75"),
        (37.77777777777778, "37.777778"),
    ]

    def test_format_cases(self):
        for value, expected in self.CASES:
            with self.subTest(repr(value)):
                self.assertEqual(format_result(value), expected)

    def test_format_invalid(self):
        self.assertEqual(format_result(None), "")
        self.assertEqual(format_result(float("nan")), "")
        self.assertEqual(format_result(float("inf")), "")

    def test_camel_case_alias(self):
        self.assertEqual(conversions.formatResult(30.48), "30.48")


class TestDataIntegrity(unittest.TestCase):
    def test_required_categories_present(self):
        for cat in ("length", "weight", "temperature", "area", "volume"):
            self.assertIn(cat, DATA["categories"])

    def test_minimum_unit_count(self):
        total = sum(len(cat["units"]) for cat in DATA["categories"].values())
        self.assertGreaterEqual(total, 30, f"only {total} units defined")

    def test_base_unit_exists_and_is_identity(self):
        for cat_key, cat in DATA["categories"].items():
            self.assertIn("base", cat, f"{cat_key}: missing base")
            self.assertIn(cat["base"], cat["units"],
                          f"{cat_key}: base '{cat['base']}' not defined")
            base_def = cat["units"][cat["base"]]
            if "affine" in base_def:
                self.assertEqual(base_def["affine"]["a"], 1)
                self.assertEqual(base_def["affine"]["b"], 0)
            else:
                self.assertEqual(base_def["factor"], 1,
                                 f"{cat_key}: base factor must be 1")

    def test_unit_definitions_valid(self):
        for cat_key, cat in DATA["categories"].items():
            for unit_key, unit_def in cat["units"].items():
                label = f"{cat_key}.{unit_key}"
                self.assertTrue(unit_def.get("nameKo"), f"{label}: missing nameKo")
                self.assertTrue(unit_def.get("symbol"), f"{label}: missing symbol")
                affine = unit_def.get("affine")
                if affine is not None:
                    self.assertTrue(math.isfinite(affine["a"]), f"{label}: bad affine.a")
                    self.assertTrue(math.isfinite(affine["b"]), f"{label}: bad affine.b")
                    self.assertNotEqual(affine["a"], 0, f"{label}: affine.a is 0")
                else:
                    factor = unit_def.get("factor")
                    self.assertIsNotNone(factor, f"{label}: missing factor")
                    self.assertTrue(math.isfinite(factor), f"{label}: bad factor")
                    self.assertGreater(factor, 0, f"{label}: factor must be > 0")

    def test_unit_codes_globally_unique(self):
        build_unit_index(DATA)  # raises on duplicates

    def test_pairs_valid(self):
        index = build_unit_index(DATA)
        self.assertGreaterEqual(len(DATA["pairs"]), 30, "too few popular pairs")
        for pair in DATA["pairs"]:
            label = f"pair {pair.get('from')}->{pair.get('to')}"
            self.assertIn(pair["from"], index, f"{label}: unknown from unit")
            self.assertIn(pair["to"], index, f"{label}: unknown to unit")
            self.assertEqual(index[pair["from"]][0], index[pair["to"]][0],
                             f"{label}: units in different categories")
            values = pair.get("values")
            self.assertIsInstance(values, list, f"{label}: values not a list")
            self.assertGreater(len(values), 0, f"{label}: empty values")
            for v in values:
                self.assertIsInstance(v, (int, float), f"{label}: non-numeric value {v!r}")
                self.assertTrue(math.isfinite(v), f"{label}: non-finite value {v!r}")


class TestCrossCheckFixture(unittest.TestCase):
    """Dump Python results for all pair/value combos so the Node suite can
    verify the JS engine computes identical numbers."""

    def test_generate_cross_check_fixture(self):
        combos = []
        for pair in DATA["pairs"]:
            for value in pair["values"]:
                result = convert(value, pair["from"], pair["to"])
                self.assertIsNotNone(
                    result, f"{value} {pair['from']}->{pair['to']} returned None")
                combos.append({
                    "from": pair["from"],
                    "to": pair["to"],
                    "value": value,
                    "expected": result,
                })
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        with open(CROSS_CHECK_PATH, "w", encoding="utf-8") as fh:
            json.dump({"tolerance": REL_TOL, "combos": combos}, fh, indent=1)
        self.assertGreater(len(combos), 300, "unexpectedly few cross-check combos")


if __name__ == "__main__":
    unittest.main()
