"""Send synthetic events to Kafka; JSON Schema gate + DLQ for poison payloads."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from ingestion.contract import (
    KAFKA_TOPIC_DLQ,
    KAFKA_TOPIC_EVENTS,
    build_dlq_record,
    make_poison_event,
    validate_event,
)
from ingestion.event_generator import generate_events_batch
from kafka import KafkaProducer

IN_DOCKER = Path("/.dockerenv").exists()
KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "kafka:9092" if IN_DOCKER else "127.0.0.1:29092",
)
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", KAFKA_TOPIC_EVENTS)
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", KAFKA_TOPIC_DLQ)


def _make_producer(broker: str = KAFKA_BROKER) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=[broker],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def send_events_to_kafka(
    events,
    broker=KAFKA_BROKER,
    topic=KAFKA_TOPIC,
    dlq_topic=KAFKA_DLQ_TOPIC,
    *,
    producer: KafkaProducer | None = None,
) -> tuple[int, int]:
    """Validate each event; valid → main topic, invalid → DLQ. Returns (ok, dlq)."""
    own_producer = producer is None
    prod = producer or _make_producer(broker)
    sent_ok = 0
    sent_dlq = 0
    try:
        for event in events:
            if isinstance(event, dict):
                errors = validate_event(event)
            else:
                errors = ["(root): event must be a JSON object"]
            if not errors:
                prod.send(topic, value=event)
                sent_ok += 1
                continue
            envelope = build_dlq_record(
                event,
                error_type="schema_validation",
                error_detail="; ".join(errors),
                source_topic=topic,
            )
            prod.send(dlq_topic, value=envelope)
            sent_dlq += 1
        prod.flush()
    finally:
        if own_producer:
            prod.close()
    print(
        f"Sent {sent_ok} ok → '{topic}', {sent_dlq} DLQ → '{dlq_topic}' "
        f"(broker {broker})"
    )
    return sent_ok, sent_dlq


def send_poison_to_dlq(
    count: int,
    broker=KAFKA_BROKER,
    topic=KAFKA_TOPIC,
    dlq_topic=KAFKA_DLQ_TOPIC,
    *,
    producer: KafkaProducer | None = None,
) -> int:
    """Publish N deliberately invalid payloads as DLQ envelopes (demo)."""
    kinds = ("missing_keys", "wrong_types", "not_object")
    own_producer = producer is None
    prod = producer or _make_producer(broker)
    sent = 0
    try:
        for i in range(count):
            kind = kinds[i % len(kinds)]
            poison = make_poison_event(kind)
            if isinstance(poison, dict):
                errors = validate_event(poison)
            else:
                errors = ["(root): event must be a JSON object"]
            envelope = build_dlq_record(
                poison,
                error_type="inject_poison",
                error_detail="; ".join(errors) or f"poison kind={kind}",
                source_topic=topic,
            )
            prod.send(dlq_topic, value=envelope)
            sent += 1
        prod.flush()
    finally:
        if own_producer:
            prod.close()
    print(f"Injected {sent} poison envelope(s) → DLQ '{dlq_topic}'")
    return sent


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Produce synthetic NexusFlow events to Kafka (JSON Schema + DLQ).",
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
    parser.add_argument(
        "--inject-poison",
        type=int,
        default=0,
        metavar="N",
        help="Publish N invalid payloads to the DLQ topic (demo), then continue.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.batches is not None and args.batches < 1:
        raise SystemExit("--batches must be >= 1")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    if args.inject_poison < 0:
        raise SystemExit("--inject-poison must be >= 0")

    if args.once:
        limit = 1
    elif args.batches is not None:
        limit = args.batches
    else:
        limit = None

    print("Starting Kafka producer (JSON Schema gate + DLQ)...")
    if args.inject_poison:
        send_poison_to_dlq(args.inject_poison)

    sent = 0
    total_ok = 0
    total_dlq = 0
    while True:
        ok, dlq = send_events_to_kafka(generate_events_batch(args.batch_size))
        total_ok += ok
        total_dlq += dlq
        sent += 1
        if limit is not None and sent >= limit:
            print(
                f"Done after {sent} batch(es). totals ok={total_ok} dlq={total_dlq}"
            )
            return
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
