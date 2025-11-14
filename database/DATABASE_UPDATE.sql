-- Database update for approval workflow
-- Run this SQL to update the scheduled_post table

USE smms;

-- Update the scheduled_post status ENUM to include 'pending'
ALTER TABLE scheduled_post 
MODIFY COLUMN status ENUM('pending', 'scheduled', 'published', 'failed') DEFAULT 'scheduled';

-- Verify the change
DESCRIBE scheduled_post;
