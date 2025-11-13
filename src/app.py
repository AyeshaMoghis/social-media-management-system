"""
Social Media Management System - Flask Application
Integrates authentication + social media OAuth connections + post scheduling
"""
# Standard library imports
import os
import secrets
import hashlib
import base64
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import uuid
from werkzeug.utils import secure_filename
import base64, os, hashlib

# Third-party imports
from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import requests

# ---------------------------
# CONFIG & SETUP
# ---------------------------
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Session configuration
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600
app.config['SESSION_TYPE'] = 'filesystem'

# Upload Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webm'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create uploads directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------
# DATABASE CONFIGURATION
# ---------------------------
if os.environ.get('TESTING') == 'true':
    print("🧪 TEST MODE: Using SQLite in-memory database")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
else:
    user = os.getenv('MYSQL_USER', 'root')
    pw = os.getenv('MYSQL_PASSWORD', '')
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    db_name = os.getenv('MYSQL_DB', 'smms')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{pw}@{host}/{db_name}'
    print(f"🚀 Using MySQL database: {db_name}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
dbs = SQLAlchemy(app)

# ---------------------------
# OAUTH CONFIG
# ---------------------------
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI')

TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
TWITTER_REDIRECT_URI = os.getenv('TWITTER_REDIRECT_URI')


# ---------------------------
# DATABASE MODELS
# ---------------------------
class User(dbs.Model):
    __tablename__ = 'user'
    user_id = dbs.Column(dbs.Integer, primary_key=True)
    email = dbs.Column(dbs.String(100), unique=True, nullable=False)
    full_name = dbs.Column(dbs.String(100))
    role = dbs.Column(dbs.String(20), default='user')
    created_at = dbs.Column(dbs.DateTime, default=datetime.utcnow)


class Platform(dbs.Model):
    __tablename__ = 'platform'
    platform_id = dbs.Column(dbs.Integer, primary_key=True)
    platform_name = dbs.Column(dbs.String(50), nullable=False)
    api_endpoint = dbs.Column(dbs.String(255))
    is_active = dbs.Column(dbs.Boolean, default=True)


class LinkedAccount(dbs.Model):
    __tablename__ = 'linked_account'
    account_id = dbs.Column(dbs.Integer, primary_key=True)
    user_id = dbs.Column(dbs.Integer, dbs.ForeignKey('user.user_id'))
    platform_id = dbs.Column(dbs.Integer, dbs.ForeignKey('platform.platform_id'))
    access_token = dbs.Column(dbs.Text)
    refresh_token = dbs.Column(dbs.Text)
    external_id = dbs.Column(dbs.String(255))
    account_username = dbs.Column(dbs.String(100))
    follower_count = dbs.Column(dbs.Integer, default=0)
    post_count = dbs.Column(dbs.Integer, default=0)
    last_synced = dbs.Column(dbs.DateTime, default=datetime.utcnow)
    linked_at = dbs.Column(dbs.DateTime, default=datetime.utcnow)


class OAuthState(dbs.Model):
    __tablename__ = 'oauth_state'
    state_id = dbs.Column(dbs.String(100), primary_key=True)
    user_id = dbs.Column(dbs.Integer, nullable=False)
    platform = dbs.Column(dbs.String(50), nullable=False)
    code_verifier = dbs.Column(dbs.String(200))
    created_at = dbs.Column(dbs.DateTime, default=datetime.utcnow)


class Post(dbs.Model):
    __tablename__ = 'post'
    post_id = dbs.Column(dbs.Integer, primary_key=True)
    user_id = dbs.Column(dbs.Integer, dbs.ForeignKey('user.user_id'), nullable=False)
    content_text = dbs.Column(dbs.Text)
    media_url = dbs.Column(dbs.String(500))
    status = dbs.Column(dbs.Enum('draft', 'pending', 'approved', 'rejected', 'scheduled', 'published', 'failed'))
    created_at = dbs.Column(dbs.DateTime, default=datetime.utcnow)
    updated_at = dbs.Column(dbs.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostPlatform(dbs.Model):
    __tablename__ = 'post_platform'
    id = dbs.Column(dbs.Integer, primary_key=True)
    post_id = dbs.Column(dbs.Integer, dbs.ForeignKey('post.post_id', ondelete='CASCADE'))
    platform_id = dbs.Column(dbs.Integer, dbs.ForeignKey('platform.platform_id', ondelete='CASCADE'))
    platform_post_id = dbs.Column(dbs.String(255))
    published = dbs.Column(dbs.Boolean, default=False)
    error_message = dbs.Column(dbs.Text)
    published_at = dbs.Column(dbs.DateTime)


class ScheduledPost(dbs.Model):
    __tablename__ = 'scheduled_post'
    schedule_id = dbs.Column(dbs.Integer, primary_key=True)
    post_id = dbs.Column(dbs.Integer, dbs.ForeignKey('post.post_id', ondelete='CASCADE'))
    platform_id = dbs.Column(dbs.Integer, dbs.ForeignKey('platform.platform_id', ondelete='CASCADE'))
    scheduled_time = dbs.Column(dbs.DateTime)
    status = dbs.Column(dbs.Enum('scheduled', 'published', 'failed'), default='scheduled')
    published_at = dbs.Column(dbs.DateTime)
    error_message = dbs.Column(dbs.Text)


# ---------------------------
# HELPER FUNCTIONS
# ---------------------------
def current_user():
    """Get current logged-in user from session"""
    user_id = session.get('user_id')
    if user_id:
        return dbs.session.get(User, user_id)
    return None


def cleanup_old_oauth_states():
    """Remove OAuth states older than 10 minutes"""
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    OAuthState.query.filter(OAuthState.created_at < cutoff).delete()
    dbs.session.commit()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'image'
    elif ext in {'mp4', 'mov', 'avi', 'webm'}:
        return 'video'
    return None


def check_and_publish_scheduled_posts():
    """Check for scheduled posts that are past their scheduled time and mark them as published"""
    try:
        # Use local time instead of UTC since scheduled times are in local timezone
        from datetime import datetime as dt
        current_time = dt.now()
        print(f"🕐 Current local time: {current_time}")
        
        # Find all scheduled posts where the scheduled time has passed
        scheduled_posts = ScheduledPost.query.filter(
            ScheduledPost.status == 'scheduled',
            ScheduledPost.scheduled_time <= current_time
        ).all()
        
        print(f"📋 Found {len(scheduled_posts)} scheduled posts to check")
        for sp in scheduled_posts:
            print(f"   - Post {sp.post_id}: scheduled for {sp.scheduled_time}")
        
        published_count = 0
        for sched_post in scheduled_posts:
            # Update the scheduled post status
            sched_post.status = 'published'
            sched_post.published_at = current_time
            
            # Update the main post status
            post = Post.query.get(sched_post.post_id)
            if post:
                post.status = 'published'
                post.updated_at = current_time
            
            # Update the post platform status
            post_platform = PostPlatform.query.filter_by(
                post_id=sched_post.post_id,
                platform_id=sched_post.platform_id
            ).first()
            if post_platform:
                post_platform.published = True
                post_platform.published_at = current_time
            
            published_count += 1
        
        if published_count > 0:
            dbs.session.commit()
            print(f"✅ Auto-published {published_count} scheduled posts")
        
        return published_count
    except Exception as e:
        print(f"❌ Error checking scheduled posts: {e}")
        dbs.session.rollback()
        return 0


# ---------------------------
# IMPORT AUTH BLUEPRINT
# ---------------------------
from src.auth import auth
app.register_blueprint(auth)


# ---------------------------
# MAIN ROUTES
# ---------------------------
@app.route('/')
def home():
    """Landing page - redirects based on login status"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # User is logged in - redirect to their dashboard
    if session.get('role') == 'manager':
        return redirect(url_for('manager_dashboard'))
    else:
        return redirect(url_for('linked_accounts'))


# ---------------------------
# ROLE-BASED DASHBOARDS
# ---------------------------
@app.route('/dashboard/user')
def user_dashboard():
    """User dashboard - redirects to linked accounts"""
    if 'user_id' not in session or session.get('role') != 'user':
        flash("Access denied — Users only.", "danger")
        return redirect(url_for('auth.login'))
    return redirect(url_for('linked_accounts'))


@app.route('/dashboard/manager')
def manager_dashboard():
    """Manager Dashboard Page"""
    if 'user_id' not in session or session.get('role') != 'manager':
        flash("Access denied — Managers only.", "danger")
        return redirect(url_for('auth.login'))
    return render_template('manager_dashboard.html', name=session.get('full_name'))


# ---------------------------
# LINKED ACCOUNTS PAGE
# ---------------------------
@app.route('/linked-accounts')
def linked_accounts():
    """Display all linked social media accounts for current user"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = dbs.session.get(User, user_id)
    
    if not user:
        return redirect(url_for('auth.login'))
    
    accounts = LinkedAccount.query.filter_by(user_id=user.user_id).all()

    account_list = []
    for acc in accounts:
        platform = dbs.session.get(Platform, acc.platform_id)
        platform_name = platform.platform_name if platform else 'Unknown'
        show_stats = platform_name.lower() in ['twitter', 'x']

        account_list.append({
            'account_id': acc.account_id,
            'platform_name': platform_name,
            'account_username': acc.account_username,
            'linked_at': acc.linked_at,
            'follower_count': acc.follower_count,
            'post_count': acc.post_count,
            'is_connected': bool(acc.access_token),
            'last_synced': acc.last_synced,
            'show_stats': show_stats
        })

    return render_template(
        'linked_accounts.html',
        user=user,
        accounts=account_list,
        now=datetime.utcnow()
    )


# ---------------------------
# LINKEDIN AUTH
# ---------------------------
@app.route('/connect/linkedin')
def connect_linkedin():
    """Initiate LinkedIn OAuth flow"""
    if 'user_id' not in session:
        flash("Please log in first", "danger")
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    active_user = dbs.session.get(User, user_id)
    
    if not active_user:
        flash("User not found", "danger")
        return redirect(url_for('auth.login'))
    
    print(f"✅ User {active_user.user_id} starting LinkedIn connection")

    linkedin = Platform.query.filter_by(platform_name='LinkedIn').first()
    if not linkedin:
        linkedin = Platform(
            platform_name='LinkedIn',
            api_endpoint='https://api.linkedin.com/v2/ugcPosts'
        )
        dbs.session.add(linkedin)
        dbs.session.commit()

    state = secrets.token_urlsafe(32)

    oauth_state = OAuthState(
        state_id=state,
        user_id=active_user.user_id,
        platform='linkedin'
    )
    dbs.session.add(oauth_state)
    dbs.session.commit()

    cleanup_old_oauth_states()

    # ✅ FIXED: Request correct scopes for posting
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        "?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
        "&scope=openid%20profile%20email%20w_member_social"  # ✅ Added openid for profile access
        f"&state={state}"
    )

    return redirect(auth_url)


@app.route('/callback/linkedin')
def linkedin_callback():
    from datetime import datetime
    try:
        code = request.args.get("code")
        state = request.args.get("state")

        print("DEBUG: Entered NEW linkedin callback")

        # TEST EXPECTATION 1:
        # Missing BOTH code AND state -> "missing parameters"
        if not code and not state:
            return "missing parameters", 400

        # TEST EXPECTATION 2:
        # Missing code only -> "Missing authorization code"
        if not code:
            return "Missing authorization code", 400

        # State must exist in DB
        oauth_state = OAuthState.query.filter_by(state_id=state).first()
        if not oauth_state:
            return "Invalid OAuth state", 400

        # Exchange code for token
        token_resp = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET
            },
            timeout=10
        )

        token_data = token_resp.json()

        # TEST EXPECTATION 3:
        # Missing token -> "Failed to get access token"
        if "access_token" not in token_data:
            return "Failed to get access token", 400

        access_token = token_data["access_token"]

        # Fetch profile
        profile_resp = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )

        profile_data = profile_resp.json()

        external_id = profile_data.get("sub")
        name = profile_data.get("name", "LinkedIn User")

        if not external_id:
            return "Failed to fetch profile", 400

        user_id = session.get("user_id")

        # Get or create platform
        platform = Platform.query.filter_by(platform_name="LinkedIn").first()
        if not platform:
            platform = Platform(platform_name="LinkedIn")
            dbs.session.add(platform)
            dbs.session.commit()

        # Update or create LinkedAccount
        acc = LinkedAccount.query.filter_by(
            user_id=user_id,
            platform_id=platform.platform_id
        ).first()

        if not acc:
            acc = LinkedAccount(
                user_id=user_id,
                platform_id=platform.platform_id,
                linked_at=datetime.utcnow()
            )
            dbs.session.add(acc)

        acc.account_username = name
        acc.access_token = access_token
        acc.external_id = external_id
        acc.last_synced = datetime.utcnow()

        # TEST EXPECTATION 4:
        # Must delete oauth state
        dbs.session.delete(oauth_state)

        dbs.session.commit()

        # TEST EXPECTATION 5:
        # Must redirect on success
        return redirect("/linked-accounts")

    except Exception as e:
        print("LinkedIn callback error:", e)
        dbs.session.rollback()
        return str(e), 500

# ---------------------------
# TWITTER AUTH
# ---------------------------
@app.route('/connect/twitter')
def connect_twitter():
    try:
        print(f"✅ User {session.get('user_id')} starting Twitter connection")

        # Ensure Twitter platform exists (unit test requires this)
        with app.app_context():
            twitter_platform = Platform.query.filter_by(platform_name="Twitter").first()
            if not twitter_platform:
                twitter_platform = Platform(
                    platform_name="Twitter",
                    api_endpoint="https://api.twitter.com/2"
                )
                dbs.session.add(twitter_platform)
                dbs.session.commit()

        # Step 1: Generate PKCE verifier and challenge
        code_verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b'=').decode('utf-8')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).rstrip(b'=').decode('utf-8')

        session['twitter_code_verifier'] = code_verifier

        # Step 3: Generate state
        import secrets
        state = secrets.token_urlsafe(32)
        session['twitter_state'] = state

        auth_url = (
            "https://twitter.com/i/oauth2/authorize?"
            f"response_type=code&client_id={TWITTER_CLIENT_ID}"
            "&redirect_uri=http%3A%2F%2F127.0.0.1%3A5000%2Fcallback%2Ftwitter"
            "&scope=tweet.read%20tweet.write%20users.read%20offline.access"
            f"&state={state}&code_challenge={code_challenge}&code_challenge_method=S256"
        )

        return redirect(auth_url)

    except Exception as e:
        print("Error initiating Twitter connection:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/callback/twitter')
def callback_twitter():
    try:
        state = request.args.get('state')
        code = request.args.get('code')

        if not state or not code:
            return jsonify({"error": "Missing state or code"}), 400

        # Verify state
        saved_state = session.get('twitter_state')
        if not saved_state or saved_state != state:
            return jsonify({"error": "Invalid OAuth state"}), 400

        # Retrieve verifier
        code_verifier = session.get('twitter_code_verifier')
        if not code_verifier:
            return jsonify({"error": "Missing code_verifier"}), 400

        # Exchange code for access token
        token_url = "https://api.twitter.com/2/oauth2/token"
        auth_str = f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()

        payload = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "http://127.0.0.1:5000/callback/twitter",
            "code_verifier": code_verifier,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_b64}",
        }

        token_resp = requests.post(token_url, data=payload, headers=headers, timeout=10)
        token_data = token_resp.json()
        print("Twitter token response:", token_data)

        if "access_token" not in token_data:
            return jsonify({"error": "Failed to get Twitter access token"}), 400

        access_token = token_data["access_token"]

        # Get user info from Twitter
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_resp = requests.get("https://api.twitter.com/2/users/me", headers=headers, timeout=10)
        profile_data = profile_resp.json()
        print("Twitter /me response:", profile_data)

        external_id = profile_data.get("data", {}).get("id")
        username = profile_data.get("data", {}).get("username", "Unknown")

        if not external_id:
            return jsonify({"error": "Failed to fetch Twitter profile"}), 400

        # Save in DB
        user_id = session.get("user_id")

        # Get or create Twitter platform dynamically
        twitter_platform = Platform.query.filter_by(platform_name="Twitter").first()
        if not twitter_platform:
            twitter_platform = Platform(platform_name="Twitter")
            dbs.session.add(twitter_platform)
            dbs.session.commit()

        platform_id = twitter_platform.platform_id  # DYNAMIC ID

        # Check if user already linked this platform
        existing = LinkedAccount.query.filter_by(
            user_id=user_id,
            platform_id=platform_id
        ).first()

        if existing:
            # Update existing entry
            existing.account_username = f"@{username}"
            existing.access_token = access_token
            existing.refresh_token = token_data.get("refresh_token")
            existing.external_id = external_id
            existing.linked_at = datetime.utcnow()
        else:
            # Create new linked account
            new_acc = LinkedAccount(
                user_id=user_id,
                platform_id=platform_id,   # FIXED — NO HARD-CODED “3”
                account_username=f"@{username}",
                access_token=access_token,
                refresh_token=token_data.get("refresh_token"),
                external_id=external_id,
                linked_at=datetime.utcnow(),
            )
            dbs.session.add(new_acc)

        dbs.session.commit()
        print(f"✅ Twitter account linked for user {user_id}: @{username} (ID: {external_id})")

        return redirect("/linked-accounts")

    except Exception as e:
        print("Twitter callback error:", e)
        dbs.session.rollback()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# ACCOUNT MANAGEMENT
# ---------------------------
@app.route('/refresh-account/<int:account_id>')
def refresh_account(account_id):
    """Refresh account data from social media platform"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    acc = LinkedAccount.query.filter_by(
        account_id=account_id,
        user_id=user_id
    ).first()

    if not acc or not acc.access_token:
        return redirect(url_for('linked_accounts'))

    platform = dbs.session.get(Platform, acc.platform_id)

    try:
        if platform.platform_name.lower() == "linkedin":
            profile_response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {acc.access_token}"},
                timeout=10
            )

            if profile_response.status_code == 200:
                profile = profile_response.json()
                given = profile.get('given_name', '')
                family = profile.get('family_name', '')
                name = profile.get("name") or f"{given} {family}".strip()
                acc.account_username = name or "LinkedIn User"
                acc.last_synced = datetime.utcnow()
                dbs.session.commit()
                print(f"✅ Refreshed LinkedIn: {acc.account_username}")

        elif platform.platform_name.lower() == "twitter":
            headers = {"Authorization": f"Bearer {acc.access_token}"}
            user_response = requests.get(
                "https://api.twitter.com/2/users/me",
                headers=headers,
                params={"user.fields": "public_metrics,username,name"},
                timeout=10
            )

            if user_response.status_code == 200:
                user_data = user_response.json().get("data", {})
                username = user_data.get("username", "Unknown")
                name = user_data.get("name", "Twitter User")
                metrics = user_data.get("public_metrics", {})

                acc.account_username = f"{name} (@{username})"
                acc.follower_count = metrics.get("followers_count", 0)
                acc.post_count = metrics.get("tweet_count", 0)
                acc.last_synced = datetime.utcnow()
                dbs.session.commit()
                print(f"✅ Refreshed Twitter: {acc.account_username}")
            else:
                print(f"⚠️ Twitter refresh failed: {user_response.text}")

    except requests.RequestException as error:
        print(f"❌ Refresh error: {error}")

    return redirect(url_for("linked_accounts"))


@app.route('/disconnect-account/<int:account_id>')
def disconnect_account(account_id):
    """Disconnect and remove a linked account"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    acc = LinkedAccount.query.filter_by(
        account_id=account_id,
        user_id=user_id
    ).first()

    if acc:
        dbs.session.delete(acc)
        dbs.session.commit()
        print(f"✅ Disconnected account {account_id}")
        flash("Account disconnected successfully", "success")

    return redirect(url_for('linked_accounts'))


@app.route('/account-details/<int:account_id>')
def account_details(account_id):
    """Display detailed information for a linked account"""
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    acc = LinkedAccount.query.filter_by(
        account_id=account_id,
        user_id=user_id
    ).first()

    if not acc:
        flash("Account not found.", "danger")
        return redirect(url_for('linked_accounts'))

    platform = dbs.session.get(Platform, acc.platform_id)
    active_user = dbs.session.get(User, user_id)

    details = {
        'account_id': acc.account_id,
        'platform_name': platform.platform_name if platform else 'Unknown',
        'account_username': acc.account_username,
        'linked_at': acc.linked_at,
        'follower_count': acc.follower_count,
        'post_count': acc.post_count,
        'has_token': bool(acc.access_token)
    }

    return render_template('account_details.html', account=details, user=active_user)


# ---------------------------
# POST SCHEDULER ROUTES
# ---------------------------
@app.route('/post-scheduler')
def post_scheduler():
    """Post scheduler page - renamed from create_schedule_posts"""
    if 'user_id' not in session:
        flash("Please log in first", "warning")
        return redirect(url_for('auth.login'))
    
    user = current_user()
    
    # Get user's linked accounts
    accounts = LinkedAccount.query.filter_by(user_id=user.user_id).all()
    
    account_list = []
    for acc in accounts:
        platform = dbs.session.get(Platform, acc.platform_id)
        if platform and acc.access_token:
            account_list.append({
                'account_id': acc.account_id,
                'platform_name': platform.platform_name,
                'account_username': acc.account_username,
                'platform_id': acc.platform_id
            })
    
    # If no accounts linked, redirect to linked accounts page
    if not account_list:
        flash("Please connect at least one social media account first", "warning")
        return redirect(url_for('linked_accounts'))
    
    return render_template('create_schedule_posts.html', user=user, accounts=account_list)


@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Get all posts for current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Check and update scheduled posts that should be published
        check_and_publish_scheduled_posts()
        
        user_id = session['user_id']
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)

        # Get posts for this user
        query = Post.query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)

        posts = query.order_by(Post.created_at.desc()).limit(limit).all()

        posts_list = []
        for post in posts:
            platforms = PostPlatform.query.filter_by(post_id=post.post_id).all()
            platform_data = []
            for pp in platforms:
                platform = dbs.session.get(Platform, pp.platform_id)
                platform_data.append({
                    'platform_name': platform.platform_name if platform else 'Unknown',
                    'published': pp.published,
                    'published_at': pp.published_at.strftime('%Y-%m-%d %H:%M:%S') if pp.published_at else None
                })
            
            print(f"📱 Post {post.post_id} platforms: {[p['platform_name'] for p in platform_data]}")
            
            # Get scheduled time if post is scheduled
            scheduled_time = None
            if post.status == 'scheduled':
                scheduled_post = ScheduledPost.query.filter_by(post_id=post.post_id).first()
                if scheduled_post and scheduled_post.scheduled_time:
                    scheduled_time = scheduled_post.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')

            posts_list.append({
                'id': post.post_id,
                'text': post.content_text,
                'media_url': post.media_url,
                'status': post.status,
                'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': post.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'scheduled_time': scheduled_time,
                'platforms': platform_data
            })

        return jsonify(posts_list), 200

    except Exception as e:
        print(f"Error getting posts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        text = request.form.get('text', '')
        account_ids = request.form.getlist('account_ids[]')
        scheduled_time = request.form.get('scheduled_time')
        status = request.form.get('status', 'draft')
        
        # Debug logging
        print(f"📝 Creating post - Status received: '{status}', Scheduled time: '{scheduled_time}'")
        print(f"📝 Account IDs: {account_ids}")

        media_file = request.files.get('media')
        if not text and not media_file:
            return jsonify({'error': 'Post must contain text or media'}), 400
        if not account_ids:
            return jsonify({'error': 'At least one account must be selected'}), 400

        # Handle file upload
        media_url = None
        if media_file and media_file.filename:
            if allowed_file(media_file.filename):
                file_ext = media_file.filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}.{file_ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                media_file.save(file_path)
                media_url = file_path
            else:
                return jsonify({'error': 'Invalid file type'}), 400

        # Parse schedule time
        scheduled_dt = None
        if scheduled_time:
            try:
                scheduled_dt = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                return jsonify({'error': 'Invalid scheduled time format'}), 400

        # Determine status based on what was sent from frontend
        # Frontend sends: 'draft', 'published', or 'scheduled'
        if status == 'published':
            final_status = 'published'
        elif status == 'scheduled' or scheduled_dt:
            final_status = 'scheduled'
        else:
            final_status = 'draft'
        
        print(f"✅ Final status determined: '{final_status}'")

        # Create post
        post = Post(
            user_id=user_id,
            content_text=text,
            media_url=media_url,
            status=final_status
        )
        dbs.session.add(post)
        dbs.session.flush()

        # Link platforms
        for account_id in account_ids:
            account = LinkedAccount.query.get(account_id)
            if account and account.user_id == user_id:
                pp = PostPlatform(
                    post_id=post.post_id,
                    platform_id=account.platform_id
                )
                dbs.session.add(pp)

                # Create schedule if scheduled
                if scheduled_dt and final_status == 'scheduled':
                    from datetime import datetime as dt
                    print(f"📅 Creating scheduled post for {scheduled_dt} (Current local time: {dt.now()})")
                    sched = ScheduledPost(
                        post_id=post.post_id,
                        platform_id=account.platform_id,
                        scheduled_time=scheduled_dt
                    )
                    dbs.session.add(sched)

        dbs.session.commit()

        # If status is 'published', actually publish to the platforms NOW
        if final_status == 'published':
            print(f"🚀 Publishing post {post.post_id} to platforms immediately...")
            for account_id in account_ids:
                account = LinkedAccount.query.get(account_id)
                if account and account.user_id == user_id:
                    success, result = publish_to_platform(post, account)
                    
                    # Update PostPlatform with result
                    pp = PostPlatform.query.filter_by(
                        post_id=post.post_id,
                        platform_id=account.platform_id
                    ).first()
                    
                    if pp:
                        if success:
                            pp.published = True
                            pp.published_at = datetime.now()
                            pp.platform_post_id = result
                            print(f"✅ Published to {account.platform_id}: {result}")
                        else:
                            pp.published = False
                            pp.error_message = result
                            print(f"❌ Failed to publish to {account.platform_id}: {result}")
            
            dbs.session.commit()

        return jsonify({
            'message': 'Post created successfully',
            'post_id': post.post_id
        }), 201

    except Exception as e:
        dbs.session.rollback()
        print(f"Error creating post: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    """Update an existing post — also reflects updates on Twitter"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        post = Post.query.filter_by(post_id=post_id, user_id=user_id).first()
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        new_text = request.form.get('text')
        status = request.form.get('status', post.status)
        scheduled_time = request.form.get('scheduled_time')

        print(f"📝 Updating post {post_id} - Status: {status}, Scheduled: {scheduled_time}")

        # Update post content
        if new_text is not None:
            post.content_text = new_text

        # If post is published — update on Twitter (LinkedIn doesn't support edit)
        if status == 'published':
            post.status = 'published'

            # Get all linked platforms for this post
            linked_platforms = PostPlatform.query.filter_by(post_id=post.post_id).all()

            for pp in linked_platforms:
                platform = dbs.session.get(Platform, pp.platform_id)
                account = LinkedAccount.query.filter_by(user_id=user_id, platform_id=platform.platform_id).first()

                if platform and platform.platform_name.lower() in ['twitter', 'x']:
                    # If tweet exists, delete it first
                    if pp.platform_post_id:
                        print(f"🗑️ Deleting existing tweet {pp.platform_post_id} before reposting...")
                        headers = {"Authorization": f"Bearer {account.access_token}"}
                        delete_url = f"https://api.twitter.com/2/tweets/{pp.platform_post_id}"
                        delete_resp = requests.delete(delete_url, headers=headers, timeout=10)
                        print(f"🗑️ Delete response: {delete_resp.status_code} - {delete_resp.text}")

                    # Repost updated tweet
                    headers = {
                        "Authorization": f"Bearer {account.access_token}",
                        "Content-Type": "application/json"
                    }
                    payload = {"text": post.content_text}
                    post_resp = requests.post("https://api.twitter.com/2/tweets", headers=headers, json=payload, timeout=10)

                    if post_resp.status_code == 201:
                        new_tweet_data = post_resp.json()
                        new_tweet_id = new_tweet_data.get("data", {}).get("id")
                        pp.platform_post_id = new_tweet_id
                        pp.published = True
                        pp.published_at = datetime.now()
                        print(f"✅ Updated tweet posted successfully: {new_tweet_id}")
                    else:
                        pp.error_message = post_resp.text
                        print(f"❌ Failed to repost updated tweet: {post_resp.text}")
                
                elif platform and platform.platform_name.lower() == 'linkedin':
                    # ⚠️ LinkedIn API doesn't support editing posts
                    print(f"⚠️ LinkedIn doesn't support editing posts via API. Post ID: {pp.platform_post_id}")
                    pp.error_message = "LinkedIn doesn't support editing posts via API"

        elif status == 'scheduled' and scheduled_time:
            try:
                scheduled_dt = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
                post.status = 'scheduled'
                sched = ScheduledPost.query.filter_by(post_id=post.post_id).first()
                if sched:
                    sched.scheduled_time = scheduled_dt
                else:
                    platform_id = PostPlatform.query.filter_by(post_id=post.post_id).first().platform_id
                    dbs.session.add(ScheduledPost(post_id=post.post_id, platform_id=platform_id, scheduled_time=scheduled_dt))
            except ValueError:
                return jsonify({'error': 'Invalid scheduled time format'}), 400

        elif status == 'draft':
            post.status = 'draft'
            ScheduledPost.query.filter_by(post_id=post.post_id).delete()

        post.updated_at = datetime.now()
        dbs.session.commit()

        print(f"✅ Post {post_id} updated successfully")
        return jsonify({'message': 'Post updated successfully'}), 200

    except Exception as e:
        dbs.session.rollback()
        print(f"❌ Error updating post: {e}")
        return jsonify({'error': str(e)}), 500

def delete_tweet(account, tweet_id):
    """Delete a tweet on Twitter using tweet_id"""
    try:
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json"
        }
        delete_url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        response = requests.delete(delete_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"🗑️ Successfully deleted Tweet {tweet_id}")
            return True
        else:
            print(f"⚠️ Failed to delete Tweet {tweet_id}: {response.status_code} - {response.text}")
            # Try token refresh if unauthorized
            if response.status_code == 401:
                print("⚠️ Access token expired, refreshing before delete...")
                new_token = refresh_twitter_token(account)
                if new_token:
                    headers["Authorization"] = f"Bearer {new_token}"
                    response = requests.delete(delete_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        print(f"🗑️ Successfully deleted Tweet {tweet_id} after refresh")
                        return True
            return False
    except Exception as e:
        print(f"❌ Error deleting tweet: {e}")
        return False


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """Delete a post (both locally and from connected platforms where supported)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        post = Post.query.filter_by(post_id=post_id, user_id=user_id).first()

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # ✅ Delete from platforms where supported
        linked_platforms = PostPlatform.query.filter_by(post_id=post.post_id).all()
        for pp in linked_platforms:
            platform = dbs.session.get(Platform, pp.platform_id)
            account = LinkedAccount.query.filter_by(user_id=user_id, platform_id=platform.platform_id).first()

            if platform.platform_name.lower() in ['twitter', 'x'] and pp.platform_post_id:
                print(f"🗑️ Deleting tweet {pp.platform_post_id} from Twitter...")
                delete_tweet(account, pp.platform_post_id)
            
            elif platform.platform_name.lower() == 'linkedin':
                # ⚠️ LinkedIn API doesn't support deleting posts
                print(f"⚠️ LinkedIn doesn't support deleting posts via API. Post ID: {pp.platform_post_id}")
                print(f"ℹ️ Users must manually delete the post from LinkedIn: https://www.linkedin.com")

        # ✅ Delete media file locally
        if post.media_url and os.path.exists(post.media_url):
            os.remove(post.media_url)

        # ✅ Delete from DB
        ScheduledPost.query.filter_by(post_id=post.post_id).delete()
        PostPlatform.query.filter_by(post_id=post.post_id).delete()
        dbs.session.delete(post)
        dbs.session.commit()

        print(f"✅ Deleted post {post_id} locally and from supported platforms")
        return jsonify({
            'message': 'Post deleted successfully',
            'note': 'LinkedIn posts must be deleted manually from LinkedIn.com (API limitation)'
        }), 200

    except Exception as e:
        dbs.session.rollback()
        print(f"❌ Error deleting post: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
def refresh_twitter_token(account):
    """Refresh expired Twitter OAuth2 token automatically."""
    try:
        token_url = "https://api.twitter.com/2/oauth2/token"

        # Encode client ID and secret as Basic auth header
        auth_str = f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_b64}"
        }

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": account.refresh_token,
            "client_id": TWITTER_CLIENT_ID
        }

        response = requests.post(token_url, data=payload, headers=headers, timeout=10)
        data = response.json()
        print("🔁 Token refresh response:", data)

        if response.status_code == 200 and "access_token" in data:
            account.access_token = data["access_token"]
            if "refresh_token" in data:
                account.refresh_token = data["refresh_token"]
            account.last_synced = datetime.utcnow()
            dbs.session.commit()
            print("✅ Twitter token refreshed successfully")
            return account.access_token
        else:
            print("⚠️ Token refresh failed:", data)
            return None

    except Exception as e:
        print(f"❌ Token refresh error: {e}")
        return None




def publish_to_twitter(post, account):
    """Publish a post to Twitter/X"""
    try:
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json"
        }
        payload = {"text": post.content_text}

        response = requests.post(
            "https://api.twitter.com/2/tweets",
            headers=headers,
            json=payload,
            timeout=10
        )

        # ✅ Handle expired token
        if response.status_code == 401:
            print("⚠️ Access token expired, refreshing...")
            new_token = refresh_twitter_token(account)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.post(
                    "https://api.twitter.com/2/tweets",
                    headers=headers,
                    json=payload,
                    timeout=10
                )

        if response.status_code == 201:
            tweet_data = response.json()
            tweet_id = tweet_data.get('data', {}).get('id')
            print(f"✅ Published to Twitter: Tweet ID {tweet_id}")
            return True, tweet_id
        else:
            error_msg = response.json().get('detail', response.text)
            print(f"❌ Twitter publish failed: {error_msg}")
            return False, error_msg

    except Exception as e:
        print(f"❌ Twitter publish error: {e}")
        return False, str(e)


def publish_to_linkedin(post, account):
    """Publish a post to LinkedIn using OpenID and w_member_social scope."""
    try:
        if not account.access_token:
            return False, "No access token for LinkedIn account"

        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "Accept": "application/json"
        }

        # ✅ FIXED: Use external_id (sub from OpenID) directly as the author
        # Format: urn:li:person:{sub_value}
        author_urn = f"urn:li:person:{account.external_id}"
        print(f"🔵 LinkedIn: Using author URN: {author_urn}")

        # ✅ Build the UGC post payload
        post_payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post.content_text or ""
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        print(f"🔵 LinkedIn: Posting with payload: {json.dumps(post_payload, indent=2)}")

        # ✅ Make POST request to LinkedIn UGC API
        post_resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=post_payload,
            timeout=10
        )

        print(f"🔵 LinkedIn: Response status: {post_resp.status_code}")
        print(f"🔵 LinkedIn: Response body: {post_resp.text}")
        print(f"🔵 LinkedIn: Response headers: {dict(post_resp.headers)}")

        if post_resp.status_code in (200, 201):
            # Extract post ID from response
            try:
                data = post_resp.json()
                post_id = data.get("id")
            except Exception:
                post_id = None
            
            # Try getting from headers if not in body
            if not post_id:
                post_id = (post_resp.headers.get("x-restli-id") or 
                          post_resp.headers.get("Location") or 
                          "unknown")

            print(f"✅ Published to LinkedIn: Post ID {post_id}")
            return True, str(post_id)

        else:
            error_msg = f"{post_resp.status_code}: {post_resp.text}"
            print(f"❌ LinkedIn publish failed: {error_msg}")
            return False, error_msg

    except Exception as e:
        print(f"❌ LinkedIn publish error: {e}")
        return False, str(e)


def publish_to_platform(post, account):
    """
    Publish post to a specific platform
    Returns: (success: bool, platform_post_id_or_error: str)
    """
    try:
        platform = dbs.session.get(Platform, account.platform_id)
        
        if platform.platform_name.lower() == 'twitter' or platform.platform_name.lower() == 'x':
            return publish_to_twitter(post, account)
            
        elif platform.platform_name.lower() == 'linkedin':
            return publish_to_linkedin(post, account)
        
        else:
            return False, f"Platform {platform.platform_name} not supported for publishing yet"
        
    except Exception as e:
        print(f"❌ Error publishing to platform: {e}")
        return False, str(e)


# ---------------------------
# ERROR HANDLERS
# ---------------------------
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    dbs.session.rollback()
    return render_template('500.html'), 500



# ---------------------------
# RUN SERVER
# ---------------------------
if __name__ == '__main__':
    with app.app_context():
        dbs.create_all()
        print("✅ Database tables created")
    app.run(debug=True)