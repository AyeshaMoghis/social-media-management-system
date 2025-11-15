-- Add missing post_platform table to smms_db
USE smms_db;

CREATE TABLE IF NOT EXISTS post_platform (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT,
    platform_id INT,
    platform_post_id VARCHAR(255),
    published BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    published_at DATETIME,
    FOREIGN KEY (post_id) REFERENCES post(post_id) ON DELETE CASCADE,
    FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE
);
