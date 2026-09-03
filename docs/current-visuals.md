# NewsIQ Current Visual Sources

These diagrams describe the current repository evidence and intended later distribution behavior. They do not upgrade the project beyond **Partial MVP**.

## End-to-end pipeline

```mermaid
flowchart LR
    A[News sources / feeds] --> B[01 Scraper]
    B --> C[Normalize + semantic dedup]
    C --> D[(PostgreSQL + pgvector)]
    D --> E[02 Research / fact analysis]
    E --> D
    D --> F[03 Script generation]
    F --> D
    D --> G[04 Video orchestration]
    G --> H[Video worker / TTS / FFmpeg / storage]
    H --> D
    D --> I[05 Distribution]
    I --> J{Approval / publish gate}
    J -->|Not implemented / not approved| K[Stop safely]
    J -->|Future configured path| L[Platform adapters]
```

## Parallel distribution fault-isolation target

```mermaid
flowchart LR
    A[Ready media record] --> B[Parallel fan-out]
    B --> Y[YouTube branch]
    B --> T[TikTok branch]
    B --> I[Instagram branch]
    B --> O[Other / archive branch]

    Y --> M[Merge per-platform results]
    T --> M
    I --> M
    O --> M

    M --> P[(Persist each platform result)]
    P --> R[Retry failed branch / manual follow-up]
```

**Design objective:** one platform failure should not automatically block all other platform attempts. The public package still requires configured branch-level tests before this can be treated as verified runtime behavior.

## Failure map

```mermaid
flowchart TB
    Source[Source / provider failure] --> Log[Operational log]
    Research[Research-provider failure] --> Log
    AI[Model / structured-output failure] --> Log
    Video[Video-worker failure] --> Log
    Publish[Platform publish failure] --> Log

    Log --> State[(Persisted pipeline state)]
    State --> Retry[Bounded retry where safe]
    State --> Human[Human review / intervention]
```

## Version boundary

Workflow 4 has multiple daily and weekly revisions in the historical archive. The GitHub `04_video_generator.json` file is a public package representation, not proof that the newest archived revision has been selected as canonical. Canonical selection requires a controlled comparison plus configured verification.
