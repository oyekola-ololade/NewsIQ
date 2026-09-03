# NewsIQ W4 Daily — v4

[← Revision Table of Contents](../../TABLE_OF_CONTENTS.md) · [Architecture](ARCHITECTURE.md) · [Revision Record](REVISION_RECORD.md)

**Status:** LATEST KNOWN DAILY REVISION BY MODIFICATION ORDER · canonical status still pending

## Architecture
[Open the v4 architecture diagram →](ARCHITECTURE.md)

## Supported interpretation
v4 is the latest file in the genuine four-revision Daily Robust sequence after normalization by Drive modification chronology.

## Important distinction
“Latest” is **not** automatically “canonical.” Promotion requires alignment with the current video-worker contract, correct lock/concurrency behavior, current provider/config assumptions, useful error handling and a successful representative run.

## Promotion checklist
- import/topology valid;
- correct daily lock behavior;
- worker request contract valid;
- worker output persisted/forwarded correctly;
- failure path visible and recoverable;
- no stale credentials/provider assumptions;
- representative current execution succeeds.

## Media
Historical workflow revision within the current project archive. Architecture is documented; no standalone demo/screenshot placeholders are created here.