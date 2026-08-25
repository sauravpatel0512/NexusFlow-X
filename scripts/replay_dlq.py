"""Revalidate DLQ envelopes and republish schema-valid payloads to the main topic."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from kafka import KafkaConsumer, TopicPartition

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingestion.contract import KAFKA_TOPIC_DLQ, KAFKA_TOPIC_EVENTS  # noqa: E402
from ingestion.dlq_replay import replay_envelopes  # noqa: E402

IN_DOCKER = Path("/.dockerenv").exists()
KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "kafka:9092" if IN_DOCKER else "127.0.0.1:29092",
)
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", KAFKA_TOPIC_DLQ)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay valid DLQ payloads to the main topic.")
    parser.add_argument("-n", "--max", type=int, default=10, help="Max DLQ messages to scan.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify only; do not publish to the main topic.",
    )
    parser.add_argument(
        "--target-topic",
        default=None,
        help="Override source_topic on replay (default: honor envelope source_topic).",
    )
    parser.add_argument("--timeout-ms", type=int, default=5000)
    return parser.parse_args(argv)


def _collect_envelopes(consumer: KafkaConsumer, max_messages: int) -> list[dict]:
    out: list[dict] = []
    for msg in consumer:
        value = msg.value
        if isinstance(value, dict):
            out.append(value)
        if len(out) >= max_messages:
            break
    return out


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.max < 1:
        raise SystemExit("--max must be >= 1")

    from kafka import KafkaProducer

    consumer = KafkaConsumer(
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        enable_auto_commit=False,
        consumer_timeout_ms=args.timeout_ms,
    )
    partitions = consumer.partitions_for_topic(KAFKA_DLQ_TOPIC)
    if not partitions:
        print(f"No partitions for topic '{KAFKA_DLQ_TOPIC}' (create with make topic).")
        consumer.close()
        return

    tps = [TopicPartition(KAFKA_DLQ_TOPIC, p) for p in sorted(partitions)]
    consumer.assign(tps)
    consumer.seek_to_beginning(*tps)
    envelopes = _collect_envelopes(consumer, args.max)
    consumer.close()

    if args.target_topic:
        envelopes = [{**e, "source_topic": args.target_topic} for e in envelopes]

    producer = None if args.dry_run else KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    class _DryRunProducer:
        def send(self, *_args, **_kwargs):
            return None

        def flush(self):
            return None

        def close(self):
            return None

    try:
        result = replay_envelopes(
            envelopes,
            producer=_DryRunProducer() if args.dry_run else producer,
            default_topic=KAFKA_TOPIC_EVENTS,
            dry_run=args.dry_run,
        )
    finally:
        if producer is not None:
            producer.close()

    mode = "dry-run" if args.dry_run else "replay"
    print(
        f"DLQ {mode}: scanned={result.scanned} replayed={result.replayed} "
        f"skipped_invalid={result.skipped_invalid} skipped_malformed={result.skipped_malformed}"
    )


if __name__ == "__main__":
    main()
