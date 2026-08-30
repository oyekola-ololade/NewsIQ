-- News IQ Database Schema
-- PostgreSQL 15+ with pgvector extension

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- CATEGORIES
-- ============================================================
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO categories (name, display_name) VALUES
('technology', 'Technology'),
('sports', 'Sports'),
('entertainment', 'Entertainment'),
('world', 'World News'),
('business', 'Business')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SOURCES
-- ============================================================
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    domain VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    country VARCHAR(10) DEFAULT 'us',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sources_key ON sources(source_key);

-- ============================================================
-- HEADLINES (Main Table)
-- ============================================================
CREATE TABLE headlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    category VARCHAR(50) NOT NULL REFERENCES categories(name),
    source_id UUID NOT NULL REFERENCES sources(id),
    url TEXT UNIQUE NOT NULL,
    image_url TEXT,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT,
    content TEXT,
    embedding vector(384),
    status VARCHAR(20) DEFAULT 'pending_research',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '7 days',
    CONSTRAINT valid_status CHECK (
        status IN ('pending_research', 'researched', 'scripted', 'generated', 'published')
    )
);

CREATE INDEX idx_headlines_status ON headlines(status);
CREATE INDEX idx_headlines_category ON headlines(category);
CREATE INDEX idx_headlines_scraped_at ON headlines(scraped_at);
CREATE INDEX idx_headlines_expires_at ON headlines(expires_at);
CREATE INDEX idx_headlines_embedding ON headlines USING ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- RESEARCH
-- ============================================================
CREATE TABLE research (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    headline_id UUID NOT NULL REFERENCES headlines(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    key_facts JSONB DEFAULT '[]',
    contradictions JSONB DEFAULT '[]',
    verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified',
    source_urls JSONB DEFAULT '[]',
    generated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_verification CHECK (
        verification_status IN ('high_confidence', 'medium_confidence', 'single_source', 'unverified')
    )
);

CREATE INDEX idx_research_headline_id ON research(headline_id);
CREATE INDEX idx_research_verification_status ON research(verification_status);

-- ============================================================
-- SCRIPTS
-- ============================================================
CREATE TABLE scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    headline_id UUID REFERENCES headlines(id) ON DELETE CASCADE,
    script_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    word_count INT,
    estimated_duration_seconds INT,
    tone VARCHAR(50) DEFAULT 'professional',
    generated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_script_type CHECK (script_type IN ('daily_short', 'weekly')),
    CONSTRAINT valid_word_count CHECK (
        (script_type = 'daily_short' AND word_count >= 45 AND word_count <= 150)
        OR (script_type = 'weekly' AND word_count >= 750 AND word_count <= 1500)
    )
);

CREATE INDEX idx_scripts_headline_id ON scripts(headline_id);
CREATE INDEX idx_scripts_type ON scripts(script_type);
CREATE INDEX idx_scripts_created_at ON scripts(created_at);

-- ============================================================
-- VIDEOS
-- ============================================================
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id),
    video_type VARCHAR(20) NOT NULL,
    file_path_local TEXT,
    google_drive_id VARCHAR(255),
    google_drive_link TEXT,
    duration_seconds INT,
    format VARCHAR(20),
    file_size_bytes BIGINT,
    quality_score FLOAT,
    quality_status VARCHAR(20) DEFAULT 'pending_review',
    quality_notes TEXT,
    generated_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_video_type CHECK (video_type IN ('daily_short', 'weekly')),
    CONSTRAINT valid_quality_status CHECK (quality_status IN ('pending_review', 'approved', 'failed')),
    CONSTRAINT valid_format CHECK (format IN ('9:16', '16:9'))
);

CREATE INDEX idx_videos_script_id ON videos(script_id);
CREATE INDEX idx_videos_quality_status ON videos(quality_status);
CREATE INDEX idx_videos_video_type ON videos(video_type);

-- ============================================================
-- DISTRIBUTIONS
-- ============================================================
CREATE TABLE distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id),
    platform VARCHAR(50) NOT NULL,
    post_id VARCHAR(255),
    post_url TEXT,
    scheduled_time TIMESTAMP,
    posted_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    retry_count INT DEFAULT 0,
    last_retry TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_platform CHECK (platform IN ('youtube', 'tiktok', 'instagram')),
    CONSTRAINT valid_dist_status CHECK (status IN ('pending', 'posted', 'failed'))
);

CREATE INDEX idx_distributions_video_id ON distributions(video_id);
CREATE INDEX idx_distributions_platform ON distributions(platform);
CREATE INDEX idx_distributions_status ON distributions(status);
CREATE INDEX idx_distributions_scheduled_time ON distributions(scheduled_time);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    video_id UUID REFERENCES videos(id),
    channel VARCHAR(20),
    recipient VARCHAR(255),
    message TEXT,
    sent_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_notification_status CHECK (status IN ('pending', 'sent', 'failed'))
);

CREATE INDEX idx_notifications_event_type ON notifications(event_type);
CREATE INDEX idx_notifications_status ON notifications(status);

-- ============================================================
-- LOGS
-- ============================================================
CREATE TABLE logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow VARCHAR(50) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_log_level CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

CREATE INDEX idx_logs_workflow ON logs(workflow);
CREATE INDEX idx_logs_level ON logs(level);
CREATE INDEX idx_logs_created_at ON logs(created_at DESC);

-- ============================================================
-- CLEANUP FUNCTION (7-day retention)
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS void AS $$
BEGIN
    DELETE FROM headlines WHERE expires_at < NOW();
    DELETE FROM research WHERE created_at < NOW() - INTERVAL '7 days';
    DELETE FROM scripts WHERE created_at < NOW() - INTERVAL '7 days';
    DELETE FROM videos WHERE created_at < NOW() - INTERVAL '7 days';
    DELETE FROM distributions WHERE created_at < NOW() - INTERVAL '7 days';
    DELETE FROM notifications WHERE created_at < NOW() - INTERVAL '7 days';
    DELETE FROM logs WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Run this via cron or pg_cron:
-- SELECT cron.schedule('cleanup-job', '0 0 * * *', 'SELECT cleanup_expired_data()');

