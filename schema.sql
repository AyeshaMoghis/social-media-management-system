-- ======================================================
--  SMMS DATABASE MIGRATION: Initial Schema
--  Date: 2025-11-04
-- ======================================================

-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS smms_db;
USE smms_db;

-- ===========================
-- Table: user
-- ===========================
CREATE TABLE IF NOT EXISTS user (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role ENUM('user', 'manager') DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ===========================
-- Table: platform
-- ===========================
CREATE TABLE IF NOT EXISTS platform (
    platform_id INT AUTO_INCREMENT PRIMARY KEY,
    platform_name VARCHAR(50) NOT NULL,
    api_endpoint VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

-- ===========================
-- Table: linked_account
-- ===========================
CREATE TABLE IF NOT EXISTS linked_account (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    platform_id INT,
    access_token TEXT,
    refresh_token TEXT,
    external_id VARCHAR(255),  -- Added column
    token_expiry DATETIME,
    account_username VARCHAR(100),
    linked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    follower_count INT DEFAULT 0,
    post_count INT DEFAULT 0,
    last_synced DATETIME,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE
);

-- ===========================
-- Table: post
-- ===========================
CREATE TABLE IF NOT EXISTS post (
    post_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    platform_id INT,
    content_text TEXT,
    media_url VARCHAR(255),
    status ENUM('draft', 'pending', 'approved', 'rejected', 'scheduled', 'published', 'failed') DEFAULT 'draft',  -- Modified column
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    approved_by INT,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES user(user_id),
    FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE
);

-- ===========================
-- Table: scheduled_post
-- ===========================
CREATE TABLE IF NOT EXISTS scheduled_post (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT,
    platform_id INT,
    scheduled_time DATETIME,
    status ENUM('scheduled', 'published', 'failed') DEFAULT 'scheduled',
    published_at DATETIME,
    error_message TEXT,
    FOREIGN KEY (post_id) REFERENCES post(post_id) ON DELETE CASCADE,
    FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE
);

-- ===========================
-- Table: analytics
-- ===========================
CREATE TABLE IF NOT EXISTS analytics (
    analytics_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT,
    platform_id INT,
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    impressions INT DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES post(post_id) ON DELETE CASCADE,
    FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE
);

-- ===========================
-- Table: oauth_state
-- ===========================
CREATE TABLE IF NOT EXISTS oauth_state (
    state_id VARCHAR(100) PRIMARY KEY,
    user_id INT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    code_verifier VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

-- ===========================
-- Insert default platforms
-- ===========================
INSERT INTO platform (platform_name, api_endpoint, is_active)
VALUES
    ('LinkedIn', 'https://api.linkedin.com/v2/ugcPosts', TRUE),
    ('Medium', 'https://api.medium.com/v1/users/{{userId}}/posts', TRUE),
    ('Twitter', 'https://api.twitter.com/2', TRUE);
