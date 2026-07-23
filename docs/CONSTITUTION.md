# NexusFlow-X — project principles

1. **Local-first.** Docker Compose on a laptop by default. Cloud/K8s stay on [ROADMAP.md](ROADMAP.md).
2. **Medallion honesty.** Bronze = raw Kafka; Silver = flatten + quality rules; Gold = hourly aggregates.
3. **Fail visibly.** Bad rows go to quarantine; metrics record batch `error` instead of silent drops.
4. **Reproducible ops.** Prefer Makefile/runbook commands; shell scripts stay LF-only.
5. **Evidence over claims.** [validation-log.md](validation-log.md) and [assets/dashboard.png](assets/dashboard.png) must match the running stack.
