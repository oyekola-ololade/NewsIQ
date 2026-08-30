#!/usr/bin/env python3
"""
News IQ Video Worker - Stress Test Suite
Tests: concurrency, throughput, memory, error rates, bottlenecks

Usage:
    python stress_test.py --url https://your-worker.railway.app --requests 10 --concurrent 3
"""

import os
import sys
import time
import json
import random
import asyncio
import argparse
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


# ---------------------------------------------------------------------------
# Test Data
# ---------------------------------------------------------------------------

SAMPLE_SCRIPTS = [
    {
        "title": "Tech Giant Announces Revolutionary AI Chip",
        "content": "[EMPHASIS]Breaking news[/EMPHASIS] from the tech world! [PAUSE] A major company just announced a revolutionary AI chip that promises to double processing speed while using half the power. [PAUSE] Industry experts say this could change everything. [EMPHASIS]Subscribe for more tech updates![/EMPHASIS]",
        "video_type": "daily_short"
    },
    {
        "title": "Global Markets Rally on Economic Data",
        "content": "Markets are surging today after new economic data showed stronger than expected growth. [PAUSE] The S and P 500 hit a new record high. [SOUND:alert] Analysts say this trend could continue through the quarter. [PAUSE] Stay informed with daily market briefs.",
        "video_type": "daily_short"
    },
    {
        "title": "Space Mission Discovers Water on Mars Moon",
        "content": "In a stunning discovery, a space mission has found evidence of water on one of Mars moons. [PAUSE] This finding could be a game changer for future colonization efforts. [EMPHASIS]The search for life continues.[/EMPHASIS] [PAUSE] Follow for more space news.",
        "video_type": "daily_short"
    },
    {
        "title": "New Climate Agreement Reached at Summit",
        "content": "World leaders have reached a landmark climate agreement at the global summit. [PAUSE] The deal commits nations to reducing emissions by forty percent before twenty thirty. [SOUND:notification] Environmental groups are calling it a historic step. [PAUSE] Get the full story here.",
        "video_type": "daily_short"
    },
    {
        "title": "Weekly News Brief - August 13, 2026",
        "content": "[EMPHASIS]Welcome to your weekly news brief.[/EMPHASIS] [PAUSE] This week we cover major developments in technology, markets, space exploration, and climate policy. [PAUSE] First up, the tech industry saw its biggest announcement of the year. [PAUSE] Then, markets responded to surprising economic data. [PAUSE] In space news, water was discovered where scientists least expected it. [PAUSE] And finally, world leaders made history with a new climate deal. [EMPHASIS]That is all for this week.[/EMPHASIS] [PAUSE] Subscribe for daily updates and weekly recaps.",
        "video_type": "weekly"
    },
]


# ---------------------------------------------------------------------------
# Result Tracking
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    request_id: int
    script_title: str
    video_type: str
    status_code: int
    success: bool
    duration_ms: float
    video_id: Optional[str] = None
    bucket_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    quality_score: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass  
class StressReport:
    total_requests: int
    successful: int
    failed: int
    total_duration_sec: float
    avg_response_ms: float
    min_response_ms: float
    max_response_ms: float
    median_response_ms: float
    p95_response_ms: float
    p99_response_ms: float
    throughput_rps: float
    error_rate_pct: float
    daily_short_stats: dict
    weekly_stats: dict
    slowest_request: Optional[TestResult] = None
    fastest_request: Optional[TestResult] = None
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

class VideoWorkerStressTest:
    def __init__(self, base_url: str, timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.results: List[TestResult] = []
        self.health_url = f"{self.base_url}/health"
        self.generate_url = f"{self.base_url}/generate"

    def health_check(self) -> bool:
        """Verify worker is alive before stress test."""
        try:
            resp = requests.get(self.health_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"   Health OK - {data.get('status', 'unknown')}")
                return True
        except Exception as e:
            print(f"   Health check FAILED: {e}")
        return False

    def send_request(self, request_id: int) -> TestResult:
        """Send a single video generation request."""
        script = random.choice(SAMPLE_SCRIPTS)
        payload = {
            "script_id": f"stress-test-{request_id:04d}-{random.randint(1000,9999)}",
            "title": script["title"],
            "content": script["content"],
            "video_type": script["video_type"],
        }

        start = time.perf_counter()
        try:
            resp = requests.post(
                self.generate_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            data = resp.json() if resp.text else {}

            return TestResult(
                request_id=request_id,
                script_title=script["title"][:40],
                video_type=script["video_type"],
                status_code=resp.status_code,
                success=data.get("success", False) if resp.status_code == 200 else False,
                duration_ms=elapsed_ms,
                video_id=data.get("video_id"),
                bucket_url=data.get("bucket_url"),
                file_size_bytes=data.get("file_size_bytes"),
                quality_score=data.get("quality_score"),
                error_message=data.get("message") if not data.get("success") else None,
            )

        except requests.Timeout:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                request_id=request_id,
                script_title=script["title"][:40],
                video_type=script["video_type"],
                status_code=0,
                success=False,
                duration_ms=elapsed_ms,
                error_message=f"Request timeout after {self.timeout}s",
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                request_id=request_id,
                script_title=script["title"][:40],
                video_type=script["video_type"],
                status_code=0,
                success=False,
                duration_ms=elapsed_ms,
                error_message=str(e),
            )

    def run_sequential(self, count: int) -> List[TestResult]:
        """Run requests one at a time."""
        print(f"\n[SEQUENTIAL MODE] Sending {count} requests, one at a time...")
        results = []
        for i in range(count):
            print(f"   Request {i+1}/{count}...", end=" ", flush=True)
            result = self.send_request(i)
            results.append(result)
            status = "OK" if result.success else "FAIL"
            print(f"{status} ({result.duration_ms:.0f}ms)")
            if not result.success:
                print(f"      Error: {result.error_message}")
        return results

    def run_concurrent(self, count: int, max_workers: int) -> List[TestResult]:
        """Run requests with thread pool concurrency."""
        print(f"\n[CONCURRENT MODE] Sending {count} requests with {max_workers} workers...")
        results = []
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.send_request, i): i for i in range(count)}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                status = "OK" if result.success else "FAIL"
                print(f"   [{completed}/{count}] Request {result.request_id} -> {status} ({result.duration_ms:.0f}ms)")
                if not result.success:
                    print(f"      Error: {result.error_message}")

        # Sort by request_id for consistent reporting
        results.sort(key=lambda r: r.request_id)
        return results

    def build_report(self, results: List[TestResult]) -> StressReport:
        """Analyze results and build report."""
        durations = [r.duration_ms for r in results]
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        daily_shorts = [r for r in successful if r.video_type == "daily_short"]
        weeklies = [r for r in successful if r.video_type == "weekly"]

        total_time_sec = sum(durations) / 1000

        report = StressReport(
            total_requests=len(results),
            successful=len(successful),
            failed=len(failed),
            total_duration_sec=total_time_sec,
            avg_response_ms=statistics.mean(durations) if durations else 0,
            min_response_ms=min(durations) if durations else 0,
            max_response_ms=max(durations) if durations else 0,
            median_response_ms=statistics.median(durations) if durations else 0,
            p95_response_ms=statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations) if durations else 0,
            p99_response_ms=statistics.quantiles(durations, n=100)[98] if len(durations) >= 100 else max(durations) if durations else 0,
            throughput_rps=len(results) / total_time_sec if total_time_sec > 0 else 0,
            error_rate_pct=(len(failed) / len(results)) * 100 if results else 0,
            daily_short_stats={
                "count": len(daily_shorts),
                "avg_size_mb": statistics.mean([r.file_size_bytes / (1024*1024) for r in daily_shorts if r.file_size_bytes]) if daily_shorts else 0,
                "avg_duration_s": statistics.mean([r.duration_ms / 1000 for r in daily_shorts]) if daily_shorts else 0,
            },
            weekly_stats={
                "count": len(weeklies),
                "avg_size_mb": statistics.mean([r.file_size_bytes / (1024*1024) for r in weeklies if r.file_size_bytes]) if weeklies else 0,
                "avg_duration_s": statistics.mean([r.duration_ms / 1000 for r in weeklies]) if weeklies else 0,
            },
            slowest_request=max(results, key=lambda r: r.duration_ms) if results else None,
            fastest_request=min(results, key=lambda r: r.duration_ms) if results else None,
            errors=[f"Req {r.request_id}: {r.error_message}" for r in failed if r.error_message],
        )
        return report

    def print_report(self, report: StressReport):
        """Print formatted stress test report."""
        print("\n" + "="*70)
        print("  NEWS IQ VIDEO WORKER - STRESS TEST REPORT")
        print("="*70)

        print(f"\n  TOTAL REQUESTS:     {report.total_requests}")
        print(f"  SUCCESSFUL:         {report.successful} ({100-report.error_rate_pct:.1f}%)")
        print(f"  FAILED:             {report.failed} ({report.error_rate_pct:.1f}%)")
        print(f"  TOTAL TIME:         {report.total_duration_sec:.1f}s")
        print(f"  THROUGHPUT:         {report.throughput_rps:.2f} req/sec")

        print(f"\n  RESPONSE TIMES:")
        print(f"    Fastest:          {report.fastest_request.duration_ms:.0f}ms")
        print(f"    Slowest:          {report.slowest_request.duration_ms:.0f}ms")
        print(f"    Average:          {report.avg_response_ms:.0f}ms")
        print(f"    Median:           {report.median_response_ms:.0f}ms")
        print(f"    P95:              {report.p95_response_ms:.0f}ms")
        print(f"    P99:              {report.p99_response_ms:.0f}ms")

        print(f"\n  DAILY SHORT VIDEOS:")
        print(f"    Generated:        {report.daily_short_stats['count']}")
        print(f"    Avg Size:         {report.daily_short_stats['avg_size_mb']:.2f} MB")
        print(f"    Avg Gen Time:     {report.daily_short_stats['avg_duration_s']:.1f}s")

        print(f"\n  WEEKLY VIDEOS:")
        print(f"    Generated:        {report.weekly_stats['count']}")
        print(f"    Avg Size:         {report.weekly_stats['avg_size_mb']:.2f} MB")
        print(f"    Avg Gen Time:     {report.weekly_stats['avg_duration_s']:.1f}s")

        if report.errors:
            print(f"\n  ERRORS ({len(report.errors)}):")
            for err in report.errors[:10]:
                print(f"    - {err}")
            if len(report.errors) > 10:
                print(f"    ... and {len(report.errors) - 10} more")

        print("\n" + "="*70)
        self._print_recommendations(report)
        print("="*70)

    def _print_recommendations(self, report: StressReport):
        """Print actionable recommendations based on results."""
        print("\n  RECOMMENDATIONS:")

        if report.error_rate_pct > 10:
            print("    [CRITICAL] Error rate is above 10%. Do NOT deploy to production.")
            print("               Check worker logs for memory limits or timeout issues.")
        elif report.error_rate_pct > 0:
            print(f"    [WARNING] {report.error_rate_pct:.1f}% failure rate. Review errors above.")

        if report.avg_response_ms > 120000:
            print("    [CRITICAL] Average response > 2 minutes. n8n HTTP node will timeout.")
            print("               Increase n8n timeout OR add async queue pattern.")
        elif report.avg_response_ms > 60000:
            print("    [WARNING] Average response > 1 minute. Set n8n timeout to 120s minimum.")

        if report.throughput_rps < 0.01:
            print("    [INFO] Throughput is very low. This is expected - video encoding is CPU-heavy.")
            print("           For production: run 1 video at a time, not concurrent.")

        if report.p95_response_ms > report.avg_response_ms * 2:
            print("    [WARNING] High variance in response times. Likely resource contention.")
            print("               Consider: dedicated CPU tier OR sequential processing only.")

        if report.daily_short_stats['avg_size_mb'] < 0.5:
            print("    [WARNING] Daily short videos are very small (< 0.5MB).")
            print("               Check FFmpeg bitrate settings for quality.")

        if report.successful > 0 and report.error_rate_pct == 0:
            print("    [PASS] All requests succeeded. Worker is ready for production.")
            print("    [INFO] Set n8n Workflow 4 to sequential mode (1 video at a time).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Stress test News IQ Video Worker")
    parser.add_argument("--url", required=True, help="Worker base URL (e.g. https://worker.railway.app)")
    parser.add_argument("--requests", type=int, default=5, help="Total requests to send (default: 5)")
    parser.add_argument("--concurrent", type=int, default=1, help="Max concurrent workers (default: 1 = sequential)")
    parser.add_argument("--timeout", type=int, default=180, help="Request timeout in seconds (default: 180)")
    parser.add_argument("--output", type=str, default=None, help="Save JSON report to file")
    args = parser.parse_args()

    print("="*70)
    print("  NEWS IQ VIDEO WORKER - STRESS TEST")
    print("="*70)
    print(f"\n  Target URL:     {args.url}")
    print(f"  Total Requests: {args.requests}")
    print(f"  Concurrency:    {args.concurrent}")
    print(f"  Timeout:        {args.timeout}s")

    tester = VideoWorkerStressTest(args.url, timeout=args.timeout)

    print("\n[1/3] Health check...")
    if not tester.health_check():
        print("\nWorker is not responding. Aborting.")
        sys.exit(1)

    print("\n[2/3] Running stress test...")
    if args.concurrent <= 1:
        results = tester.run_sequential(args.requests)
    else:
        results = tester.run_concurrent(args.requests, args.concurrent)

    print("\n[3/3] Building report...")
    report = tester.build_report(results)
    tester.print_report(report)

    if args.output:
        # Convert dataclass to dict for JSON
        report_dict = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_url": args.url,
            "total_requests": report.total_requests,
            "successful": report.successful,
            "failed": report.failed,
            "error_rate_pct": report.error_rate_pct,
            "total_duration_sec": report.total_duration_sec,
            "throughput_rps": report.throughput_rps,
            "response_times_ms": {
                "min": report.min_response_ms,
                "max": report.max_response_ms,
                "avg": report.avg_response_ms,
                "median": report.median_response_ms,
                "p95": report.p95_response_ms,
                "p99": report.p99_response_ms,
            },
            "daily_short_stats": report.daily_short_stats,
            "weekly_stats": report.weekly_stats,
            "errors": report.errors,
        }
        with open(args.output, "w") as f:
            json.dump(report_dict, f, indent=2)
        print(f"\n  Report saved to: {args.output}")

    # Exit code based on success
    sys.exit(0 if report.error_rate_pct == 0 else 1)


if __name__ == "__main__":
    main()

