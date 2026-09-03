# NewsIQ Verification & Release Gate

## Current classification

**Partial MVP — not a live production system.**

The repository contains real Python, SQL, n8n, Docker/Railway, and video-worker implementation evidence. It does not contain proof of a complete configured end-to-end live run or real multi-platform publishing.

## What is already checked

- Five n8n exports are present and JSON-parseable.
- Python source exists for API/utilities and the video worker.
- PostgreSQL/pgvector schema exists.
- Public configuration uses placeholders rather than live credentials.
- Social-publishing stubs do not fabricate successful external post IDs.
- Automatic approval is not silently enabled.

## What still requires configured verification

1. Source ingestion against configured providers.
2. Database connectivity and semantic-dedup behavior.
3. Research-provider failure and retry behavior.
4. Structured script-generation validation.
5. Daily and weekly Workflow-4 canonical-revision selection.
6. Video-worker processing, locking, storage, and retry behavior.
7. Approval-state behavior.
8. Distribution branch independence.
9. Per-platform success/failure persistence.
10. End-to-end state continuity from ingestion through final distribution records.

## Minimum end-to-end matrix

| Case | Expected result |
|---|---|
| New unique article | persisted once and advances to research |
| Semantic duplicate | blocked/merged according to threshold policy |
| Research-provider failure | logged and safely retryable |
| Invalid AI output | rejected/normalized without corrupt state |
| Daily script | stored with valid structured fields |
| Weekly script | stored only through the intended weekly path |
| Video-worker success | media state advances with stored artifact reference |
| Video-worker failure | lock/retry state remains recoverable |
| Approval absent | distribution does not execute |
| One platform fails | other independent branches can still complete |

## Security note

Historical debugging material outside this public package previously contained provider credentials. Public repository files must never reintroduce those values. Any exposed historical key should be treated as compromised and rotated if it could still be active.

## Claim boundary

Acceptable: **partial working AI news-intelligence MVP**, **five-stage public workflow package**, **Python + PostgreSQL + n8n implementation evidence**, **video-worker implementation**.

Not currently supported: **production-ready**, **live autonomous publishing**, **complete ten-stage live system**, **production traffic**, **paying customers**, **SLA**, or **verified distribution across real social accounts**.
