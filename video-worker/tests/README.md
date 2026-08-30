# Video Worker - Test Suite

## Files

| File | Purpose |
|------|---------|
| `quick_test.py` | Single request smoke test. Use this first. |
| `stress_test.py` | Full stress test with metrics and recommendations. |
| `run_all_tests.py` | Runs all scenarios from `config.json` automatically. |
| `config.json` | Defines test scenarios (requests, concurrency, timeout). |

## Quick Start

### 1. Smoke Test (1 request)

```bash
python quick_test.py --url https://your-worker.railway.app
```

This sends one `daily_short` request and prints the result. Use this to verify the worker is alive and functional.

### 2. Baseline Performance (5 sequential requests)

```bash
python stress_test.py --url https://your-worker.railway.app --requests 5 --concurrent 1
```

This measures how long one video takes when the worker is not under load. This is your "happy path" baseline.

### 3. Light Concurrency (5 requests, 2 workers)

```bash
python stress_test.py --url https://your-worker.railway.app --requests 5 --concurrent 2 --timeout 300
```

Tests if the worker can handle 2 videos at once. On Railway shared CPU, this may already cause slowdowns.

### 4. Heavy Concurrency (10 requests, 5 workers)

```bash
python stress_test.py --url https://your-worker.railway.app --requests 10 --concurrent 5 --timeout 600
```

This will likely fail or time out. Video encoding is CPU-bound. The purpose is to find the breaking point.

### 5. Full Suite (all scenarios)

```bash
python run_all_tests.py --url https://your-worker.railway.app
```

Runs every scenario in `config.json` and generates JSON reports for each.

## Understanding the Output

The stress test prints a report like this:

```
TOTAL REQUESTS:     5
SUCCESSFUL:         5 (100.0%)
FAILED:             0 (0.0%)
TOTAL TIME:         245.3s
THROUGHPUT:         0.02 req/sec

RESPONSE TIMES:
  Fastest:          42000ms
  Slowest:          58000ms
  Average:          49000ms
  Median:           48000ms
  P95:              57000ms

DAILY SHORT VIDEOS:
  Generated:        5
  Avg Size:         1.2 MB
  Avg Gen Time:     49.0s
```

### Key Metrics

| Metric | Good | Bad | Action |
|--------|------|-----|--------|
| Error rate | 0% | >10% | Do not deploy. Check worker logs. |
| Avg response | 30-60s | >120s | Increase n8n timeout or use async queue. |
| Throughput | 0.01-0.02 rps | 0.00 rps | Worker is frozen or crashed. |
| Video size | 0.5-2 MB | <0.3 MB | Check FFmpeg quality settings. |

## What to Expect

Video generation is **CPU-bound and single-threaded per request**:
- gTTS: ~2-5s (network call to Google)
- PIL frame: ~0.5s (fast)
- FFmpeg encode: ~25-50s (CPU-heavy, depends on script length)
- S3 upload: ~2-5s (network)

**Total per video: ~30-60 seconds**

**Concurrent requests will fight for CPU** and each will take longer. On Railway shared CPU (0.5 vCPU), running 2 videos at once might make each take 90s instead of 45s.

## Production Recommendation

Based on stress test results, configure n8n Workflow 4 as:

```
Mode: SEQUENTIAL (not parallel)
Timeout: 120s (or match your P95 + 20% buffer)
Retry: 2 attempts with 30s delay
Max per batch: 1 video at a time
```

If you need to generate 5 daily shorts, run them one by one in a loop, not all at once.

## Interpreting Failures

**Timeout errors:**
- Worker is overloaded (too many concurrent requests)
- Solution: Reduce concurrency, increase timeout, or upgrade Railway CPU tier

**500 errors / "FFmpeg error":**
- Worker ran out of memory during encoding
- Solution: Add swap space or upgrade Railway memory tier

**Database connection errors:**
- Connection pool exhausted
- Solution: Increase `max_size` in `asyncpg.create_pool()` or reduce concurrent DB operations

**S3 upload errors:**
- Wrong bucket credentials or permissions
- Solution: Verify `BUCKET_*` env vars in Railway dashboard

