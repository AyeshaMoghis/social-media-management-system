-- ======================================================
--  SMMS DATABASE MIGRATION: Add post_platform Table
--  Date: 2025-11-04
-- ======================================================

USE smms_db;

-- ===========================
-- Table: post_platform
-- ===========================
CREATE TABLE IF NOT EXISTS post_platform (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    platform_id INT NOT NULL,
    platform_post_id VARCHAR(255),
    published BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    FOREIGN KEY (post_id) REFERENCES post(post_id) ON DELETE CASCADE,
    FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE,
    INDEX idx_post_id (post_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
