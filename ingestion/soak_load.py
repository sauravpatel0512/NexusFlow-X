"""Duration-based soak / load helpers (Kafka-free planning + run loop)."""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any

from ingestion.event_generator import generate_events_batch
from ingestion.producer import send_events_to_kafka, send_poison_to_dlq


@dataclass
class SoakPlan:
    duration_sec: float
    batch_size: int
    sleep_sec: float
    poison_every: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Soak-load NexusFlow: bounded duration, rate, optional poison mix.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        metavar="SEC",
        help="How long to run (default: 60).",
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
        default=None,
        metavar="SEC",
        help="Seconds between batches (default: derived from --rate or 1.0).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=None,
        metavar="EPS",
        help="Target events/sec (sets sleep ≈ batch_size / rate when --sleep omitted).",
    )
    parser.add_argument(
        "--poison-every",
        type=int,
        default=0,
        metavar="N",
        help="Inject 1 poison DLQ envelope every N batches (0 = never).",
    )
    return parser.parse_args(argv)


def build_plan(args: argparse.Namespace) -> SoakPlan:
    if args.duration <= 0:
        raise SystemExit("--duration must be > 0")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    if args.poison_every < 0:
        raise SystemExit("--poison-every must be >= 0")
    if args.rate is not None and args.rate <= 0:
        raise SystemExit("--rate must be > 0")

    if args.sleep is not None:
        sleep_sec = args.sleep
    elif args.rate is not None:
        sleep_sec = max(0.0, args.batch_size / args.rate)
    else:
        sleep_sec = 1.0
    if sleep_sec < 0:
        raise SystemExit("--sleep must be >= 0")

    return SoakPlan(
        duration_sec=float(args.duration),
        batch_size=int(args.batch_size),
        sleep_sec=float(sleep_sec),
        poison_every=int(args.poison_every),
    )


def run_soak(plan: SoakPlan, *, producer: Any = None) -> dict[str, float | int]:
    """Run soak loop. Optional producer for tests (Kafka-free)."""
    started = time.monotonic()
    batches = 0
    total_ok = 0
    total_dlq = 0
    poison = 0

    while (time.monotonic() - started) < plan.duration_sec:
        ok, dlq = send_events_to_kafka(
            generate_events_batch(plan.batch_size),
            producer=producer,
        )
        total_ok += ok
        total_dlq += dlq
        batches += 1
        if plan.poison_every and batches % plan.poison_every == 0:
            poison += send_poison_to_dlq(1, producer=producer)
        if (time.monotonic() - started) >= plan.duration_sec:
            break
        if plan.sleep_sec > 0:
            time.sleep(plan.sleep_sec)

    elapsed = max(time.monotonic() - started, 1e-9)
    events = total_ok + total_dlq
    return {
        "batches": batches,
        "ok": total_ok,
        "dlq": total_dlq,
        "poison": poison,
        "elapsed_sec": round(elapsed, 3),
        "eps": round(events / elapsed, 2),
    }


def main(argv: list[str] | None = None) -> None:
    plan = build_plan(parse_args(argv))
    print(
        f"Soak starting: duration={plan.duration_sec}s batch_size={plan.batch_size} "
        f"sleep={plan.sleep_sec}s poison_every={plan.poison_every}"
    )
    stats = run_soak(plan)
    print(
        f"Soak done: batches={stats['batches']} ok={stats['ok']} dlq={stats['dlq']} "
        f"poison={stats['poison']} elapsed={stats['elapsed_sec']}s eps={stats['eps']}"
    )


if __name__ == "__main__":
    main()
