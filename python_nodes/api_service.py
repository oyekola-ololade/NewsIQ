"""
News IQ - FastAPI Service
Powers embedding generation, video composition, and platform posting
Called by n8n via HTTP Request nodes
"""

import os
import json
import base64
import tempfile
import subprocess
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import numpy as np
from sentence_transformers import SentenceTransformer

load_dotenv()

app = FastAPI(title="News IQ Service", version="1.0.0")

# Global model (loaded once at startup)
embedding_model = None

def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return embedding_model

# ============================================================================
# EMBEDDING ENDPOINTS
# ============================================================================

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    count: int
    model: str

@app.post("/embed-batch", response_model=EmbedResponse)
async def embed_batch(request: EmbedRequest):
    """Generate embeddings for a batch of texts."""
    try:
        model = get_embedding_model()
        embeddings = model.encode(request.texts, convert_to_numpy=True)
        embeddings_list = embeddings.tolist()

        return EmbedResponse(
            embeddings=embeddings_list,
            count=len(embeddings_list),
            model="all-MiniLM-L6-v2"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed")
async def embed_single(text: str):
    """Generate embedding for a single text."""
    try:
        model = get_embedding_model()
        embedding = model.encode([text], convert_to_numpy=True)[0]
        return {"embedding": embedding.tolist(), "model": "all-MiniLM-L6-v2"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# VIDEO COMPOSITION ENDPOINTS
# ============================================================================

class VideoComposeRequest(BaseModel):
    audio_base64: str
    script_type: str = "daily_short"  # daily_short or weekly
    title: str = "News Short"
    expected_duration: int = 60

class VideoComposeResponse(BaseModel):
    video_path: str
    file_size_bytes: int
    duration_seconds: int
    format: str
    video_codec: str
    audio_codec: str
    success: bool

@app.post("/compose-video", response_model=VideoComposeResponse)
async def compose_video(request: VideoComposeRequest):
    """
    Compose a video from audio + background image using FFmpeg.
    Returns video metadata. Video file is saved to temp directory.
    """
    temp_dir = tempfile.mkdtemp(prefix="news_iq_video_")

    try:
        # Decode audio
        audio_path = os.path.join(temp_dir, "voiceover.mp3")
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(request.audio_base64))

        # Determine format
        is_daily = request.script_type == "daily_short"
        resolution = "1080x1920" if is_daily else "1920x1080"  # 9:16 vs 16:9
        format_str = "9:16" if is_daily else "16:9"

        # Create background image (solid color with text overlay capability)
        bg_path = os.path.join(temp_dir, "background.png")
        bg_color = "0x1a1a2e" if is_daily else "0x0f0f23"

        # Generate background using FFmpeg
        bg_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={bg_color}:s={resolution}:d=1",
            "-frames:v", "1",
            bg_path
        ]
        subprocess.run(bg_cmd, check=True, capture_output=True)

        # Compose final video
        video_path = os.path.join(temp_dir, "output.mp4")

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", bg_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-s", resolution,
            "-movflags", "+faststart",
            video_path
        ]

        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        # Get video metadata
        file_size = os.path.getsize(video_path)

        # Get duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.stdout.strip() else 0

        return VideoComposeResponse(
            video_path=video_path,
            file_size_bytes=file_size,
            duration_seconds=int(duration),
            format=format_str,
            video_codec="h264",
            audio_codec="aac",
            success=True
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# GOOGLE DRIVE ENDPOINTS
# ============================================================================

class DriveUploadRequest(BaseModel):
    video_path: str
    filename: str
    folder_id: Optional[str] = None

class DriveUploadResponse(BaseModel):
    file_id: str
    drive_link: str
    success: bool

@app.post("/upload-drive", response_model=DriveUploadResponse)
async def upload_to_drive(request: DriveUploadRequest):
    """Upload video to Google Drive. Requires service account credentials."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "credentials.json")
        folder_id = request.folder_id or os.getenv("GOOGLE_FOLDER_ID")

        credentials = Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=credentials)

        file_metadata = {
            "name": request.filename,
            "mimeType": "video/mp4",
            "parents": [folder_id] if folder_id else []
        }

        media = MediaFileUpload(request.video_path, mimetype="video/mp4", resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        return DriveUploadResponse(
            file_id=file.get("id"),
            drive_link=file.get("webViewLink"),
            success=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DriveDownloadRequest(BaseModel):
    file_id: str

class DriveDownloadResponse(BaseModel):
    local_path: str
    success: bool

@app.post("/download-drive", response_model=DriveDownloadResponse)
async def download_from_drive(request: DriveDownloadRequest):
    """Download video from Google Drive to local temp."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "credentials.json")

        credentials = Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=credentials)

        temp_dir = tempfile.mkdtemp(prefix="news_iq_download_")
        local_path = os.path.join(temp_dir, "video.mp4")

        request_drive = service.files().get_media(fileId=request.file_id)

        with open(local_path, "wb") as f:
            downloader = request_drive
            f.write(downloader.execute())

        return DriveDownloadResponse(
            local_path=local_path,
            success=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PLATFORM POSTING ENDPOINTS (Stub implementations)
# ============================================================================

class YouTubePostRequest(BaseModel):
    video_path: str
    title: str
    description: str
    category_id: str = "25"
    privacy: str = "public"
    video_type: str = "shorts"  # shorts or long

class YouTubePostResponse(BaseModel):
    success: bool
    video_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

@app.post("/post-youtube", response_model=YouTubePostResponse)
async def post_youtube(request: YouTubePostRequest):
    """Publishing is intentionally disabled in this public partial-MVP build."""
    raise HTTPException(
        status_code=501,
        detail="Youtube publishing is not implemented or verified in this repository."
    )

class TikTokPostRequest(BaseModel):
    video_path: str
    caption: str
    privacy_level: str = "0"

class TikTokPostResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

@app.post("/post-tiktok", response_model=TikTokPostResponse)
async def post_tiktok(request: TikTokPostRequest):
    """Publishing is intentionally disabled in this public partial-MVP build."""
    raise HTTPException(
        status_code=501,
        detail="Tiktok publishing is not implemented or verified in this repository."
    )

class InstagramPostRequest(BaseModel):
    video_path: str
    caption: str
    media_type: str = "REELS"

class InstagramPostResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

@app.post("/post-instagram", response_model=InstagramPostResponse)
async def post_instagram(request: InstagramPostRequest):
    """Publishing is intentionally disabled in this public partial-MVP build."""
    raise HTTPException(
        status_code=501,
        detail="Instagram publishing is not implemented or verified in this repository."
    )

# ============================================================================
# SHORTFORM EXTRACTION ENDPOINTS
# ============================================================================

class ExtractShortformRequest(BaseModel):
    video_path: str
    min_segments: int = 3
    max_segments: int = 4
    target_duration_s: float = 45.0

class ExtractedSegmentResponse(BaseModel):
    segment_path: str
    segment_index: int
    start_s: float
    end_s: float
    duration_s: float
    format: str
    file_size_bytes: int

class ExtractShortformResponse(BaseModel):
    success: bool
    segments: List[ExtractedSegmentResponse]
    source_duration_s: float
    source_resolution: str
    error: Optional[str] = None

@app.post("/extract-shortform", response_model=ExtractShortformResponse)
async def extract_shortform(request: ExtractShortformRequest):
    """
    Extract 3-4 shortform segments from a weekly 16:9 video.
    Converts each segment to 9:16 vertical format.
    """
    try:
        from shortform_extractor import WeeklyShortformExtractor

        extractor = WeeklyShortformExtractor(
            target_duration_s=request.target_duration_s,
            min_segments=request.min_segments,
            max_segments=request.max_segments
        )

        segments = await extractor.extract_segments(request.video_path)

        # Get source metadata for response
        from shortform_extractor import VideoMetadata
        # Re-analyze for metadata (extractor already did this, but we need it for response)
        # For simplicity, we'll use ffprobe directly here
        import subprocess
        import json

        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height",
            "-show_entries", "format=duration",
            "-of", "json", request.video_path
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        probe_data = json.loads(probe_result.stdout)

        duration = float(probe_data.get("format", {}).get("duration", 0))
        video_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), {})
        width = int(video_stream.get("width", 1920))
        height = int(video_stream.get("height", 1080))

        segment_responses = [
            ExtractedSegmentResponse(
                segment_path=seg.segment_path,
                segment_index=seg.segment_index,
                start_s=seg.start_s,
                end_s=seg.end_s,
                duration_s=seg.duration_s,
                format=seg.format,
                file_size_bytes=seg.file_size_bytes
            )
            for seg in segments
        ]

        return ExtractShortformResponse(
            success=True,
            segments=segment_responses,
            source_duration_s=duration,
            source_resolution=f"{width}x{height}",
            error=None
        )

    except Exception as e:
        logger.error(f"Shortform extraction failed: {e}")
        return ExtractShortformResponse(
            success=False,
            segments=[],
            source_duration_s=0,
            source_resolution="",
            error=str(e)
        )

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "news-iq",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))

