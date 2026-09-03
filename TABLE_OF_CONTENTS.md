# NewsIQ — Table of Contents

> **Current truth:** partial MVP / implementation project. Python services, PostgreSQL schema, five n8n pipeline workflows, video-worker evidence and Railway build/deployment/debug artifacts exist. Full autonomous multi-platform publishing is not established.

## Start here
- [Main README](README.md)
- [Version / revision archive](versions/TABLE_OF_CONTENTS.md)
- [Current pipeline visual](assets/current-pipeline.svg)
- [Architecture](docs/architecture.md)
- [Workflow inventory](docs/workflow-inventory.md)
- [Verification matrix](docs/verification.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [`n8n_workflows/`](n8n_workflows/) — current public W1–W5 package exports
- [`python_nodes/`](python_nodes/) — Python implementation
- [`database/`](database/) — PostgreSQL/pgvector schema

## Pipeline
| Stage | Responsibility | Evidence |
|---|---|---|
| W1 | fetch, normalize, semantic dedup, persist | implementation artifact |
| W2 | research / fact analysis | implementation artifact |
| W3 | daily/weekly script generation | implementation artifact |
| W4 | video generation | multiple genuine daily/weekly revisions |
| W5 | distribution | partial; sequential→parallel design evolution |

## Version / revision navigation
- [Current partial MVP](versions/current-partial-mvp/README.md) — [architecture](versions/current-partial-mvp/ARCHITECTURE.md)
- W4 Daily: [v1](versions/w4-daily/v1/README.md) · [v2](versions/w4-daily/v2/README.md) · [v3](versions/w4-daily/v3/README.md) · [v4](versions/w4-daily/v4/README.md)
- W4 Weekly: [v1](versions/w4-weekly/v1/README.md) · [v2](versions/w4-weekly/v2/README.md) · [v3](versions/w4-weekly/v3/README.md)
- [W5 distribution evolution](versions/w5-distribution/README.md) — [architecture](versions/w5-distribution/ARCHITECTURE.md)

Every historical revision has an architecture page. Historical revisions do not get fake demo/screenshot placeholders; only the current project state has current-media placeholders.