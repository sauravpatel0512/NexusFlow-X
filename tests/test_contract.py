"""JSON Schema contract + DLQ envelope tests (no Kafka required)."""
from __future__ import annotations

from ingestion.contract import (
    DLQ_ENVELOPE_KEYS,
    build_dlq_record,
    load_event_schema,
    make_poison_event,
    validate_event,
)
from ingestion.event_generator import generate_event
from ingestion.schemas import BRONZE_METRICS_KEYS, BRONZE_TOP_LEVEL_KEYS


def test_generated_event_passes_json_schema():
    assert validate_event(generate_event()) == []


def test_json_schema_required_keys_match_schemas_py():
    schema = load_event_schema()
    assert set(schema["required"]) == BRONZE_TOP_LEVEL_KEYS
    metrics_required = set(schema["properties"]["metrics"]["required"])
    assert metrics_required == BRONZE_METRICS_KEYS
    assert set(schema["properties"]["metrics"]["properties"]) == BRONZE_METRICS_KEYS
    assert set(schema["properties"]["extra"]["properties"]) == {"note"}


def test_poison_missing_keys_fails():
    errors = validate_event(make_poison_event("missing_keys"))
    assert errors
    assert any("required" in e.lower() or "event_type" in e for e in errors)


def test_poison_wrong_types_fails():
    errors = validate_event(make_poison_event("wrong_types"))
    assert len(errors) >= 1


def test_poison_not_object_handled_by_caller_shape():
    poison = make_poison_event("not_object")
    assert not isinstance(poison, dict)


def test_dlq_envelope_shape():
    record = build_dlq_record(
        {"broken": True},
        error_type="schema_validation",
        error_detail="missing event_id",
    )
    assert set(record.keys()) == DLQ_ENVELOPE_KEYS
    assert record["error_type"] == "schema_validation"
    assert record["error_detail"] == "missing event_id"
    assert record["source_topic"] == "nexusflow-events"
    assert record["payload"] == {"broken": True}
    assert record["ingested_at"].endswith("Z")
