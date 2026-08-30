#!/usr/bin/env python3
"""
News IQ - Video Worker Service
Generates MP4 videos from scripts using gTTS + FFmpeg
Uploads to Railway S3-compatible bucket
"""

import os
import re
import uuid
import json
import asyncio
import subprocess
import tempfile
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
import boto3
from botocore.config import Config
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")
BUCKET_REGION = os.getenv("BUCKET_REGION", "us-west-1")
BUCKET_ENDPOINT = os.getenv("BUCKET_ENDPOINT")
BUCKET_ACCESS_KEY = os.getenv("BUCKET_ACCESS_KEY")
BUCKET_SECRET_KEY = os.getenv("BUCKET_SECRET_KEY")

# Video specs
DAILY_SHORT = {
    "width": 1080,
    "height": 1920,
    "format": "9:16",
    "font_size": 60,
    "max_title_width": 960,
    "line_height": 80,
}

WEEKLY = {
    "width": 1920,
    "height": 1080,
    "format": "16:9",
    "font_size": 48,
    "max_title_width": 1700,
    "line_height": 70,
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def insert_video(self, data: dict) -> str:
        query = """
        INSERT INTO videos (
            id, script_id, video_type, file_path_local,
            duration_seconds, format, file_size_bytes,
            quality_score, quality_status, generated_at
        ) VALUES (
            gen_random_uuid(), $1, $2, $3,
            $4, $5, $6,
            $7, $8, NOW()
        )
        RETURNING id
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchval(
                query,
                data["script_id"],
                data["video_type"],
                data["bucket_url"],
                data["duration_seconds"],
                data["format"],
                data["file_size_bytes"],
                data["quality_score"],
                data["quality_status"],
            )
            return row

db = Database(DATABASE_URL)

# ---------------------------------------------------------------------------
# S3 / Bucket Client
# ---------------------------------------------------------------------------

def get_s3_client():
    return boto3.client(
        "s3",
        region_name=BUCKET_REGION,
        endpoint_url=BUCKET_ENDPOINT,
        aws_access_key_id=BUCKET_ACCESS_KEY,
        aws_secret_access_key=BUCKET_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    script_id: str = Field(..., description="UUID of the script in PostgreSQL")
    title: str = Field(..., description="Headline / title to display")
    content: str = Field(..., description="Full script text with markers")
    video_type: str = Field(default="daily_short", pattern="^(daily_short|weekly)$")

class GenerateResponse(BaseModel):
    success: bool
    video_id: Optional[str] = None
    bucket_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    file_size_bytes: Optional[int] = None
    format: Optional[str] = None
    quality_score: Optional[float] = None
    message: str

# ---------------------------------------------------------------------------
# Script Processing
# ---------------------------------------------------------------------------

def clean_script_markers(text: str) -> str:
    """Remove markers for TTS, keep natural pauses."""
    text = text.replace("[PAUSE]", ". ")
    text = text.replace("[/EMPHASIS]", "")
    text = re.sub(r"\[EMPHASIS\]", "", text)
    text = re.sub(r"\[SOUND:[^\]]+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ---------------------------------------------------------------------------
# Audio Generation
# ---------------------------------------------------------------------------

def generate_audio(text: str, output_path: str) -> float:
    """Generate MP3 with gTTS. Returns duration in seconds."""
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(output_path)

    # Get exact duration via ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])

# ---------------------------------------------------------------------------
# Frame Generation (PIL)
# ---------------------------------------------------------------------------

def find_font(size: int):
    """Find a suitable system font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Wrap text into lines that fit within max_width."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def create_title_frame(title: str, spec: dict, output_path: str):
    """Create a single PNG frame with the title centered."""
    w, h = spec["width"], spec["height"]
    img = Image.new("RGB", (w, h), color=(15, 15, 35))
    draw = ImageDraw.Draw(img)
    font = find_font(spec["font_size"])

    lines = wrap_text(draw, title, font, spec["max_title_width"])
    line_h = spec["line_height"]
    total_h = len(lines) * line_h
    start_y = (h - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        y = start_y + i * line_h
        draw.text((x, y), line, fill=(255, 255, 255), font=font)

    img.save(output_path)

# ---------------------------------------------------------------------------
# Video Composition (FFmpeg)
# ---------------------------------------------------------------------------

def compose_video(frame_path: str, audio_path: str, output_path: str, duration: float, spec: dict):
    """Use FFmpeg to stitch frame + audio into MP4."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", frame_path,
        "-i", audio_path,
        "-c:v", "libx264", "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={spec['width']}:{spec['height']}",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

# ---------------------------------------------------------------------------
# Upload to Bucket
# ---------------------------------------------------------------------------

def upload_to_bucket(local_path: str, key: str) -> str:
    """Upload file to Railway S3 bucket. Returns public URL."""
    s3 = get_s3_client()
    s3.upload_file(local_path, BUCKET_NAME, key)

    # Build URL from endpoint + bucket + key
    # Railway buckets are typically: https://{bucket}.{endpoint}/{key}
    # or via the endpoint directly
    url = f"{BUCKET_ENDPOINT}/{BUCKET_NAME}/{key}"
    return url

# ---------------------------------------------------------------------------
# Quality Scoring
# ---------------------------------------------------------------------------

def calculate_quality_score(file_size_bytes: int, duration: float, spec: dict) -> float:
    """Simple 0-100 quality score."""
    score = 0.0
    file_mb = file_size_bytes / (1024 * 1024)

    # File size (encoding quality indicator)
    if file_mb > 1.0:
        score += 25
    elif file_mb > 0.5:
        score += 15

    # Duration sanity
    if duration > 5:
        score += 25

    # Resolution
    if spec["width"] >= 1080 and spec["height"] >= 1080:
        score += 25

    # Audio present (implicit since we build with audio)
    score += 25

    return min(score, 100.0)

# ---------------------------------------------------------------------------
# Core Generation Logic
# ---------------------------------------------------------------------------

async def generate_video(req: GenerateRequest) -> GenerateResponse:
    if not db.pool:
        await db.connect()

    spec = DAILY_SHORT if req.video_type == "daily_short" else WEEKLY
    tmp_dir = tempfile.mkdtemp(prefix="news_iq_")

    try:
        # 1. Clean text
        clean_text = clean_script_markers(req.content)
        if not clean_text:
            return GenerateResponse(success=False, message="Empty script after cleaning markers")

        # 2. Generate audio
        mp3_path = os.path.join(tmp_dir, "voiceover.mp3")
        duration = generate_audio(clean_text, mp3_path)

        # 3. Create title frame
        frame_path = os.path.join(tmp_dir, "frame.png")
        create_title_frame(req.title, spec, frame_path)

        # 4. Compose video
        mp4_path = os.path.join(tmp_dir, "video.mp4")
        compose_video(frame_path, mp3_path, mp4_path, duration, spec)

        # 5. Verify file
        if not os.path.exists(mp4_path):
            return GenerateResponse(success=False, message="FFmpeg failed to create video file")

        file_size = os.path.getsize(mp4_path)
        if file_size < 1024:
            return GenerateResponse(success=False, message="Video file is too small (likely corrupt)")

        # 6. Upload to bucket
        bucket_key = f"videos/{req.video_type}/{uuid.uuid4()}.mp4"
        bucket_url = upload_to_bucket(mp4_path, bucket_key)

        # 7. Calculate quality
        quality_score = calculate_quality_score(file_size, duration, spec)
        quality_status = "approved" if quality_score >= 70 else "pending_review"

        # 8. Save to database
        video_id = await db.insert_video({
            "script_id": req.script_id,
            "video_type": req.video_type,
            "bucket_url": bucket_url,
            "duration_seconds": int(duration),
            "format": spec["format"],
            "file_size_bytes": file_size,
            "quality_score": quality_score,
            "quality_status": quality_status,
        })

        return GenerateResponse(
            success=True,
            video_id=video_id,
            bucket_url=bucket_url,
            duration_seconds=int(duration),
            file_size_bytes=file_size,
            format=spec["format"],
            quality_score=quality_score,
            message=f"Video generated and uploaded. Quality: {quality_score:.0f}/100",
        )

    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
        return GenerateResponse(success=False, message=f"FFmpeg/gTTS error: {err}")

    except Exception as e:
        return GenerateResponse(success=False, message=f"Generation failed: {str(e)}")

    finally:
        # Cleanup temp files
        for f in ["voiceover.mp3", "frame.png", "video.mp4"]:
            p = os.path.join(tmp_dir, f)
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(tmp_dir)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.close()

app = FastAPI(
    title="News IQ Video Worker",
    description="Generates MP4 videos from news scripts",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate a video from a script.
    - Creates MP3 via gTTS (free)
    - Renders title frame via PIL
    - Encodes MP4 via FFmpeg
    - Uploads to Railway bucket
    - Stores metadata in PostgreSQL
    """
    result = await generate_video(req)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)
    return result

@app.get("/")
async def root():
    return {
        "service": "News IQ Video Worker",
        "endpoints": ["/health", "/generate"],
        "docs": "/docs",
    }

