"""Producer routing: schema gate → main vs DLQ (fake producer, no broker)."""
from __future__ import annotations

from ingestion.contract import make_poison_event
from ingestion.event_generator import generate_event
from ingestion.producer import _parse_args, send_events_to_kafka, send_poison_to_dlq


class _FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    def send(self, topic, value=None, **_kwargs):
        self.sent.append((topic, value))

    def flush(self):
        return None

    def close(self):
        return None


def test_parse_args_inject_poison():
    args = _parse_args(["--inject-poison", "5", "--once"])
    assert args.inject_poison == 5
    assert args.once is True


def test_send_events_routes_invalid_to_dlq():
    fake = _FakeProducer()
    ok, dlq = send_events_to_kafka(
        [generate_event(), make_poison_event("missing_keys")],
        producer=fake,
    )
    assert ok == 1
    assert dlq == 1
    topics = [t for t, _ in fake.sent]
    assert topics.count("nexusflow-events") == 1
    assert topics.count("nexusflow-events-dlq") == 1
    envelope = next(v for t, v in fake.sent if t == "nexusflow-events-dlq")
    assert envelope["error_type"] == "schema_validation"
    assert "error_detail" in envelope


def test_send_poison_to_dlq_only():
    fake = _FakeProducer()
    n = send_poison_to_dlq(3, producer=fake)
    assert n == 3
    assert all(t == "nexusflow-events-dlq" for t, _ in fake.sent)
    assert all(v["error_type"] == "inject_poison" for _, v in fake.sent)
