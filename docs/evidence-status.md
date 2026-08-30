# Evidence and Status Register

## Classification

**PARTIAL MVP**

## Verified from repository files

- Five valid n8n JSON exports are present.
- The exports contain 92 nodes combined.
- Python FastAPI and utility code is present.
- A PostgreSQL schema with pgvector is present.
- Docker/Railway configuration is present.
- A separate video worker and test scripts are present.

## Not verified by this package

- A currently live deployment
- A configured end-to-end run across every external service
- Real social-platform publishing
- Production traffic, reliability, security, or scale
- Paying customers or measurable business outcomes
- Completion of the broader ten-stage product vision

## Stub and safety status

The original Python service contained YouTube, TikTok, and Instagram stub endpoints that returned synthetic success identifiers. The public package replaces those responses with HTTP 501 errors.

The original weekly approval node returned `approved: true` without a real approval integration. The public export now defaults to `approved: false`.

These changes preserve the implementation evidence while preventing the repository from presenting simulated success as real execution.

