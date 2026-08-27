"""Soak load planner (no Kafka)."""
from __future__ import annotations

from ingestion.soak_load import build_plan, parse_args


def test_parse_defaults():
    args = parse_args([])
    assert args.duration == 60.0
    assert args.batch_size == 10
    assert args.poison_every == 0


def test_build_plan_derives_sleep_from_rate():
    args = parse_args(["--duration", "30", "--batch-size", "50", "--rate", "100"])
    plan = build_plan(args)
    assert plan.duration_sec == 30.0
    assert plan.batch_size == 50
    assert abs(plan.sleep_sec - 0.5) < 1e-9


def test_build_plan_explicit_sleep_wins():
    args = parse_args(["--duration", "10", "--sleep", "0.2", "--rate", "999"])
    plan = build_plan(args)
    assert plan.sleep_sec == 0.2
