# NewsIQ — Version / Revision Archive

This archive follows the version history that the evidence actually supports.

## Project-level state

- [Current partial MVP](current-partial-mvp/README.md)

## W4 — Daily video-generation lineage

Chronology normalized by actual Drive modification order:

- [Daily v1](w4-daily/v1/README.md)
- [Daily v2](w4-daily/v2/README.md)
- [Daily v3](w4-daily/v3/README.md)
- [Daily v4](w4-daily/v4/README.md)

The four files are genuine revisions. The canonical daily revision is **not** selected solely by the highest number; runtime/topology/provider/failure-path verification is still required.

## W4 — Weekly video-generation lineage

- [Weekly v1](w4-weekly/v1/README.md)
- [Weekly v2](w4-weekly/v2/README.md)
- [Weekly v3](w4-weekly/v3/README.md)

Again, chronology is real; canonical status still requires execution-aware comparison.

## W5 — Distribution evolution

- [Distribution evolution](w5-distribution/README.md)

The important supported architecture change is from sequential posting toward **parallel independent platform branches with merged results**, so one platform failure should not block later branches.

## Canonical-selection rule

Promote a workflow revision only after comparing:

1. modification chronology;
2. topology/node changes;
3. provider/config references;
4. failure behavior;
5. alignment with later design decisions;
6. successful representative execution evidence.

A filename that looks newest is not enough.