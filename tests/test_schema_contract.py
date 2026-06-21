"""Contract tests: producer output matches the canonical Bronze schema,
and quality_rules.yaml only references fields the schema contains.

The canonical contract lives in ingestion/schemas.py. Streaming jobs should
import bronze_validate_fields / silver_validate_fields from there.
"""
from __future__ import annotations

import os

from ingestion.event_generator import generate_event
from ingestion.data_quality import load_quality_rules
from ingestion.schemas import (
    BRONZE_EXTRA_KEYS,
    BRONZE_LEAF_FIELDS,
    BRONZE_METRICS_KEYS,
    BRONZE_TOP_LEVEL_KEYS,
    SILVER_FLAT_FIELDS,
)


# -----------------------------------------------------------------------
# 1. Producer payload matches the canonical Bronze schema contract
# -----------------------------------------------------------------------

def test_producer_top_level_keys():
    event = generate_event()
    assert set(event.keys()) == BRONZE_TOP_LEVEL_KEYS


def test_producer_metrics_keys():
    event = generate_event()
    assert set(event["metrics"].keys()) == BRONZE_METRICS_KEYS


def test_producer_extra_keys():
    event = generate_event()
    assert set(event["extra"].keys()) == BRONZE_EXTRA_KEYS


def test_silver_flat_fields_match_bronze_leaves():
    """Silver/Gold rely on flattening nested metrics/extra into these columns."""
    assert frozenset(SILVER_FLAT_FIELDS) == BRONZE_LEAF_FIELDS


def test_quality_rules_numeric_fields_are_metrics_only():
    """DQ range checks run on flattened metric columns, not arbitrary keys."""
    rules_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ingestion",
        "quality_rules.yaml",
    )
    rules = load_quality_rules(rules_path)
    for field in rules.get("numeric_ranges", {}):
        assert field in BRONZE_METRICS_KEYS, (
            f"numeric_ranges.{field} must be a Bronze metrics key"
        )


# -----------------------------------------------------------------------
# 2. Quality rules only reference leaf fields in the schema
# -----------------------------------------------------------------------

def test_quality_rules_fields_exist_in_schema():
    rules_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ingestion",
        "quality_rules.yaml",
    )
    rules = load_quality_rules(rules_path)

    for field in rules.get("numeric_ranges", {}):
        assert field in BRONZE_LEAF_FIELDS, (
            f"quality_rules.yaml references '{field}' which is not a leaf field in the schema contract"
        )
