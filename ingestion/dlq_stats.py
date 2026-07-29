"""Kafka DLQ depth helpers (end-offset sum — no message scan)."""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from ingestion.contract import KAFKA_TOPIC_DLQ

IN_DOCKER = Path("/.dockerenv").exists()
KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "kafka:9092" if IN_DOCKER else "127.0.0.1:29092",
)
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", KAFKA_TOPIC_DLQ)


def sum_end_offsets(end_offsets: Mapping[object, int]) -> int:
    """Sum partition high-water marks (= approximate message count if never truncated)."""
    return int(sum(int(v) for v in end_offsets.values()))


def fetch_dlq_depth(
    *,
    broker: str | None = None,
    topic: str | None = None,
    timeout_ms: int = 3000,
) -> tuple[int | None, str | None]:
    """Return (depth, error). depth is None when Kafka is unreachable / topic missing."""
    broker = broker or KAFKA_BROKER
    topic = topic or KAFKA_DLQ_TOPIC
    try:
        from kafka import KafkaConsumer, TopicPartition
    except Exception as ex:  # pragma: no cover - import env issues
        return None, f"kafka-python unavailable: {ex}"

    consumer = None
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=[broker],
            enable_auto_commit=False,
            consumer_timeout_ms=timeout_ms,
        )
        partitions = consumer.partitions_for_topic(topic)
        if not partitions:
            return 0, f"topic '{topic}' not found (run make topic)"
        tps = [TopicPartition(topic, p) for p in sorted(partitions)]
        ends = consumer.end_offsets(tps)
        return sum_end_offsets(ends), None
    except Exception as ex:
        return None, str(ex)
    finally:
        if consumer is not None:
            try:
                consumer.close()
            except Exception:
                pass
