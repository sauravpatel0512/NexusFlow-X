import uuid

from ingestion.event_generator import generate_event, generate_events_batch

REQUIRED_KEYS = {
    "event_id",
    "timestamp",
    "event_type",
    "source",
    "status",
    "metrics",
    "extra",
}


def test_generate_event_shape():
    e = generate_event("trip_start")
    assert set(e.keys()) == REQUIRED_KEYS
    assert e["event_type"] == "trip_start"
    uuid.UUID(e["event_id"])
    assert "Z" in e["timestamp"] or e["timestamp"].endswith("Z")
    assert set(e["metrics"].keys()) == {"distance", "temperature", "amount", "duration"}
    assert "note" in e["extra"]


def test_generate_events_batch_length():
    batch = generate_events_batch(3)
    assert len(batch) == 3
    for ev in batch:
        assert set(ev.keys()) == REQUIRED_KEYS
