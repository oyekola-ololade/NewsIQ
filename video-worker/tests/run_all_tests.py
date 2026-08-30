#!/usr/bin/env python3
"""
Run all stress test scenarios defined in config.json
Usage: python run_all_tests.py --url https://your-worker.railway.app
"""

import json
import subprocess
import sys
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    print("="*70)
    print("  NEWS IQ VIDEO WORKER - FULL TEST SUITE")
    print("="*70)
    print(f"  Target: {args.url}")
    print(f"  Scenarios: {len(config['test_scenarios'])}\n")

    all_passed = True
    reports = []

    for i, scenario in enumerate(config["test_scenarios"], 1):
        print(f"\n{'='*70}")
        print(f"  SCENARIO {i}/{len(config['test_scenarios'])}: {scenario['name']}")
        print(f"  {scenario['description']}")
        print(f"  Requests: {scenario['requests']} | Workers: {scenario['concurrent']}")
        print(f"{'='*70}")

        output_file = f"report_{scenario['name']}_{datetime.now().strftime('%H%M%S')}.json"

        cmd = [
            sys.executable, "stress_test.py",
            "--url", args.url,
            "--requests", str(scenario["requests"]),
            "--concurrent", str(scenario["concurrent"]),
            "--timeout", str(scenario["timeout"]),
            "--output", output_file,
        ]

        result = subprocess.run(cmd, capture_output=False)

        if result.returncode == 0:
            print(f"\n  [PASS] Scenario '{scenario['name']}' completed successfully")
        else:
            print(f"\n  [FAIL] Scenario '{scenario['name']}' had errors")
            all_passed = False

        reports.append(output_file)

    print("\n" + "="*70)
    print("  ALL SCENARIOS COMPLETE")
    print("="*70)
    print(f"\n  Reports generated:")
    for r in reports:
        print(f"    - {r}")

    if all_passed:
        print("\n  [ALL PASS] Worker is production-ready")
    else:
        print("\n  [SOME FAILED] Review reports before deploying")

if __name__ == "__main__":
    main()

