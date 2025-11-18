-- Use/create database
CREATE DATABASE IF NOT EXISTS smms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smms;

-- user
CREATE TABLE IF NOT EXISTS `user` (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(100) NOT NULL UNIQUE,
  password_hash VARCHAR(255),
  full_name VARCHAR(100),
  role VARCHAR(20) DEFAULT 'user',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- platform
CREATE TABLE IF NOT EXISTS platform (
  platform_id INT AUTO_INCREMENT PRIMARY KEY,
  platform_name VARCHAR(100) NOT NULL,
  api_endpoint VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE
);

-- linked_account
CREATE TABLE IF NOT EXISTS linked_account (
  account_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  platform_id INT,
  access_token TEXT,
  refresh_token TEXT,
  external_id VARCHAR(255),
  account_username VARCHAR(100),
  follower_count INT DEFAULT 0,
  post_count INT DEFAULT 0,
  last_synced DATETIME,
  linked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES `user`(user_id) ON DELETE CASCADE,
  FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE
);

-- post
CREATE TABLE IF NOT EXISTS post (
  post_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  platform_id INT,
  content_text TEXT,
  media_url VARCHAR(500),
  status ENUM('draft','pending','approved','rejected','scheduled','published','failed') DEFAULT 'draft',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES `user`(user_id) ON DELETE CASCADE
);

-- post_platform
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

-- scheduled_post
CREATE TABLE IF NOT EXISTS scheduled_post (
  schedule_id INT AUTO_INCREMENT PRIMARY KEY,
  post_id INT,
  platform_id INT,
  scheduled_time DATETIME,
  status ENUM('scheduled','published','failed') DEFAULT 'scheduled',
  published_at DATETIME,
  error_message TEXT,
  FOREIGN KEY (post_id) REFERENCES post(post_id) ON DELETE CASCADE,
  FOREIGN KEY (platform_id) REFERENCES platform(platform_id) ON DELETE CASCADE
);

-- notification
CREATE TABLE IF NOT EXISTS notification (
  notification_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  post_id INT,
  schedule_id INT,
  notification_type VARCHAR(50),
  title VARCHAR(255),
  message TEXT,
  is_read BOOLEAN DEFAULT FALSE,
  sent_via ENUM('email','in_app','both') DEFAULT 'both',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  read_at DATETIME NULL,
  FOREIGN KEY (user_id) REFERENCES `user`(user_id) ON DELETE CASCADE,
  FOREIGN KEY (post_id) REFERENCES post(post_id) ON DELETE SET NULL,
  FOREIGN KEY (schedule_id) REFERENCES scheduled_post(schedule_id) ON DELETE SET NULL
);
