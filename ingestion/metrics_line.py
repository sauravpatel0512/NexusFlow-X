"""Append one NDJSON line per micro-batch to data/metrics/pipeline_metrics.jsonl.

Each line is a JSON object: ``ts`` (Unix epoch seconds), ``layer``, ``batch_id``,
``row_count``, optional ``error``, optional ``extra``.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ingestion.paths import data_root

FILENAME = "pipeline_metrics.jsonl"


def append_pipeline_metric(
    layer: str,
    batch_id: int,
    row_count: int,
    *,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "ts": int(time.time()),
        "layer": layer,
        "batch_id": batch_id,
        "row_count": row_count,
        "error": error,
    }
    if extra:
        payload["extra"] = extra
    metrics_dir = data_root() / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    path = metrics_dir / FILENAME
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
