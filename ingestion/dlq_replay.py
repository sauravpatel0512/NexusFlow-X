"""Classify DLQ envelopes and replay schema-valid payloads to the main topic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ingestion.contract import KAFKA_TOPIC_EVENTS, validate_event


@dataclass
class ReplayResult:
    scanned: int = 0
    replayed: int = 0
    skipped_invalid: int = 0
    skipped_malformed: int = 0


def classify_envelope(envelope: Any) -> tuple[str, dict[str, Any] | None]:
    """Return (status, payload). status: replayable | still_invalid | malformed."""
    if not isinstance(envelope, dict):
        return "malformed", None
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return "malformed", None
    if validate_event(payload):
        return "still_invalid", None
    return "replayable", payload


def replay_envelopes(
    envelopes: Iterable[Mapping[str, Any] | dict[str, Any]],
    *,
    producer: Any,
    default_topic: str = KAFKA_TOPIC_EVENTS,
    dry_run: bool = False,
) -> ReplayResult:
    result = ReplayResult()
    for envelope in envelopes:
        result.scanned += 1
        status, payload = classify_envelope(envelope)
        if status == "malformed":
            result.skipped_malformed += 1
            continue
        if status == "still_invalid":
            result.skipped_invalid += 1
            continue
        topic = envelope.get("source_topic") or default_topic
        if not dry_run:
            producer.send(topic, value=payload)
        result.replayed += 1
    if not dry_run and hasattr(producer, "flush"):
        producer.flush()
    return result
