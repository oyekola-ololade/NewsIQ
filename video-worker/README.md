# NewsIQ Video Worker

> Component status: implementation present; current public deployment is not claimed.

This FastAPI worker generates video assets from stored scripts using gTTS, Pillow, and FFmpeg, then writes metadata to PostgreSQL and can upload output to an S3-compatible bucket.

## Required configuration

- `DATABASE_URL`
- `BUCKET_NAME`
- `BUCKET_REGION`
- `BUCKET_ENDPOINT`
- `BUCKET_ACCESS_KEY`
- `BUCKET_SECRET_KEY`

Use placeholders from `../config/.env.example`. Do not commit real values.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Tests

The `tests/` directory contains smoke, sequential, concurrency, and stress-test scripts. Their presence is implementation evidence; no pass result is claimed until they are executed against a configured environment and the results are retained.

