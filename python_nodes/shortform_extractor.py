"""
News IQ - Weekly Shortform Extractor
Extracts 3-4 optimal segments from weekly 16:9 video and converts to 9:16 shorts.
Called by n8n via the /extract-shortform API endpoint.
"""

import os
import math
import tempfile
import subprocess
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    """Metadata extracted from a video file."""
    duration_s: float
    width: int
    height: int
    fps: float
    bitrate_kbps: float
    audio_codec: str
    video_codec: str


@dataclass
class Segment:
    """A video segment definition."""
    start_s: float
    end_s: float
    duration_s: float
    score: float
    index: int


@dataclass
class ExtractedSegment:
    """An extracted and converted segment."""
    segment_path: str
    segment_index: int
    start_s: float
    end_s: float
    duration_s: float
    format: str
    file_size_bytes: int


class WeeklyShortformExtractor:
    """
    Extract optimal segments from weekly video for shortform platforms.

    Process:
    1. Analyze video (duration, resolution, codecs)
    2. Detect scene changes / natural breakpoints
    3. Extract 3-4 optimal segments (30-60s each)
    4. Convert each segment from 16:9 to 9:16
    5. Return paths to extracted segments
    """

    def __init__(
        self,
        target_duration_s: float = 45.0,
        min_segments: int = 3,
        max_segments: int = 4,
        min_segment_length_s: float = 30.0,
        max_segment_length_s: float = 60.0,
        scene_threshold: float = 0.35,
        output_resolution: Tuple[int, int] = (1080, 1920)
    ):
        self.target_duration_s = target_duration_s
        self.min_segments = min_segments
        self.max_segments = max_segments
        self.min_segment_length_s = min_segment_length_s
        self.max_segment_length_s = max_segment_length_s
        self.scene_threshold = scene_threshold
        self.output_resolution = output_resolution

    # =====================================================================
    # PUBLIC API
    # =====================================================================

    async def extract_segments(self, video_path: str) -> List[ExtractedSegment]:
        """
        Main entry point: extract shortform segments from weekly video.

        Args:
            video_path: Path to the weekly 16:9 MP4 video

        Returns:
            List of ExtractedSegment objects (3-4 items)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"Starting shortform extraction from: {video_path}")

        # Step 1: Analyze video
        metadata = await self._analyze_video(video_path)
        logger.info(f"Video metadata: {metadata.duration_s:.1f}s, "
                   f"{metadata.width}x{metadata.height}, {metadata.fps}fps")

        # Step 2: Detect breakpoints
        breakpoints = await self._detect_breakpoints(video_path, metadata)
        logger.info(f"Detected {len(breakpoints)} potential breakpoints")

        # Step 3: Define optimal segments
        segments = await self._define_segments(breakpoints, metadata)
        logger.info(f"Selected {len(segments)} segments for extraction")

        # Step 4: Extract and convert each segment
        extracted = []
        temp_dir = tempfile.mkdtemp(prefix="news_iq_shortform_")

        for i, segment in enumerate(segments):
            segment_path = await self._extract_and_convert_segment(
                video_path=video_path,
                segment=segment,
                output_dir=temp_dir,
                output_index=i,
                source_metadata=metadata
            )

            file_size = os.path.getsize(segment_path)
            extracted.append(ExtractedSegment(
                segment_path=segment_path,
                segment_index=i,
                start_s=segment.start_s,
                end_s=segment.end_s,
                duration_s=segment.duration_s,
                format="9:16",
                file_size_bytes=file_size
            ))
            logger.info(f"Extracted segment {i}: {segment.start_s:.1f}s - "
                       f"{segment.end_s:.1f}s ({segment.duration_s:.1f}s)")

        logger.info(f"Shortform extraction complete: {len(extracted)} segments")
        return extracted

    # =====================================================================
    # STEP 1: VIDEO ANALYSIS
    # =====================================================================

    async def _analyze_video(self, video_path: str) -> VideoMetadata:
        """Extract metadata using ffprobe."""

        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,bit_rate",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-of", "json",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)

        # Parse format info
        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))
        bitrate = float(fmt.get("bit_rate", 0)) / 1000  # kbps

        # Parse stream info
        streams = data.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

        width = int(video_stream.get("width", 1920))
        height = int(video_stream.get("height", 1080))

        # Parse fps from fraction (e.g., "30000/1001")
        fps_str = video_stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)

        return VideoMetadata(
            duration_s=duration,
            width=width,
            height=height,
            fps=fps,
            bitrate_kbps=bitrate,
            audio_codec=audio_stream.get("codec_name", "aac"),
            video_codec=video_stream.get("codec_name", "h264")
        )

    # =====================================================================
    # STEP 2: BREAKPOINT DETECTION
    # =====================================================================

    async def _detect_breakpoints(
        self,
        video_path: str,
        metadata: VideoMetadata
    ) -> List[Tuple[float, float]]:
        """
        Detect natural breakpoints in the video.

        Strategy:
        1. Use FFmpeg scene detection to find visual transitions
        2. Use equal-interval fallback for uniform coverage
        3. Merge and score breakpoints

        Returns:
            List of (timestamp_s, confidence_score) tuples
        """
        breakpoints = []

        # Method 1: Scene detection via FFmpeg
        scene_breakpoints = await self._detect_scene_changes(video_path)
        breakpoints.extend(scene_breakpoints)

        # Method 2: Equal-interval breakpoints (ensures coverage)
        interval_breakpoints = self._generate_interval_breakpoints(metadata.duration_s)
        breakpoints.extend(interval_breakpoints)

        # Sort and deduplicate (merge breakpoints within 5s of each other)
        breakpoints.sort(key=lambda x: x[0])
        merged = self._merge_nearby_breakpoints(breakpoints, min_distance_s=5.0)

        return merged

    async def _detect_scene_changes(self, video_path: str) -> List[Tuple[float, float]]:
        """Use FFmpeg select filter to detect scene changes."""

        # Export frame timestamps where scene change exceeds threshold
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"select='gt(scene\\,{self.scene_threshold})',showinfo",
            "-f", "null", "-"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        breakpoints = []
        for line in result.stderr.split("\n"):
            # Parse lines like: "pts_time:123.456"
            if "pts_time:" in line:
                try:
                    timestamp_str = line.split("pts_time:")[1].split(" ")[0]
                    timestamp = float(timestamp_str)
                    # Skip very start and very end
                    if 5.0 < timestamp < (result.returncode or 300):  # rough guard
                        breakpoints.append((timestamp, 0.8))
                except (ValueError, IndexError):
                    continue

        return breakpoints

    def _generate_interval_breakpoints(
        self,
        total_duration_s: float
    ) -> List[Tuple[float, float]]:
        """Generate evenly-spaced breakpoints for coverage."""

        # Divide video into max_segments + 1 parts
        num_breakpoints = self.max_segments + 1
        interval = total_duration_s / num_breakpoints

        breakpoints = []
        for i in range(1, num_breakpoints):
            timestamp = i * interval
            # Lower confidence for interval-based (0.5) vs scene-based (0.8)
            breakpoints.append((timestamp, 0.5))

        return breakpoints

    def _merge_nearby_breakpoints(
        self,
        breakpoints: List[Tuple[float, float]],
        min_distance_s: float = 5.0
    ) -> List[Tuple[float, float]]:
        """Merge breakpoints that are too close together."""

        if not breakpoints:
            return []

        merged = [breakpoints[0]]

        for timestamp, confidence in breakpoints[1:]:
            last_timestamp, last_confidence = merged[-1]

            if abs(timestamp - last_timestamp) < min_distance_s:
                # Merge: keep the one with higher confidence
                if confidence > last_confidence:
                    merged[-1] = (timestamp, confidence)
            else:
                merged.append((timestamp, confidence))

        return merged

    # =====================================================================
    # STEP 3: SEGMENT DEFINITION
    # =====================================================================

    async def _define_segments(
        self,
        breakpoints: List[Tuple[float, float]],
        metadata: VideoMetadata
    ) -> List[Segment]:
        """
        Define optimal segments based on breakpoints.

        Ensures:
        - Each segment is 30-60 seconds
        - Segments don't overlap
        - We get 3-4 segments total
        """

        duration = metadata.duration_s

        # Create candidate segments between breakpoints
        all_times = [0.0] + [bp[0] for bp in breakpoints] + [duration]
        all_times.sort()

        candidates = []
        for i in range(len(all_times) - 1):
            start = all_times[i]
            end = all_times[i + 1]
            seg_duration = end - start

            if self.min_segment_length_s <= seg_duration <= self.max_segment_length_s:
                # Score based on position (prefer middle sections, avoid very start/end)
                position_score = 1.0 - abs((start + end) / 2 - duration / 2) / (duration / 2)
                candidates.append(Segment(
                    start_s=start,
                    end_s=end,
                    duration_s=seg_duration,
                    score=position_score,
                    index=i
                ))

        # If we don't have enough candidates, force-split the video evenly
        if len(candidates) < self.min_segments:
            candidates = self._force_split_evenly(duration)

        # Sort by score and take top segments
        candidates.sort(key=lambda s: s.score, reverse=True)
        selected = candidates[:self.max_segments]

        # Sort by start time for chronological order
        selected.sort(key=lambda s: s.start_s)

        # Re-index
        for i, seg in enumerate(selected):
            seg.index = i

        return selected

    def _force_split_evenly(self, duration: float) -> List[Segment]:
        """Force-split video into equal segments when natural breakpoints fail."""

        num_segments = self.max_segments
        segment_length = duration / num_segments

        # Clamp to target range
        segment_length = max(self.min_segment_length_s,
                            min(segment_length, self.max_segment_length_s))

        segments = []
        for i in range(num_segments):
            start = i * segment_length
            end = min(start + self.target_duration_s, duration)

            # Adjust end if it exceeds duration
            if end > duration - 5:  # Leave 5s buffer at end
                end = duration

            seg_duration = end - start
            if seg_duration >= self.min_segment_length_s:
                segments.append(Segment(
                    start_s=start,
                    end_s=end,
                    duration_s=seg_duration,
                    score=0.6,
                    index=i
                ))

        return segments

    # =====================================================================
    # STEP 4: EXTRACT & CONVERT
    # =====================================================================

    async def _extract_and_convert_segment(
        self,
        video_path: str,
        segment: Segment,
        output_dir: str,
        output_index: int,
        source_metadata: VideoMetadata
    ) -> str:
        """
        Extract a segment and convert from 16:9 to 9:16.

        Conversion strategy:
        - Input: 1920x1080 (16:9) or similar
        - Output: 1080x1920 (9:16)
        - Center crop: keep middle portion, crop sides
        - Preserve quality with libx264 + AAC
        """

        output_path = os.path.join(output_dir, f"weekly_segment_{output_index}.mp4")

        # Build FFmpeg command
        # Strategy: scale to fit height, then crop width to 9:16 ratio
        # For 1080x1920 output from 1920x1080 input:
        # - Scale so height = 1920, width becomes 1920 * (16/9) = 3413
        # - Crop width from center: 3413 -> 1080
        # - crop=1080:1920:(3413-1080)/2:0

        source_w = source_metadata.width
        source_h = source_metadata.height
        target_w, target_h = self.output_resolution

        # Calculate crop parameters
        # Scale to target height first, then crop width
        scaled_w = int(target_h * source_w / source_h)
        crop_x = int((scaled_w - target_w) / 2)

        # Ensure crop_x is even (required by some codecs)
        crop_x = crop_x - (crop_x % 2)

        vf_filter = (
            f"scale={scaled_w}:{target_h},"
            f"crop={target_w}:{target_h}:{crop_x}:0,"
            f"format=yuv420p"
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(segment.start_s),
            "-to", str(segment.end_s),
            "-i", video_path,
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Segment extraction failed: {result.stderr[:500]}")

        if not os.path.exists(output_path):
            raise RuntimeError("Segment file was not created")

        return output_path

    # =====================================================================
    # UTILITY
    # =====================================================================

    def cleanup_temp_files(self, segments: List[ExtractedSegment]):
        """Clean up extracted segment files."""
        for seg in segments:
            try:
                if os.path.exists(seg.segment_path):
                    os.remove(seg.segment_path)
                    logger.info(f"Cleaned up: {seg.segment_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {seg.segment_path}: {e}")


# =====================================================================
# STANDALONE TEST
# =====================================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        extractor = WeeklyShortformExtractor()
        # Test with a sample video path
        # segments = await extractor.extract_segments("/path/to/weekly.mp4")
        # for seg in segments:
        #     print(f"Segment {seg.segment_index}: {seg.duration_s:.1f}s at {seg.segment_path}")
        print("Shortform extractor ready. Import and call extract_segments(video_path).")

    asyncio.run(test())
