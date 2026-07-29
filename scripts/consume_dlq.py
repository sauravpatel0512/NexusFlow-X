"""Print recent messages from the NexusFlow Kafka DLQ topic."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from kafka import KafkaConsumer, TopicPartition

# Allow `python scripts/consume_dlq.py` from repo root.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingestion.contract import KAFKA_TOPIC_DLQ  # noqa: E402

IN_DOCKER = Path("/.dockerenv").exists()
KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "kafka:9092" if IN_DOCKER else "127.0.0.1:29092",
)
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", KAFKA_TOPIC_DLQ)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consume NexusFlow DLQ messages.")
    parser.add_argument(
        "-n",
        "--max",
        type=int,
        default=10,
        metavar="N",
        help="Max messages to print (default: 10).",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=5000,
        help="Poll timeout in ms when no more messages (default: 5000).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.max < 1:
        raise SystemExit("--max must be >= 1")

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
    # Read from earliest so demo poison messages are visible without a consumer group.
    consumer.seek_to_beginning(*tps)

    printed = 0
    print(f"Reading up to {args.max} message(s) from '{KAFKA_DLQ_TOPIC}'...")
    for msg in consumer:
        print(json.dumps(msg.value, indent=2, default=str))
        print("---")
        printed += 1
        if printed >= args.max:
            break
    consumer.close()
    print(f"Printed {printed} message(s).")


if __name__ == "__main__":
    main()
