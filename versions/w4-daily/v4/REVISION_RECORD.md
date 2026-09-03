# NewsIQ W4 Daily v4 — Revision Record

**Status:** LATEST KNOWN DAILY ROBUST REVISION BY CHRONOLOGY  
**Normalized order:** 4 of 4  
**Canonical status:** CANDIDATE ONLY — not promoted without comparison and execution.

## Provenance

This is the latest file in the genuine Daily Robust revision line after normalization by actual Drive modification order.

## Why chronology is not enough

The archive explicitly forbids selecting a canonical workflow from filename or modification time alone. v4 must still be compared against v1–v3 and tested.

## Promotion gate

1. parse/import successfully in the target n8n generation;
2. inspect node/connection topology against earlier revisions;
3. confirm current video-worker endpoint and response contract;
4. validate lock acquisition/release and stale-lock behavior;
5. verify database state on success and failure;
6. confirm output contract consumed by W5;
7. run representative daily generation;
8. preserve execution evidence and limitations.

## Evidence boundary

Latest-known revision is not equivalent to current verified implementation. Until the gate passes, call this `latest chronological W4 Daily candidate`, not `canonical`. Historical revision line: no separate demo/screenshot placeholders here; current evidence belongs at the project-level current evidence folders.