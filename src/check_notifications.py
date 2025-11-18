#!/usr/bin/env python3
"""
Notification System Diagnostic Tool
Run this to check if everything is set up correctly
"""
import sys
import os

print("=" * 60)
print("  NOTIFICATION SYSTEM DIAGNOSTIC")
print("=" * 60)
print()

issues = []
warnings = []

# 1. Check if notification_helper.py exists
print("1. Checking notification_helper.py...")
if os.path.exists('notification_helper.py'):
    print("   ✅ notification_helper.py found")
else:
    print("   ❌ notification_helper.py NOT found!")
    issues.append("notification_helper.py must be in the same directory as app.py")

# 2. Check if notifapp.py exists
print("2. Checking notifapp.py...")
if os.path.exists('notifapp.py'):
    print("   ✅ notifapp.py found")
else:
    print("   ❌ notifapp.py NOT found!")
    issues.append("notifapp.py (notification microservice) not found")

# 3. Try to import notification_helper
print("3. Testing notification_helper import...")
try:
    from notification_helper import notify_post_created
    print("   ✅ notification_helper imports successfully")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    issues.append(f"Cannot import notification_helper: {e}")

# 4. Check if notification microservice is running
print("4. Checking if notification microservice is running on port 5001...")
try:
    import requests
    response = requests.get("http://127.0.0.1:5001/health", timeout=2)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Notification service is running!")
        print(f"      Status: {data.get('status')}")
        print(f"      Database: {data.get('database')}")
    else:
        print(f"   ❌ Service returned status {response.status_code}")
        issues.append("Notification microservice not healthy")
except requests.exceptions.ConnectionError:
    print("   ❌ Cannot connect to notification service!")
    print("      The notification microservice is NOT running!")
    issues.append("notifapp.py is NOT running on port 5001")
except Exception as e:
    print(f"   ❌ Error: {e}")
    issues.append(f"Error connecting to notification service: {e}")

# 5. Check database connection (if service is running)
print("5. Testing notification creation...")
if not any("NOT running" in i for i in issues):
    try:
        import requests
        test_payload = {
            "user_id": 1,
            "post_id": None,
            "status": "test_notification",
            "notification_type": "system"
        }
        response = requests.post(
            "http://127.0.0.1:5001/api/events/publish",
            json=test_payload,
            timeout=5
        )
        if response.status_code == 201:
            print(f"   ✅ Test notification created successfully!")
            data = response.json()
            print(f"      Notification ID: {data.get('notification_id')}")
        else:
            print(f"   ❌ Failed to create notification: {response.text}")
            issues.append(f"Database error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        issues.append(f"Error creating test notification: {e}")
else:
    print("   ⏭️  Skipped (notification service not running)")

# 6. Check if notifications table exists
print("6. Checking notifications database table...")
try:
    import mysql.connector
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "smms")
    )
    cur = conn.cursor()
    cur.execute("SHOW TABLES LIKE 'notification'")
    if cur.fetchone():
        print("   ✅ notification table exists")
        cur.execute("DESCRIBE notification")
        columns = [row[0] for row in cur.fetchall()]
        print(f"      Columns: {', '.join(columns)}")
    else:
        print("   ❌ notification table does NOT exist!")
        issues.append("notification table not found in database")
    cur.close()
    conn.close()
except ImportError:
    print("   ⚠️  mysql-connector-python not installed")
    warnings.append("Cannot check database - mysql-connector-python not installed")
except Exception as e:
    print(f"   ❌ Database error: {e}")
    if "Access denied" in str(e):
        warnings.append("Database credentials may be incorrect")
    else:
        issues.append(f"Database connection error: {e}")

print()
print("=" * 60)
print("  DIAGNOSTIC RESULTS")
print("=" * 60)

if issues:
    print("\n❌ ISSUES FOUND:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    print("\n🔧 HOW TO FIX:")
    if any("NOT running" in i for i in issues):
        print("""
   The notification microservice is not running!
   
   You need to run BOTH services:
   
   Terminal 1:
   $ python notifapp.py
   (This runs the notification service on port 5001)
   
   Terminal 2:
   $ python app.py
   (This runs your main app on port 5000)
   """)
    
    if any("notification table" in i for i in issues):
        print("""
   The notification table doesn't exist in your database!
   
   Run this SQL to create it:
   
   CREATE TABLE notification (
       notification_id INT AUTO_INCREMENT PRIMARY KEY,
       user_id INT NOT NULL,
       post_id INT NULL,
       schedule_id INT NULL,
       notification_type VARCHAR(20) DEFAULT 'system',
       title VARCHAR(255) NOT NULL,
       message TEXT,
       sent_via VARCHAR(20) DEFAULT 'in_app',
       is_read BOOLEAN DEFAULT FALSE,
       read_at DATETIME NULL,
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
   );
   """)
else:
    print("\n✅ All checks passed! Notification system should be working.")

if warnings:
    print("\n⚠️  WARNINGS:")
    for w in warnings:
        print(f"   - {w}")

print()
