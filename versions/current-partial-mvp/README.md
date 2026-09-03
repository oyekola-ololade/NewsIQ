# NewsIQ — Current Partial-MVP State

[← Version / Revision Table of Contents](../TABLE_OF_CONTENTS.md) · [Architecture](ARCHITECTURE.md)

**Status:** CURRENT PROJECT STATE · PARTIAL MVP · not live production

## Implemented/evidenced components

- Python service/source artifacts;
- PostgreSQL schema and pgvector-oriented design/implementation evidence;
- five n8n pipeline workflow stages;
- separate video-worker service and related tests/debug artifacts;
- Railway build/deployment/debug evidence;
- multiple genuine W4 video-generation revisions;
- multiple/partial W5 distribution variants.

## Architecture

[Open the current partial-MVP architecture →](ARCHITECTURE.md)

## Current pipeline

`W1 Scraper → W2 Research → W3 Script → W4 Video → W5 Distribution`

### W1
Fetch, normalize, deduplicate and persist headlines. Needs a fresh representative source/database rerun before stronger runtime claims.

### W2
Research/enrichment/fact-analysis. Provider history is mixed; current search provider/fallback must be confirmed from current code/config before being labelled authoritative.

### W3
Daily/weekly script generation. Implementation artifact exists; representative current runs remain desirable evidence.

### W4
Real daily/weekly revision histories exist. Canonical daily and weekly revisions still require execution-aware selection.

### W5
Distribution is partial. The mature architecture direction is independent parallel platform branches; branch-level current execution must be verified before full publishing claims.

## Current limitations

- full autonomous multi-platform publishing is not established;
- current canonical W4 daily/weekly selection is not final;
- current provider configuration must be verified;
- a full current E2E run from ingestion through distribution is still required.

## Media

Only this current project state gets placeholders:

- [`../../evidence/current/demo/README.md`](../../evidence/current/demo/README.md)
- [`../../evidence/current/screenshots/README.md`](../../evidence/current/screenshots/README.md)

Old W4 revisions do not receive empty demo/screenshot folders.