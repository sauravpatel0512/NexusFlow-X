"""Quarantine layout helpers (by medallion layer) + parse_failures from metrics extra."""
from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path

# Known quarantine subdirs written by Bronze/Silver streams (see LOCAL_RUNBOOK).
KNOWN_LAYERS = ("bronze", "bronze_parse", "silver")


def _data_root() -> Path:
    env = os.getenv("NEXUSFLOW_DATA_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data"


def quarantine_root(data_root: Path | None = None) -> Path:
    return (data_root or _data_root()) / "quarantine"


def count_parquet_files(layer_dir: Path) -> int:
    if not layer_dir.is_dir():
        return 0
    return sum(1 for _ in layer_dir.rglob("*.parquet"))


def quarantine_breakdown(
    data_root: Path | None = None,
    *,
    layers: Iterable[str] = KNOWN_LAYERS,
) -> dict[str, dict[str, int]]:
    """Return ``{layer: {"files": N}}`` for each known quarantine subdirectory.

    Layers with no directory still appear with ``files: 0`` so the dashboard
    can show an empty bronze_parse / silver / bronze split.
    """
    root = quarantine_root(data_root)
    out: dict[str, dict[str, int]] = {}
    for layer in layers:
        out[layer] = {"files": count_parquet_files(root / layer)}
    # Surface unexpected quarantine folders (e.g. future gold DQ).
    if root.is_dir():
        known = set(layers)
        for child in sorted(root.iterdir()):
            if child.is_dir() and child.name not in known:
                out[child.name] = {"files": count_parquet_files(child)}
    return out


def sum_parse_failures(metrics_lines: Iterable[Mapping] | None) -> int:
    """Sum ``extra.parse_failures`` across pipeline metrics NDJSON lines."""
    total = 0
    if not metrics_lines:
        return 0
    for line in metrics_lines:
        extra = line.get("extra") if isinstance(line, Mapping) else None
        if not isinstance(extra, Mapping):
            continue
        raw = extra.get("parse_failures", 0)
        try:
            total += int(raw or 0)
        except (TypeError, ValueError):
            continue
    return total
