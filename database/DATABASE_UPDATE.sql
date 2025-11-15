-- Database update for approval workflow
-- Run this SQL to update the scheduled_post table

USE smms;

-- Update the scheduled_post status ENUM to include 'pending'
ALTER TABLE scheduled_post 
MODIFY COLUMN status ENUM('pending', 'scheduled', 'published', 'failed') DEFAULT 'scheduled';

-- Verify the change
DESCRIBE scheduled_post;

ALTER TABLE linked_account ADD COLUMN external_id VARCHAR(255);


ALTER TABLE platform 
ADD COLUMN user_id INT NULL AFTER is_active,
ADD COLUMN platform_user_id VARCHAR(255) NULL AFTER user_id,
ADD COLUMN access_token TEXT NULL AFTER platform_user_id,
ADD COLUMN refresh_token TEXT NULL AFTER access_token,
ADD COLUMN expires_at DATETIME NULL AFTER refresh_token,
ADD COLUMN account_username VARCHAR(100) NULL AFTER expires_at,
ADD COLUMN follower_count INT DEFAULT 0 AFTER account_username,
ADD COLUMN post_count INT DEFAULT 0 AFTER follower_count,
ADD FOREIGN KEY (user_id) REFERENCES user(user_id);

