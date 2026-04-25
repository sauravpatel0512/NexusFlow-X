import os
import numbers

import yaml


def test_quality_rules_loads_and_has_numeric_ranges():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "ingestion", "quality_rules.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "numeric_ranges" in data
    for key in ("distance", "temperature", "amount", "duration"):
        assert key in data["numeric_ranges"]
        assert "min" in data["numeric_ranges"][key]
        assert "max" in data["numeric_ranges"][key]


def test_quality_rules_numeric_ranges_are_consistent_and_numeric():
    """Catch swapped min/max or string bounds from bad YAML edits."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "ingestion", "quality_rules.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    ranges = data["numeric_ranges"]
    for name, spec in ranges.items():
        lo, hi = spec["min"], spec["max"]
        assert isinstance(lo, numbers.Real) and not isinstance(
            lo, bool
        ), f"{name}.min must be numeric"
        assert isinstance(hi, numbers.Real) and not isinstance(
            hi, bool
        ), f"{name}.max must be numeric"
        assert lo <= hi, f"{name}: min must be <= max (got {lo} > {hi})"
