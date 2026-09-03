# NewsIQ W4 Daily v1 — Architecture

[← Revision Table of Contents](../../TABLE_OF_CONTENTS.md)

```mermaid
flowchart LR
  DB[(Ready daily script)] --> Lock[Acquire daily-processing lock]
  Lock --> Select[Select work item]
  Select --> Media[Video/TTS orchestration]
  Media --> Store[Persist video/output state]
  Store --> Release[Release/update lock]
```

**Revision status:** historical first daily W4 revision. This diagram captures the supported responsibility boundary; v1 is not automatically canonical.