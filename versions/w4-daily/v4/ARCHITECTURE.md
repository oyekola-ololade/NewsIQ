# NewsIQ W4 Daily v4 — Architecture

[← Revision Table of Contents](../../TABLE_OF_CONTENTS.md)

```mermaid
flowchart LR
  Queue[(Daily scripts)] --> Lock[Acquire/check lock]
  Lock --> Build[Build current media request]
  Build --> Worker[Video worker / processing]
  Worker --> Result{validated result?}
  Result -->|yes| Persist[(Persist media + status)]
  Result -->|no| Fail[Failure/retry + lock cleanup]
```

**Revision status:** latest chronological daily revision in the recovered sequence, **not automatically canonical**.