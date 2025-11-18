"""
Notification Microservice - CLEAN FIXED VERSION
Features:
- Handles publish/schedule/fail/approval/team/account events
- IST timestamps everywhere
- Correct platform names
- Clean database inserts
- Clean JSON output for frontend
"""

import os
import smtplib
import traceback
from datetime import datetime, timezone, timedelta
import pytz
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- CONFIG -----------------------------------------------------------------

app = Flask(__name__)
CORS(app)

DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DB", "smms")

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)

IST = timezone(timedelta(hours=5, minutes=30))


# --- DB HELPER ---------------------------------------------------------------

def get_conn():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )


# --- EMAIL (optional) --------------------------------------------------------

def get_user_email(user_id):
    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT full_name, email FROM user WHERE user_id=%s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Exception:
        return None


def send_email_notification(to_email, to_name, subject, message):
    if not EMAIL_ENABLED:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[SMMS] {subject}"
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email

        html = f"""
        <html>
            <body>
                <h3>{subject}</h3>
                <p>{message}</p>
            </body>
        </html>
        """

        msg.attach(MIMEText(message, "plain"))
        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"📧 Email sent to {to_email}")

        return True

    except Exception as e:
        print("❌ Email error:", e)
        return False


# --- MAIN EVENT HANDLER -------------------------------------------------------

@app.route("/api/events/publish", methods=["POST"])
def handle_event():
    """
    Expected JSON:
    {
        "user_id": 1,
        "post_id": 10,
        "schedule_id": null,
        "platform": "LinkedIn",
        "status": "published" | "failed" | ...
        "error_reason": "...",
        "error_message": "...",
        "title": "...",
        "message": "...",
        "notification_type": "system"
    }
    """
    data = request.get_json(force=True) or {}
    print("🔥 Event received:", data)

    # Basic fields
    user_id = data.get("user_id")
    post_id = data.get("post_id")
    schedule_id = data.get("schedule_id")
    platform = (data.get("platform") or "").strip() or "Platform"
    status = data.get("status")
    custom_title = data.get("title")
    custom_message = data.get("message")
    notification_type = data.get("notification_type", "system")

    # Error field normalization
    error_reason = (
        data.get("error_reason") or
        data.get("error_message") or
        ""
    )

    # Timestamp in IST
    ist = pytz.timezone("Asia/Kolkata")
    timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

    if not status:
        return jsonify({"error": "missing status"}), 400
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400

    # --- TITLE LOGIC ---------------------------------------------------------

    if custom_title:
        title = custom_title

    elif status == "published":
        title = f"✅ Post published on {platform}"

    elif status == "failed":
        title = f"❌ Post failed on {platform}"

    elif status == "scheduled":
        title = "📅 Post scheduled"

    elif status == "draft_created":
        title = "📝 Draft saved"

    elif status == "deleted":
        title = "🗑️ Post deleted"

    elif status == "edited":
        title = "✏️ Post updated"

    elif status == "approval_request":
        title = "📋 Approval Required"
        notification_type = "team"

    elif status == "approved":
        title = "✅ Post approved"
        notification_type = "team"

    elif status == "rejected":
        title = "❌ Post rejected"
        notification_type = "team"

    else:
        title = f"🔔 {status.replace('_', ' ').title()}"

    # --- MESSAGE LOGIC --------------------------------------------------------

    if custom_message:
        message = custom_message

    elif status == "published":
        message = (
            f"Your post (ID: {post_id}) was successfully published on {platform} "
            f"at {timestamp} IST."
        )

    elif status == "failed":
        message = (
            f"Your post (ID: {post_id}) failed to publish on {platform}. "
            f"Reason: {error_reason or 'Unknown error'}."
        )

    elif status == "scheduled":
        message = f"Your post (ID: {post_id}) is scheduled for publishing."

    elif status == "draft_created":
        message = f"Draft (ID: {post_id}) saved at {timestamp}."

    elif status == "deleted":
        message = f"Post (ID: {post_id}) deleted."

    elif status == "edited":
        message = f"Post (ID: {post_id}) updated."

    elif status == "approval_request":
        requester = data.get("requester_name", "A team member")
        message = f"{requester} requested your approval for Post ID {post_id}."

    elif status == "approved":
        message = f"Post ID {post_id} was approved."

    elif status == "rejected":
        message = f"Post ID {post_id} was rejected. Reason: {error_reason or 'Not provided'}."

    else:
        message = title

    # --- INSERT INTO DATABASE ----------------------------------------------------

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO notification 
            (user_id, post_id, schedule_id, notification_type,
             title, message, sent_via, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'in_app', FALSE, NOW())
            """,
            (user_id, post_id, schedule_id, notification_type, title, message),
        )

        notif_id = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Notification created (ID {notif_id})")

    except Exception as e:
        print("❌ DB ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    # --- OPTIONAL EMAIL ---------------------------------------------------------

    if EMAIL_ENABLED:
        user = get_user_email(user_id)
        if user and user["email"]:
            send_email_notification(user["email"], user["full_name"], title, message)

    return jsonify({"status": "created", "notification_id": notif_id}), 201


# --- FETCH NOTIFICATIONS --------------------------------------------------------

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "missing user_id"}), 400

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT notification_id, title, message, notification_type,
               is_read, created_at, post_id, schedule_id
        FROM notification
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 200
        """,
        (user_id,),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    # convert datetime to ISO (NO Z, NO UTC)
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()

    counts = {
        "total": len(rows),
        "unread": sum(1 for r in rows if not r["is_read"]),
        "system": sum(1 for r in rows if r["notification_type"] == "system"),
        "team": sum(1 for r in rows if r["notification_type"] == "team"),
    }

    return jsonify({"notifications": rows, "counts": counts}), 200


# --- MARK ALL READ --------------------------------------------------------------

@app.route("/api/notifications/mark-read/<int:user_id>", methods=["PUT"])
def mark_all_read(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE notification SET is_read=TRUE, read_at=NOW() WHERE user_id=%s AND is_read=FALSE",
        (user_id,),
    )
    conn.commit()
    updated = cur.rowcount
    cur.close()
    conn.close()
    return jsonify({"status": "ok", "updated": updated})


# --- HEALTH ---------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "db": DB_NAME}), 200


# --- RUN ------------------------------------------------------------------------

if __name__ == "__main__":
    print("🔔 Starting Notification Microservice on port 5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
