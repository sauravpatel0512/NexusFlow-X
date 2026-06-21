"""Canonical Bronze and Silver field contracts for NexusFlow-X.

Producer JSON, Bronze streaming, Silver flattening, and quality_rules.yaml
should all stay aligned with these names. Contract tests import from here.
"""
from __future__ import annotations

BRONZE_TOP_LEVEL_KEYS = frozenset(
    {
        "event_id",
        "timestamp",
        "event_type",
        "source",
        "status",
        "metrics",
        "extra",
    }
)

BRONZE_METRICS_KEYS = frozenset(
    {
        "distance",
        "temperature",
        "amount",
        "duration",
    }
)

BRONZE_EXTRA_KEYS = frozenset({"note"})

BRONZE_LEAF_FIELDS = frozenset(
    (BRONZE_TOP_LEVEL_KEYS - {"metrics", "extra"})
    | BRONZE_METRICS_KEYS
    | BRONZE_EXTRA_KEYS
)

# Silver: metrics/extra flattened to top-level columns (see silver_stream.flatten_and_clean).
SILVER_FLAT_FIELDS: tuple[str, ...] = (
    "event_id",
    "timestamp",
    "event_type",
    "source",
    "status",
    "distance",
    "temperature",
    "amount",
    "duration",
    "note",
)


def bronze_validate_fields() -> list[str]:
    """Nested Bronze batch columns for validate_schema."""
    return sorted(BRONZE_TOP_LEVEL_KEYS)


def silver_validate_fields() -> list[str]:
    """Flattened Silver batch columns for validate_schema."""
    return list(SILVER_FLAT_FIELDS)
