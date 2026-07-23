# NexusFlow-X — project principles

Short principles for contributors and recruiters reviewing this portfolio repo.

1. **Local-first.** The default path is Docker Compose on a laptop. Cloud, Kubernetes, and managed services stay on the [production ROADMAP](ROADMAP.md).
2. **Medallion honesty.** Bronze is raw Kafka payloads; Silver applies schema flatten + quality rules; Gold is hourly aggregates only.
3. **Fail visibly.** Bad rows quarantine; batch metrics record `error` when a micro-batch fails—do not hide failures in silent drops.
4. **Reproducible ops.** Prefer Makefile / runbook commands over one-off tribal knowledge; keep shell scripts LF-only.
5. **Evidence over claims.** Validation and screenshots ([validation-log.md](validation-log.md), [assets/dashboard.png](assets/dashboard.png)) should match what the code actually does.
