"""
News IQ - Shared Utilities
Compatible with n8n Code nodes (JavaScript mode) and standalone Python
"""

import json
import math
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# UUID GENERATION
# ============================================================================
def generate_uuid() -> str:
    """Generate a UUID v4 string."""
    return str(uuid.uuid4())

# ============================================================================
# TIMESTAMP UTILITIES
# ============================================================================
def now_iso() -> str:
    """Current timestamp in ISO 8601 format."""
    return datetime.utcnow().isoformat() + "Z"

def today_start() -> str:
    """Start of today in ISO format."""
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"

def week_start() -> str:
    """Start of current week (Monday) in ISO format."""
    today = datetime.utcnow()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return monday.isoformat() + "Z"

def expires_at(days: int = 7) -> str:
    """Expiration timestamp N days from now."""
    return (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

# ============================================================================
# COSINE SIMILARITY (for deduplication)
# ============================================================================
def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Returns float between -1 and 1.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)

def semantic_dedup(
    new_articles: List[Dict],
    existing_embeddings: List[Dict],
    threshold: float = 0.85
) -> Tuple[List[Dict], int, int]:
    """
    Remove semantically duplicate articles.

    Args:
        new_articles: List of articles with 'embedding' field
        existing_embeddings: List of {id, embedding} from DB
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        (deduplicated_articles, unique_count, duplicates_removed)
    """
    deduplicated = []
    duplicates_removed = 0

    for article in new_articles:
        article_embedding = article.get("embedding")

        if article_embedding is None:
            deduplicated.append(article)
            continue

        is_duplicate = False

        for existing in existing_embeddings:
            existing_embedding = existing.get("embedding")
            if existing_embedding is None:
                continue

            similarity = cosine_similarity(article_embedding, existing_embedding)

            if similarity > threshold:
                is_duplicate = True
                duplicates_removed += 1
                break

        if not is_duplicate:
            deduplicated.append(article)

    return deduplicated, len(deduplicated), duplicates_removed

# ============================================================================
# ARTICLE NORMALIZATION
# ============================================================================
def normalize_article(article: Dict, category: str) -> Dict:
    """
    Normalize a raw NewsAPI article into our schema.

    Args:
        article: Raw article from NewsAPI
        category: Category string

    Returns:
        Normalized article dict
    """
    source = article.get("source", {}) or {}
    title = (article.get("title") or "").strip()

    if not title or len(title) < 5:
        return None

    return {
        "id": generate_uuid(),
        "original_title": title,
        "normalized_title": title.lower().strip(),
        "category": category,
        "source_key": source.get("id") or "unknown",
        "source_name": source.get("name") or "Unknown",
        "url": article.get("url") or "",
        "image_url": article.get("urlToImage"),
        "published_at": article.get("publishedAt"),
        "scraped_at": now_iso(),
        "description": article.get("description") or "",
        "content": article.get("content") or "",
        "embedding": None,
        "status": "pending_research",
        "created_at": now_iso(),
        "expires_at": expires_at(7)
    }

def normalize_all_articles(articles: List[Dict], category: str) -> List[Dict]:
    """Normalize a batch of articles, filtering out invalid ones."""
    normalized = []
    for article in articles:
        norm = normalize_article(article, category)
        if norm:
            normalized.append(norm)
    return normalized

# ============================================================================
# SCRIPT VALIDATION
# ============================================================================
def validate_daily_script(script_text: str) -> Dict[str, Any]:
    """
    Validate a daily short script.

    Returns:
        {valid: bool, word_count: int, duration_seconds: int, errors: List[str]}
    """
    errors = []

    # Clean markers for word count
    clean_text = re.sub(r'\[PAUSE\]', ' ', script_text)
    clean_text = re.sub(r'\[EMPHASIS:([^\]]+)\]', r'\1', clean_text)
    clean_text = re.sub(r'\[EMPHASIS\]', '', clean_text)
    clean_text = re.sub(r'\[SOUND:[^\]]+\]', '', clean_text)
    clean_text = clean_text.strip()

    words = clean_text.split()
    word_count = len(words)

    # ~150 words per minute = 2.5 words per second
    duration_seconds = int((word_count / 150) * 60)

    # Validation rules
    if word_count < 45:
        errors.append(f"Too short: {word_count} words (min 45)")
    if word_count > 150:
        errors.append(f"Too long: {word_count} words (max 150)")

    if duration_seconds < 20:
        errors.append(f"Too short: {duration_seconds}s (min 20)")
    if duration_seconds > 90:
        errors.append(f"Too long: {duration_seconds}s (max 90)")

    # Check for placeholder text
    placeholders = ["[PLACEHOLDER]", "<placeholder>", "TODO", "FIXME"]
    for ph in placeholders:
        if ph.lower() in script_text.lower():
            errors.append(f"Contains placeholder: {ph}")

    # Check for required markers
    if "[PAUSE]" not in script_text:
        errors.append("Missing [PAUSE] markers")

    # Check for hook and CTA
    if not any(hook in script_text.lower() for hook in ["breaking", "just announced", "here's what", "you need to know"]):
        errors.append("Weak hook - consider stronger opening")

    if "subscribe" not in script_text.lower() and "follow" not in script_text.lower():
        errors.append("Missing CTA (subscribe/follow)")

    return {
        "valid": len(errors) == 0,
        "word_count": word_count,
        "duration_seconds": duration_seconds,
        "errors": errors,
        "clean_text": clean_text
    }

def validate_weekly_script(script_text: str) -> Dict[str, Any]:
    """Validate a weekly recap script."""
    errors = []

    clean_text = re.sub(r'\[PAUSE\]', ' ', script_text)
    clean_text = re.sub(r'\[EMPHASIS:([^\]]+)\]', r'\1', clean_text)
    clean_text = re.sub(r'\[EMPHASIS\]', '', clean_text)
    clean_text = re.sub(r'\[SOUND:[^\]]+\]', '', clean_text)
    clean_text = clean_text.strip()

    words = clean_text.split()
    word_count = len(words)
    duration_seconds = int((word_count / 150) * 60)

    if word_count < 750:
        errors.append(f"Too short: {word_count} words (min 750)")
    if word_count > 1500:
        errors.append(f"Too long: {word_count} words (max 1500)")

    if duration_seconds < 300:
        errors.append(f"Too short: {duration_seconds}s (min 300)")
    if duration_seconds > 600:
        errors.append(f"Too long: {duration_seconds}s (max 600)")

    # Check structure
    if "intro" not in script_text.lower() and "welcome" not in script_text.lower():
        errors.append("Missing intro")

    if "outro" not in script_text.lower() and "thanks for watching" not in script_text.lower():
        errors.append("Missing outro")

    # Count segments (should have ~5)
    segment_markers = ["story", "segment", "next up", "moving on"]
    segment_count = sum(1 for m in segment_markers if m in script_text.lower())
    if segment_count < 3:
        errors.append(f"Too few segments detected ({segment_count}, expected ~5)")

    return {
        "valid": len(errors) == 0,
        "word_count": word_count,
        "duration_seconds": duration_seconds,
        "errors": errors,
        "clean_text": clean_text,
        "segment_count": segment_count
    }

# ============================================================================
# VIDEO QUALITY CHECK
# ============================================================================
def calculate_quality_score(video_metadata: Dict) -> Dict[str, Any]:
    """
    Calculate video quality score (0-100).

    Args:
        video_metadata: Dict with file_size_bytes, duration_seconds, 
                       format, codec info, etc.

    Returns:
        {score: float, status: str, notes: str, checks: Dict}
    """
    score = 0
    checks = {}
    notes = []

    # Codec check (+20)
    video_codec = video_metadata.get("video_codec", "")
    audio_codec = video_metadata.get("audio_codec", "")
    if video_codec in ["h264", "libx264"] and audio_codec in ["aac", "mp3"]:
        score += 20
        checks["codec"] = "PASS"
    else:
        checks["codec"] = "FAIL"
        notes.append(f"Codec issue: video={video_codec}, audio={audio_codec}")

    # Duration check (+20)
    expected_duration = video_metadata.get("expected_duration_seconds", 0)
    actual_duration = video_metadata.get("duration_seconds", 0)
    if expected_duration > 0 and actual_duration > 0:
        duration_diff = abs(actual_duration - expected_duration) / expected_duration
        if duration_diff <= 0.05:  # Within 5%
            score += 20
            checks["duration"] = "PASS"
        else:
            checks["duration"] = "WARN"
            notes.append(f"Duration mismatch: expected {expected_duration}s, got {actual_duration}s")
    else:
        checks["duration"] = "SKIP"

    # File size check (+20)
    file_size = video_metadata.get("file_size_bytes", 0)
    if file_size > 100 * 1024 * 1024:  # > 100MB
        score += 20
        checks["file_size"] = "PASS"
    else:
        checks["file_size"] = "WARN"
        notes.append(f"File size small: {file_size / (1024*1024):.1f}MB")

    # Format check (+20)
    fmt = video_metadata.get("format", "")
    if fmt in ["9:16", "16:9"]:
        score += 20
        checks["format"] = "PASS"
    else:
        checks["format"] = "FAIL"
        notes.append(f"Invalid format: {fmt}")

    # Audio loudness check (+20) - simplified
    loudness = video_metadata.get("audio_loudness_lufs", -20)
    if -23 <= loudness <= -18:
        score += 20
        checks["audio"] = "PASS"
    else:
        checks["audio"] = "WARN"
        notes.append(f"Audio loudness: {loudness} LUFS (target -23 to -18)")

    status = "approved" if score >= 70 else "pending_review" if score >= 50 else "failed"

    return {
        "score": min(score, 100),
        "status": status,
        "notes": "; ".join(notes) if notes else "All checks passed",
        "checks": checks
    }

# ============================================================================
# TTS TEXT CLEANER
# ============================================================================
def clean_script_for_tts(script_text: str) -> str:
    """
    Remove n8n script markers for text-to-speech processing.

    [PAUSE] -> "... "
    [EMPHASIS:word] -> "word"
    [EMPHASIS] -> ""
    [SOUND:effect] -> ""
    """
    text = script_text
    text = re.sub(r'\[PAUSE\]', '... ', text)
    text = re.sub(r'\[EMPHASIS:([^\]]+)\]', r'\1', text)
    text = re.sub(r'\[EMPHASIS\]', '', text)
    text = re.sub(r'\[SOUND:[^\]]+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ============================================================================
# LOG FORMATTER (for n8n PostgreSQL log inserts)
# ============================================================================
def format_log_entry(workflow: str, level: str, message: str, metadata: Dict = None) -> Dict:
    """Format a log entry for database insertion."""
    return {
        "workflow": workflow,
        "level": level,
        "message": message,
        "metadata": json.dumps(metadata or {}),
        "created_at": now_iso()
    }

# ============================================================================
# ERROR RESPONSE BUILDER (for n8n HTTP responses)
# ============================================================================
def build_response(success: bool, data: Dict = None, error: str = None) -> Dict:
    """Build a standardized response for n8n HTTP nodes."""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response

# ============================================================================
# CLAUDE PROMPT BUILDERS
# ============================================================================
def build_research_prompt(headline: str, search_results: List[Dict]) -> str:
    """Build the Claude research analysis prompt."""
    sources_text = "\n\n".join([
        f"Source: {s.get('source', 'Unknown')}\nURL: {s.get('url', '')}\nSnippet: {s.get('snippet', '')}"
        for s in search_results[:3]
    ])

    return f"""Analyze this headline and research findings. Extract key facts, identify any contradictions, and assign confidence levels.

Headline: {headline}

Search Results:
{sources_text}

Respond in JSON with this exact structure:
{{
    "summary": "Brief 2-3 sentence summary of the story",
    "key_facts": [
        {{
            "fact": "What happened",
            "confidence": "high|medium|low",
            "sources_mentioning": ["Source1", "Source2"]
        }}
    ],
    "contradictions": [
        {{
            "claim": "What was claimed",
            "conflict": "Different versions",
            "sources": ["Source1", "Source2"]
        }}
    ],
    "verification_status": "high_confidence|medium_confidence|single_source|unverified"
}}"""

def build_daily_script_prompt(headline: Dict) -> str:
    """Build the Claude daily script generation prompt."""
    facts = headline.get("key_facts", [])
    facts_text = "\n".join([
        f"- {f.get('fact', '')} (confidence: {f.get('confidence', 'unknown')})"
        for f in facts[:3]
    ])

    return f"""Write a punchy 30-60 second script for a news short video. Must include: hook (first 3 seconds), key facts, call-to-action.

Headline: {headline.get('title', '')}
Research Summary: {headline.get('research_summary', '')}
Key Facts:
{facts_text}

Use these markers:
[PAUSE] - natural pause (0.5-1 second)
[EMPHASIS:word] - emphasize this word
[SOUND:alert] - sound effect cue

Start with a hook that grabs attention. Keep language conversational and energetic. End with a clear CTA to subscribe/follow.

Script:"""

def build_weekly_script_prompt(top_stories: List[Dict]) -> str:
    """Build the Claude weekly script generation prompt."""
    stories_text = "\n\n".join([
        f"Story {i+1}: {s.get('title', '')}\nSummary: {s.get('research_summary', '')}"
        for i, s in enumerate(top_stories[:5])
    ])

    return f"""Write a professional 5-10 minute news recap script for YouTube.
Format: Intro (10s) -> 5 story segments (2 min each) -> Outro (30s)

Include:
- Host intro: "Welcome to this week's news brief..."
- For each story: headline, key facts, why it matters, brief analysis
- Smooth transitions between stories
- Outro with call-to-action to subscribe

Use [PAUSE] and [EMPHASIS:word] markers.
Maintain consistent host tone: professional, engaging, conversational.

Target: 750-1500 words (~5-10 minutes at 150 wpm)

Top Stories:
{stories_text}

Full Script:"""

def build_weekly_ranking_prompt(headlines: List[Dict]) -> str:
    """Build the Claude weekly story ranking prompt."""
    headlines_text = "\n".join([
        f"{i+1}. {h.get('title', '')} - {h.get('research_summary', '')[:100]}..."
        for i, h in enumerate(headlines)
    ])

    return f"""Rank these world news stories by importance, impact, and geopolitical relevance. Return the top 5 most significant stories.

Headlines:
{headlines_text}

Respond in JSON:
{{
    "top_stories": [
        {{
            "title": "Story title",
            "ranking_reason": "Why this story matters"
        }}
    ]
}}"""

# ============================================================================
# CLAUDE RESPONSE PARSERS
# ============================================================================
def parse_claude_json_response(response_text: str) -> Optional[Dict]:
    """
    Parse JSON from Claude response, handling markdown code blocks.

    Args:
        response_text: Raw text from Claude API

    Returns:
        Parsed dict or None
    """
    if not response_text:
        return None

    text = response_text.strip()

    # Handle markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to extract JSON with regex as fallback
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        return None

# ============================================================================
# NOTIFICATION FORMATTERS
# ============================================================================
def format_whatsapp_post_notification(platform: str, post_url: str, title: str) -> str:
    """Format a WhatsApp notification for a successful post."""
    emoji_map = {"youtube": "📺", "tiktok": "🎵", "instagram": "📸"}
    emoji = emoji_map.get(platform.lower(), "✅")
    return f"{emoji} Posted to {platform.upper()}!\n\n{title}\n{post_url}"

def format_approval_email(video_title: str, drive_link: str, video_id: str) -> Dict:
    """Format an approval email."""
    return {
        "subject": f"📹 Weekly Video Ready for Review: {video_title}",
        "body": f"""Your weekly news video is ready for review.

Video: {video_title}
Preview: {drive_link}
Video ID: {video_id}

Please watch the video and reply to this email with "APPROVED" to publish it to all platforms.

If you do not approve within 24 hours, the video will be skipped for this week.

---
News IQ Automated System
""",
        "video_id": video_id
    }

# ============================================================================
# N8N-SPECIFIC HELPERS
# ============================================================================
def n8n_return_items(items: List[Dict]) -> List[Dict]:
    """
    Format items for n8n Code node return.
    n8n expects: [{"json": {...}}]
    """
    return [{"json": item} for item in items]

def n8n_get_input_items(items) -> List[Dict]:
    """
    Extract JSON data from n8n input items.
    Handles both n8n's item format and plain dicts.
    """
    result = []
    for item in items:
        if isinstance(item, dict) and "json" in item:
            result.append(item["json"])
        elif isinstance(item, dict):
            result.append(item)
    return result

