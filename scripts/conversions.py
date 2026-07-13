"""baroconvert conversion engine (Python).

Mirror of js/convert.js — the two engines MUST behave identically.

Data contract (data/units.json):
  - Linear unit:  toBase(v) = v * factor,        fromBase(v) = v / factor
  - Affine unit:  toBase(v) = a * v + b,         fromBase(v) = (v - b) / a
    (when "affine" is present, "factor" is ignored)

Public API:
  load_units(path=DEFAULT_DATA_PATH) -> dict
  convert(value, from_unit, to_unit, data=None) -> float | None
  format_result(value) -> str          (alias: formatResult)
"""

import json
import math
from pathlib import Path

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "units.json"

_default_data_cache = None


def load_units(path=DEFAULT_DATA_PATH):
    """Load and return the units database from a JSON file path."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "categories" not in data:
        raise ValueError(f"invalid units data file: {path}")
    return data


def _get_default_data():
    global _default_data_cache
    if _default_data_cache is None:
        _default_data_cache = load_units()
    return _default_data_cache


def build_unit_index(data):
    """Map unit code -> (category_key, unit_def). Unit codes are globally unique."""
    index = {}
    for cat_key, cat in data["categories"].items():
        for unit_key, unit_def in cat["units"].items():
            if unit_key in index:
                raise ValueError(f"duplicate unit code across categories: {unit_key}")
            index[unit_key] = (cat_key, unit_def)
    return index


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _to_base(value, unit_def):
    affine = unit_def.get("affine")
    if affine is not None:
        return affine["a"] * value + affine["b"]
    return value * unit_def["factor"]


def _from_base(value, unit_def):
    affine = unit_def.get("affine")
    if affine is not None:
        return (value - affine["b"]) / affine["a"]
    return value / unit_def["factor"]


def convert(value, from_unit, to_unit, data=None):
    """Convert value between two units. Returns None when conversion is impossible.

    None is returned for: non-numeric/non-finite value, unknown unit codes,
    or units belonging to different categories.
    """
    if not _is_number(value) or not math.isfinite(value):
        return None
    if data is None:
        data = _get_default_data()
    index = build_unit_index(data)
    if from_unit not in index or to_unit not in index:
        return None
    from_cat, from_def = index[from_unit]
    to_cat, to_def = index[to_unit]
    if from_cat != to_cat:
        return None
    return _from_base(_to_base(float(value), from_def), to_def)


def format_result(value):
    """Format a numeric result for display.

    Rules (identical to js/convert.js formatResult):
      - None / non-finite -> ""
      - round to at most 6 decimal places
      - strip trailing zeros in the fraction
      - thousands separators (commas) in the integer part
      - never emit "-0"
    """
    if not _is_number(value) or not math.isfinite(value):
        return ""
    text = f"{abs(value):.6f}"
    int_part, frac_part = text.split(".")
    frac_part = frac_part.rstrip("0")
    grouped = f"{int(int_part):,}"
    out = grouped + (f".{frac_part}" if frac_part else "")
    negative = value < 0 and out != "0"
    return ("-" + out) if negative else out


# camelCase alias to mirror the JS API name exactly.
formatResult = format_result
