"""CLI: duration-based soak / load producer for NexusFlow."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingestion.soak_load import build_plan, parse_args, run_soak  # noqa: E402


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
