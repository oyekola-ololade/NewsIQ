# NewsIQ — Repository Index

> **Current truth:** partial MVP / implementation project. Python services, PostgreSQL schema, five n8n pipeline workflows, video-worker evidence and Railway build/deployment/debug artifacts exist. Full autonomous multi-platform publishing is not established.

## Start here

- [Main README](README.md)
- [Version / revision archive](versions/INDEX.md)
- [Current pipeline visuals](docs/current-visuals.md)
- [Verification matrix](docs/verification.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)
- `n8n_workflows/` — current public workflow exports
- `python_nodes/` — Python implementation components
- `database/` — schema/data-layer artifacts
- `config/` — configuration artifacts

## Pipeline index

| Stage | Responsibility | Current evidence |
|---|---|---|
| W1 | fetch, normalize, deduplicate, persist headlines | implementation artifact |
| W2 | research / enrichment / fact analysis | implementation + mixed provider history |
| W3 | daily/weekly script generation | implementation artifact |
| W4 | video generation | multiple genuine daily + weekly revisions |
| W5 | distribution | partial; multiple variants / architectural evolution |

## Version / revision model

NewsIQ does **not** have one clean project-wide semantic version line. The evidence supports:

- a current partial-MVP project state;
- a genuine **W4 Daily v1 → v4** revision line;
- a genuine **W4 Weekly v1 → v3** revision line;
- W5 evolution from sequential distribution toward parallel independent branches.

Those are documented individually under [`versions/`](versions/INDEX.md).

## Media rule

Only the current project state gets missing-media placeholders:

- [Current demo placeholder](evidence/current/demo/README.md)
- [Current screenshot/public-evidence placeholder](evidence/current/screenshots/README.md)

Historical W4 revisions do not get fake screenshot/demo folders.