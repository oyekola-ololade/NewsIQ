#!/usr/bin/env python3
"""
Quick single-request test for the Video Worker.
Usage: python quick_test.py --url https://your-worker.railway.app [--db-url postgresql://user:password@localhost:5432/news_iq
"""

import argparse
import requests
import json
import uuid
import asyncio
from datetime import datetime

async def create_test_script_in_db(db_url: str) -> str:
    """Create a test headline and script in the database."""
    if not db_url:
        print("[WARNING] No --db-url provided. Skipping database setup.")
        print("[INFO] Make sure a script with the generated UUID exists in the scripts table.")
        return str(uuid.uuid4())
    
    try:
        import asyncpg
        import ssl
        
        # Setup SSL for Railway PostgreSQL
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        # Connect
        conn = await asyncpg.connect(db_url, ssl=ssl_ctx, command_timeout=30)
        
        headline_id = str(uuid.uuid4())
        script_id = str(uuid.uuid4())
        
        # 1. Create headline
        headline_query = """
        INSERT INTO headlines (
            id, original_title, normalized_title, category, url, published_at, status
        ) VALUES ($1, $2, $3, $4, $5, NOW(), 'scripted')
        ON CONFLICT (url) DO UPDATE SET id = EXCLUDED.id
        RETURNING id
        """
        
        title_text = "Breaking: Major Tech Announcement Today"
        await conn.fetchval(
            headline_query,
            headline_id,
            title_text,
            title_text.lower(),
            "technology",
            f"https://test-news.local/article/{headline_id}"
        )
        print(f"[OK] Created headline: {headline_id}")
        
        # 2. Create script
        script_query = """
        INSERT INTO scripts (
            id, headline_id, script_type, content, word_count
        ) VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO NOTHING
        RETURNING id
        """
        
        content = "[EMPHASIS]Breaking news[/EMPHASIS] from Silicon Valley! A leading technology company has just unveiled its most ambitious project yet."
        result = await conn.fetchval(
            script_query,
            script_id,
            headline_id,
            "daily_short",
            content,
            len(content.split())
        )
        
        await conn.close()
        
        if result:
            print(f"[OK] Created script: {script_id}")
        else:
            print(f"[OK] Script already exists: {script_id}")
        
        return script_id
    
    except ImportError:
        print("[ERROR] asyncpg not installed. Install with: pip install asyncpg")
        return str(uuid.uuid4())
    except Exception as e:
        print(f"[ERROR] Failed to create test data in DB: {e}")
        return str(uuid.uuid4())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Worker base URL")
    parser.add_argument("--type", default="daily_short", choices=["daily_short", "weekly"])
    parser.add_argument("--db-url", help="PostgreSQL connection URL (optional, for creating test script)")
    args = parser.parse_args()

    # Create test script in DB if URL provided
    script_id = asyncio.run(create_test_script_in_db(args.db_url))

    payload = {
        "script_id": script_id,
        "title": "Breaking: Major Tech Announcement Today",
        "content": "[EMPHASIS]Breaking news[/EMPHASIS] from Silicon Valley! [PAUSE] A leading technology company has just unveiled its most ambitious project yet. [PAUSE] The new platform promises to reshape how we interact with artificial intelligence. [SOUND:alert] Industry analysts are already calling it a game changer. [PAUSE] Stay ahead of the curve. [EMPHASIS]Subscribe now for daily tech briefs.[/EMPHASIS]",
        "video_type": args.type,
    }

    print(f"\nSending {args.type} generation request to {args.url}/generate...")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")

    start = datetime.now()
    resp = requests.post(f"{args.url}/generate", json=payload, timeout=300)
    elapsed = (datetime.now() - start).total_seconds()

    print(f"Status: {resp.status_code}")
    print(f"Time: {elapsed:.1f}s\n")

    try:
        data = resp.json()
        print("Response:")
        print(json.dumps(data, indent=2))

        if data.get("success"):
            print(f"\n[PASS] Video generated successfully!")
            print(f"  Video ID: {data.get('video_id')}")
            print(f"  Bucket URL: {data.get('bucket_url')}")
            print(f"  Duration: {data.get('duration_seconds')}s")
            print(f"  Size: {data.get('file_size_bytes', 0) / (1024*1024):.2f} MB")
            print(f"  Quality: {data.get('quality_score')}/100")
        else:
            print(f"\n[FAIL] Generation failed: {data.get('message')}")
    except Exception as e:
        print(f"Response body: {resp.text}")
        print(f"Parse error: {e}")

if __name__ == "__main__":
    main()
