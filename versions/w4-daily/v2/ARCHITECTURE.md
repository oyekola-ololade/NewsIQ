# NewsIQ W4 Daily v2 — Architecture

[← Revision Table of Contents](../../TABLE_OF_CONTENTS.md)

```mermaid
flowchart LR
  DB[(Daily script queue)] --> Lock[Daily lock/state guard]
  Lock --> Validate[Validate/select candidate]
  Validate --> Worker[Video worker request]
  Worker --> Result{result}
  Result -->|success| Persist[Persist media metadata]
  Result -->|failure| Failure[Record/release failure state]
```

**Revision status:** historical chronological revision; exact canonical promotion requires execution-aware comparison.