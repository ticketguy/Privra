-- Reputation System Database Schema
-- Run this after initial database setup

-- User reputation tracking
CREATE TABLE IF NOT EXISTS user_reputation (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL,
    current_score INTEGER DEFAULT 100 CHECK (current_score >= 0 AND current_score <= 100),
    tier VARCHAR(20) DEFAULT 'normal' CHECK (tier IN ('normal', 'warning', 'throttle', 'walled', 'frozen')),
    is_frozen BOOLEAN DEFAULT FALSE,
    last_violation_at TIMESTAMP,
    last_score_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_reports_received INTEGER DEFAULT 0,
    total_reports_filed INTEGER DEFAULT 0,
    false_report_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reputation events log
CREATE TABLE IF NOT EXISTS reputation_events (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    score_change INTEGER NOT NULL,
    old_score INTEGER NOT NULL,
    new_score INTEGER NOT NULL,
    old_tier VARCHAR(20),
    new_tier VARCHAR(20),
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User reports (spam/abuse reports)
CREATE TABLE IF NOT EXISTS abuse_reports (
    id SERIAL PRIMARY KEY,
    reporter_email VARCHAR(255) NOT NULL,
    reported_email VARCHAR(255) NOT NULL,
    reporter_score INTEGER,
    impact_multiplier DECIMAL(3,2),
    score_penalty INTEGER,
    reason VARCHAR(100),
    details TEXT,
    email_subject VARCHAR(500),
    email_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'dismissed', 'false_report')),
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reporter_email, reported_email, created_at::DATE)
);

-- Bounce tracking
CREATE TABLE IF NOT EXISTS bounce_tracking (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    bounce_type VARCHAR(50),
    bounce_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spam trap hits (honeypot addresses)
CREATE TABLE IF NOT EXISTS spam_trap_hits (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    trap_address VARCHAR(255) NOT NULL,
    email_subject VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sending velocity violations
CREATE TABLE IF NOT EXISTS velocity_violations (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    emails_sent INTEGER NOT NULL,
    time_window INTEGER NOT NULL,
    threshold_exceeded BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Penalty notifications log
CREATE TABLE IF NOT EXISTS penalty_notifications (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    tier VARCHAR(20) NOT NULL,
    score INTEGER NOT NULL,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spam trap addresses (honeypots)
CREATE TABLE IF NOT EXISTS spam_traps (
    id SERIAL PRIMARY KEY,
    trap_email VARCHAR(255) UNIQUE NOT NULL,
    trap_type VARCHAR(50) DEFAULT 'honeypot',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_reputation_email ON user_reputation(user_email);
CREATE INDEX IF NOT EXISTS idx_user_reputation_score ON user_reputation(current_score);
CREATE INDEX IF NOT EXISTS idx_user_reputation_tier ON user_reputation(tier);
CREATE INDEX IF NOT EXISTS idx_reputation_events_user ON reputation_events(user_email);
CREATE INDEX IF NOT EXISTS idx_reputation_events_type ON reputation_events(event_type);
CREATE INDEX IF NOT EXISTS idx_abuse_reports_reporter ON abuse_reports(reporter_email);
CREATE INDEX IF NOT EXISTS idx_abuse_reports_reported ON abuse_reports(reported_email);
CREATE INDEX IF NOT EXISTS idx_abuse_reports_status ON abuse_reports(status);
CREATE INDEX IF NOT EXISTS idx_bounce_tracking_user ON bounce_tracking(user_email);
CREATE INDEX IF NOT EXISTS idx_spam_trap_hits_user ON spam_trap_hits(user_email);
CREATE INDEX IF NOT EXISTS idx_velocity_violations_user ON velocity_violations(user_email);

-- Function to automatically create reputation record for new users
CREATE OR REPLACE FUNCTION create_reputation_for_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_reputation (user_email)
    VALUES (NEW.email)
    ON CONFLICT (user_email) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create reputation when user is created
DROP TRIGGER IF EXISTS trigger_create_reputation ON users;
CREATE TRIGGER trigger_create_reputation
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_reputation_for_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_reputation_timestamp ON user_reputation;
CREATE TRIGGER trigger_update_reputation_timestamp
    BEFORE UPDATE ON user_reputation
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some example spam traps (customize these for your domain)
INSERT INTO spam_traps (trap_email, trap_type) VALUES
    ('noreply@' || (SELECT domain FROM domains LIMIT 1), 'honeypot'),
    ('abuse@' || (SELECT domain FROM domains LIMIT 1), 'honeypot'),
    ('postmaster@' || (SELECT domain FROM domains LIMIT 1), 'honeypot')
ON CONFLICT (trap_email) DO NOTHING;
