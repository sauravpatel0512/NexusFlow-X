"""DLQ replay helper (no Kafka broker)."""
from __future__ import annotations

from ingestion.contract import build_dlq_record, make_poison_event
from ingestion.dlq_replay import classify_envelope, replay_envelopes
from ingestion.event_generator import generate_event


class _FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    def send(self, topic, value=None, **_kwargs):
        self.sent.append((topic, value))

    def flush(self):
        return None


def test_classify_replayable_envelope():
    event = generate_event()
    envelope = build_dlq_record(event, error_type="test", error_detail="demo")
    status, payload = classify_envelope(envelope)
    assert status == "replayable"
    assert payload == event


def test_classify_poison_still_invalid():
    poison = make_poison_event("missing_keys")
    envelope = build_dlq_record(poison, error_type="schema_validation", error_detail="bad")
    status, payload = classify_envelope(envelope)
    assert status == "still_invalid"
    assert payload is None


def test_classify_malformed_envelope():
    status, payload = classify_envelope(["not", "dict"])
    assert status == "malformed"
    assert payload is None


def test_replay_envelopes_sends_valid_only():
    event = generate_event()
    valid = build_dlq_record(event, error_type="test", error_detail="ok")
    invalid = build_dlq_record(
        make_poison_event("missing_keys"),
        error_type="schema_validation",
        error_detail="bad",
    )
    fake = _FakeProducer()
    result = replay_envelopes([valid, invalid, "bad"], producer=fake)
    assert result.scanned == 3
    assert result.replayed == 1
    assert result.skipped_invalid == 1
    assert result.skipped_malformed == 1
    assert len(fake.sent) == 1
    assert fake.sent[0][0] == "nexusflow-events"
    assert fake.sent[0][1] == event


def test_replay_dry_run_does_not_send():
    event = generate_event()
    envelope = build_dlq_record(event, error_type="test", error_detail="ok")
    fake = _FakeProducer()
    result = replay_envelopes([envelope], producer=fake, dry_run=True)
    assert result.replayed == 1
    assert fake.sent == []
