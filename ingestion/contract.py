"""JSON Schema contract + DLQ envelope helpers for NexusFlow events."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).resolve().parent / "event_schema.json"

KAFKA_TOPIC_EVENTS = "nexusflow-events"
KAFKA_TOPIC_DLQ = "nexusflow-events-dlq"

DLQ_ENVELOPE_KEYS = frozenset(
    {
        "error_type",
        "error_detail",
        "source_topic",
        "ingested_at",
        "payload",
    }
)


@lru_cache(maxsize=1)
def load_event_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _validator() -> Draft7Validator:
    return Draft7Validator(load_event_schema())


def validate_event(event: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors; empty list means valid."""
    errors: list[str] = []
    for err in sorted(_validator().iter_errors(event), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{path}: {err.message}")
    return errors


def build_dlq_record(
    payload: Any,
    *,
    error_type: str,
    error_detail: str,
    source_topic: str = KAFKA_TOPIC_EVENTS,
) -> dict[str, Any]:
    """Build the standard DLQ envelope for Kafka or tests."""
    return {
        "error_type": error_type,
        "error_detail": error_detail,
        "source_topic": source_topic,
        "ingested_at": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "payload": payload,
    }


def make_poison_event(kind: str = "missing_keys") -> dict[str, Any] | list[Any]:
    """Deliberately invalid payloads for DLQ demos (`--inject-poison`)."""
    if kind == "wrong_types":
        return {
            "event_id": 12345,
            "timestamp": True,
            "event_type": ["not", "a", "string"],
            "source": None,
            "status": {"nested": True},
            "metrics": "not-an-object",
            "extra": [],
        }
    if kind == "not_object":
        return ["not", "an", "object"]
    # default: missing required keys
    return {"event_id": "poison-demo", "status": "bad"}
