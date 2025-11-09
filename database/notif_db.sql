-- ============================================================
-- SMMS Notification System (Clean Schema)
-- User Story 3.4: Notify user after post is published or fails
-- ============================================================

USE smms_db;

-- ============================================================
-- TABLES
-- ============================================================

DROP TABLE IF EXISTS notification_log;
DROP TABLE IF EXISTS notification_preference;
DROP TABLE IF EXISTS notification;

CREATE TABLE notification (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    post_id INT,
    schedule_id INT,
    notification_type ENUM('publish_success', 'publish_failure', 'engagement_alert', 'task_assignment') NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_via ENUM('email', 'in_app', 'both') NOT NULL DEFAULT 'both',
    email_sent BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES post(post_id) ON DELETE SET NULL,
    FOREIGN KEY (schedule_id) REFERENCES scheduled_post(schedule_id) ON DELETE SET NULL,
    INDEX idx_user_unread (user_id, is_read),
    INDEX idx_type (notification_type),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notification_preference (
    preference_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    notification_type ENUM('publish_success', 'publish_failure', 'engagement_alert', 'task_assignment') NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    delivery_method ENUM('email', 'in_app', 'both') DEFAULT 'both',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_type (user_id, notification_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notification_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    notification_id INT NOT NULL,
    delivery_method ENUM('email', 'in_app', 'push') NOT NULL,
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    error_message TEXT NULL,
    sent_at DATETIME NULL,
    FOREIGN KEY (notification_id) REFERENCES notification(notification_id) ON DELETE CASCADE,
    INDEX idx_status (notification_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- Create a simpler view for the frontend
CREATE OR REPLACE VIEW vw_notification_summary AS
SELECT 
    n.notification_id,
    n.user_id,
    CASE 
        WHEN n.notification_type IN ('engagement_alert') THEN 'engagement'
        WHEN n.notification_type IN ('task_assignment') THEN 'team'
        WHEN n.notification_type IN ('publish_success', 'publish_failure') THEN 'system'
        ELSE 'general'
    END AS notification_type,
    n.title,
    n.message,
    n.created_at,
    n.is_read
FROM notification n;

-- ============================================================
-- STORED PROCEDURES
-- ============================================================

DELIMITER //

CREATE PROCEDURE sp_create_publish_success_notification(
    IN p_user_id INT,
    IN p_post_id INT,
    IN p_schedule_id INT,
    IN p_platform_name VARCHAR(50)
)
BEGIN
    DECLARE v_content TEXT;
    DECLARE v_title VARCHAR(255);
    DECLARE v_msg TEXT;
    DECLARE v_method VARCHAR(10);

    SELECT content_text INTO v_content FROM post WHERE post_id = p_post_id;
    SELECT delivery_method INTO v_method
    FROM notification_preference WHERE user_id = p_user_id AND notification_type = 'publish_success' LIMIT 1;
    IF v_method IS NULL THEN SET v_method = 'both'; END IF;

    SET v_title = '✅ Post Published Successfully';
    SET v_msg = CONCAT(
        '<html><body><h3>Post Published!</h3>',
        '<p><strong>', COALESCE(v_content, 'Your post'), '</strong> was published to ', p_platform_name, '.</p>',
        '<p><strong>Time:</strong> ', NOW(), '</p></body></html>'
    );

    INSERT INTO notification (user_id, post_id, schedule_id, notification_type, title, message, sent_via)
    VALUES (p_user_id, p_post_id, p_schedule_id, 'publish_success', v_title, v_msg, v_method);
END //

CREATE PROCEDURE sp_create_publish_failure_notification(
    IN p_user_id INT,
    IN p_post_id INT,
    IN p_schedule_id INT,
    IN p_platform_name VARCHAR(50),
    IN p_reason TEXT
)
BEGIN
    DECLARE v_content TEXT;
    DECLARE v_title VARCHAR(255);
    DECLARE v_msg TEXT;
    DECLARE v_method VARCHAR(10);

    SELECT content_text INTO v_content FROM post WHERE post_id = p_post_id;
    SELECT delivery_method INTO v_method
    FROM notification_preference WHERE user_id = p_user_id AND notification_type = 'publish_failure' LIMIT 1;
    IF v_method IS NULL THEN SET v_method = 'both'; END IF;

    SET v_title = '❌ Post Publishing Failed';
    SET v_msg = CONCAT(
        '<html><body><h3>Publishing Failed</h3>',
        '<p><strong>', COALESCE(v_content, 'Your post'), '</strong> failed to publish to ', p_platform_name, '.</p>',
        '<p><strong>Reason:</strong> ', COALESCE(p_reason, 'Unknown error'), '</p>',
        '<p><strong>Time:</strong> ', NOW(), '</p></body></html>'
    );

    INSERT INTO notification (user_id, post_id, schedule_id, notification_type, title, message, sent_via)
    VALUES (p_user_id, p_post_id, p_schedule_id, 'publish_failure', v_title, v_msg, v_method);
END //

DELIMITER ;

-- ============================================================
-- TRIGGER
-- ============================================================

DROP TRIGGER IF EXISTS trg_scheduled_post_notification;
DELIMITER //
CREATE TRIGGER trg_scheduled_post_notification
AFTER UPDATE ON scheduled_post
FOR EACH ROW
BEGIN
    DECLARE v_user INT;
    DECLARE v_platform VARCHAR(50);
    IF OLD.status <> NEW.status AND (NEW.status = 'published' OR NEW.status = 'failed') THEN
        SELECT p.user_id, plat.platform_name INTO v_user, v_platform
        FROM post p JOIN platform plat ON p.platform_id = plat.platform_id
        WHERE p.post_id = NEW.post_id;
        IF NEW.status = 'published' THEN
            CALL sp_create_publish_success_notification(v_user, NEW.post_id, NEW.schedule_id, v_platform);
        ELSE
            CALL sp_create_publish_failure_notification(v_user, NEW.post_id, NEW.schedule_id, v_platform, NEW.error_message);
        END IF;
    END IF;
END //
DELIMITER ;

-- ============================================================
-- VIEWS
-- ============================================================

CREATE OR REPLACE VIEW vw_user_notification_summary AS
SELECT u.user_id, u.email, u.full_name,
       COUNT(n.notification_id) AS total_notifications,
       SUM(CASE WHEN n.is_read = FALSE THEN 1 ELSE 0 END) AS unread_count,
       MAX(n.created_at) AS last_notification_at
FROM user u
LEFT JOIN notification n ON u.user_id = n.user_id
GROUP BY u.user_id;

CREATE OR REPLACE VIEW vw_recent_notifications AS
SELECT n.notification_id, n.user_id, u.email, u.full_name, n.notification_type,
       n.title, n.message, n.is_read, n.sent_via, n.email_sent, n.created_at,
       p.content_text, plat.platform_name, sp.scheduled_time, sp.published_at
FROM notification n
JOIN user u ON n.user_id = u.user_id
LEFT JOIN post p ON n.post_id = p.post_id
LEFT JOIN scheduled_post sp ON n.schedule_id = sp.schedule_id
LEFT JOIN platform plat ON p.platform_id = plat.platform_id
ORDER BY n.created_at DESC;
