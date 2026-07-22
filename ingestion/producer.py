"""Send synthetic events to Kafka topic nexusflow-events."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from ingestion.event_generator import generate_events_batch
from kafka import KafkaProducer

IN_DOCKER = Path("/.dockerenv").exists()
KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "kafka:9092" if IN_DOCKER else "127.0.0.1:29092",
)
KAFKA_TOPIC = "nexusflow-events"


def send_events_to_kafka(events, broker=KAFKA_BROKER, topic=KAFKA_TOPIC):
    producer = KafkaProducer(
        bootstrap_servers=[broker],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    for event in events:
        producer.send(topic, value=event)
    producer.flush()
    print(f"Sent {len(events)} events to Kafka topic '{topic}'")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Produce synthetic NexusFlow events to Kafka.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Send a single batch then exit.",
    )
    parser.add_argument(
        "--batches",
        type=int,
        default=None,
        metavar="N",
        help="Send N batches then exit (default: run forever until Ctrl+C).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        metavar="N",
        help="Events per batch (default: 10).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        metavar="SEC",
        help="Seconds between batches when running more than once (default: 1).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.batches is not None and args.batches < 1:
        raise SystemExit("--batches must be >= 1")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    if args.once:
        limit = 1
    elif args.batches is not None:
        limit = args.batches
    else:
        limit = None

    print("Starting Kafka producer...")
    sent = 0
    while True:
        send_events_to_kafka(generate_events_batch(args.batch_size))
        sent += 1
        if limit is not None and sent >= limit:
            print(f"Done after {sent} batch(es).")
            return
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
