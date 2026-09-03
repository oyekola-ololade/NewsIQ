# NewsIQ W4 Weekly v3 — Architecture

[← Revision Table of Contents](../../TABLE_OF_CONTENTS.md)

```mermaid
flowchart LR
  Queue[(Weekly eligible scripts)] --> Guard[Lock + eligibility guard]
  Guard --> Worker[Media processing]
  Worker --> Validate[Validate output state]
  Validate --> Persist[(Persist weekly media)]
  Validate --> Failure[Failure / cleanup boundary]
```

Latest chronological weekly revision in the recovered sequence; **latest does not equal canonical**.