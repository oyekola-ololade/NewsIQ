# NewsIQ — Current Partial-MVP Architecture

[← Version Table of Contents](../TABLE_OF_CONTENTS.md)

```mermaid
flowchart LR
  Sources[News sources] --> W1[W1 Scraper + normalize]
  W1 --> Dedup[Embeddings + semantic dedup]
  Dedup --> DB[(PostgreSQL + pgvector)]
  DB --> W2[W2 Research / fact analysis]
  W2 --> DB
  DB --> W3[W3 Script writer]
  W3 --> DB
  DB --> W4[W4 Video generation]
  W4 --> Worker[Python/video worker + TTS/FFmpeg/storage]
  Worker --> DB
  DB --> W5[W5 Distribution]
  W5 --> Gate{approval / adapter gate}
  Gate -->|unconfigured| Stop[Stop safely]
  Gate -->|future configured| Platforms[External platforms]
```

**Status:** explanatory architecture for the current partial MVP, not proof of a live end-to-end publishing system.