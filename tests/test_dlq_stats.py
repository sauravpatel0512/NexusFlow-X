"""DLQ depth helpers (no Kafka required)."""
from __future__ import annotations

from ingestion.dlq_stats import sum_end_offsets


def test_sum_end_offsets_empty():
    assert sum_end_offsets({}) == 0


def test_sum_end_offsets_partitions():
    # Simulate TopicPartition -> high-water mark
    offsets = {"p0": 10, "p1": 5, "p2": 0}
    assert sum_end_offsets(offsets) == 15
