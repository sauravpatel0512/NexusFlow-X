"""CLI flags for the Kafka producer (no broker required)."""


from ingestion.producer import _parse_args


def test_parse_args_defaults():
    args = _parse_args([])
    assert args.once is False
    assert args.batches is None
    assert args.batch_size == 10
    assert args.sleep == 1.0


def test_parse_args_once_and_batches():
    once = _parse_args(["--once"])
    assert once.once is True
    batches = _parse_args(["--batches", "30", "--batch-size", "5", "--sleep", "0.5"])
    assert batches.batches == 30
    assert batches.batch_size == 5
    assert batches.sleep == 0.5
