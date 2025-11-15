"""
Social Media Management System - Flask Application
Integrates authentication + social media OAuth connections
"""
# Standard library imports
import os
import secrets
import hashlib
import base64
import json
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Third-party imports
from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

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
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # 24 hours
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
    print("TEST MODE: Using SQLite in-memory database")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
else:
    from urllib.parse import quote_plus
    user = os.getenv('MYSQL_USER', 'root')
    pw = os.getenv('MYSQL_PASSWORD', '')
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    db_name = os.getenv('MYSQL_DB', 'smms')
    # URL-encode the password to handle special characters
    encoded_pw = quote_plus(pw) if pw else ''
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{encoded_pw}@{host}/{db_name}'
    print(f"Using MySQL database: {db_name}")

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
    password_hash = dbs.Column(dbs.String(255))
    full_name = dbs.Column(dbs.String(100))
    role = dbs.Column(dbs.String(20), default='user')
    created_at = dbs.Column(dbs.DateTime, default=datetime.utcnow)


class Platform(dbs.Model):
    __tablename__ = 'platform'
    platform_id = dbs.Column(dbs.Integer, primary_key=True)
    # NOTE: this model is used both to store platform types (LinkedIn/Twitter)
    # and user-specific linked accounts in tests. Keep both sets of fields
    # so tests can create platforms with or without a user association.
    platform_name = dbs.Column(dbs.String(50), nullable=False)
    api_endpoint = dbs.Column(dbs.String(255))
    is_active = dbs.Column(dbs.Boolean, default=True)

    # Optional user-specific fields (when this row represents a linked account)
    user_id = dbs.Column(dbs.Integer, dbs.ForeignKey('user.user_id'), nullable=True)
    platform_user_id = dbs.Column(dbs.String(255))
    access_token = dbs.Column(dbs.Text)
    refresh_token = dbs.Column(dbs.Text)
    expires_at = dbs.Column(dbs.DateTime)
    account_username = dbs.Column(dbs.String(100))
    follower_count = dbs.Column(dbs.Integer, default=0)
    post_count = dbs.Column(dbs.Integer, default=0)


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
    # Tests construct OAuthState using `state_token` keyword, make that the
    # primary key to match expectations.
    state_token = dbs.Column(dbs.String(100), primary_key=True)
    user_id = dbs.Column(dbs.Integer, dbs.ForeignKey('user.user_id'), nullable=False)
    platform = dbs.Column(dbs.String(50), nullable=False)
    code_verifier = dbs.Column(dbs.String(200))
    created_at = dbs.Column(dbs.DateTime, default=datetime.utcnow)
    
    def __init__(self, *args, **kwargs):
        # Accept either 'state_token' or legacy 'state_id' from tests/older code
        if 'state_id' in kwargs and 'state_token' not in kwargs:
            kwargs['state_token'] = kwargs.pop('state_id')
        super().__init__(*args, **kwargs)
    
    @property
    def state_id(self):
        """Backward compatibility property for tests accessing state_id"""
        return self.state_token


class Post(dbs.Model):
    __tablename__ = 'post'
    post_id = dbs.Column(dbs.Integer, primary_key=True)
    user_id = dbs.Column(dbs.Integer, dbs.ForeignKey('user.user_id'), nullable=False)
    content_text = dbs.Column(dbs.Text)
    media_url = dbs.Column(dbs.String(500))
    status = dbs.Column(dbs.Enum('draft', 'pending', 'approved', 'rejected', 'scheduled', 'published', 'failed'), default='draft')
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
    status = dbs.Column(dbs.Enum('pending', 'scheduled', 'published', 'failed'), default='scheduled')
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
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    """Get file type (image/video)"""
    if '.' not in filename:
        return 'unknown'
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'image'
    elif ext in {'mp4', 'mov', 'avi', 'webm'}:
        return 'video'
    return 'unknown'


# ---------------------------
# PLATFORM PUBLISHING FUNCTIONS
# ---------------------------
def publish_to_linkedin(post, account):
    """Publish a post to LinkedIn.

    This function supports two call signatures for backward compatibility with tests:
    - publish_to_linkedin(post_obj, account_obj) -> returns (success: bool, result: str)
    - publish_to_linkedin(platform_id, content_str) -> returns result_str_or_None
    """
    try:
        # If caller passed a platform id and content string, normalize to objects
        id_mode = False
        if isinstance(post, (int,)) and isinstance(account, (str,)):
            platform_id = post
            content = account
            account = dbs.session.get(Platform, platform_id)
            id_mode = True
            if account is None:
                # Non-existent platform
                return None
            # create a minimal post-like object
            class _TmpPost:
                def __init__(self, content_text):
                    self.content_text = content_text
                    self.media_url = None
            post = _TmpPost(content)

        # account should now be an object with access_token
        print(f" Publishing to LinkedIn for account {getattr(account, 'account_id', getattr(account, 'platform_id', None))}")
        
        # Prepare headers for API calls
        headers = {
            "Authorization": f"Bearer {getattr(account, 'access_token', None)}",
            "Content-Type": "application/json"
        }

        # Determine the LinkedIn user ID.
        # Prefer stored platform_user_id (created during OAuth flow). If not set,
        # fall back to fetching profile via LinkedIn API.
        linkedin_id = getattr(account, 'platform_user_id', None)
        if not linkedin_id:
            # Get user info
            profile_response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=10
            )
            if profile_response.status_code != 200:
                error_msg = f"Failed to get LinkedIn user info: {profile_response.status_code}"
                print(f" {error_msg}")
                return False, error_msg
            user_info = profile_response.json()
            linkedin_id = user_info.get('sub')
            if not linkedin_id:
                print(" LinkedIn user ID not found")
                return False, "LinkedIn user ID not found"
        print(f" Got LinkedIn ID: {linkedin_id}")
        
        # Construct the post payload
        post_payload = {
            "author": f"urn:li:person:{linkedin_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post.content_text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # TODO: Add media support for LinkedIn
        # if post.media_url:
        #     # Upload media and attach to post
        #     pass
        
        print(f" Sending post to LinkedIn API...")
        # Post to LinkedIn
        post_response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=post_payload,
            timeout=10
        )
        
        if post_response.status_code == 201:
            post_data = post_response.json()
            linkedin_post_id = post_data.get('id', 'unknown')
            print(f" Successfully published to LinkedIn! Post ID: {linkedin_post_id}")
            return linkedin_post_id if id_mode else (True, linkedin_post_id)
        else:
            error_msg = f"Status {post_response.status_code}: {post_response.text}"
            print(f" LinkedIn publish failed: {error_msg}")
            return None if id_mode else (False, error_msg)
            
    except requests.exceptions.Timeout:
        error_msg = "LinkedIn API request timed out"
        print(f" {error_msg}")
        return None if id_mode else (False, error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"LinkedIn API request failed: {str(e)}"
        print(f" {error_msg}")
        return None if id_mode else (False, error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f" LinkedIn publish error: {error_msg}")
        return None if id_mode else (False, error_msg)


def publish_to_twitter(post, account):
    """Publish a post to Twitter/X using API v2 with media support"""
    try:
        # Support same flexible call signatures as publish_to_linkedin
        id_mode = False
        if isinstance(post, (int,)) and isinstance(account, (str,)):
            platform_id = post
            content = account
            account = dbs.session.get(Platform, platform_id)
            id_mode = True
            if account is None:
                return None
            class _TmpPost:
                def __init__(self, content_text):
                    self.content_text = content_text
                    self.media_url = None
            post = _TmpPost(content)

        print(f" Publishing to Twitter for account {getattr(account, 'account_id', getattr(account, 'platform_id', None))}")
        
        if not account.access_token:
            error_msg = "No access token for Twitter account"
            print(f" {error_msg}")
            return False, error_msg
        
        # Note: Twitter media upload with OAuth 2.0 is limited
        # Media uploads work best with OAuth 1.0a or Enterprise API access
        # For now, we'll post text-only
        
        if post.media_url:
            print(f"  Note: Twitter image upload with OAuth 2.0 is not supported in free tier")
            print(f"    Posting text only. To enable images, upgrade to Twitter API Pro.")
        
        # Twitter API v2 endpoint for creating tweet
        url = "https://api.twitter.com/2/tweets"
        
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare tweet data
        tweet_data = {
            "text": post.content_text or ""
        }
        
        # Make the API request
        print(f" Sending tweet to Twitter API...")
        response = requests.post(url, headers=headers, json=tweet_data, timeout=10)
        
        if response.status_code == 201:
            # Success
            tweet_response = response.json()
            tweet_id = tweet_response.get('data', {}).get('id', 'unknown')
            print(f" Successfully published to Twitter! Tweet ID: {tweet_id}")
            if post.media_url:
                print(f"  Image was not uploaded due to Twitter API limitations")
            return tweet_id if id_mode else (True, tweet_id)
        else:
            # Error
            error_data = response.json()
            error_msg = error_data.get('detail', error_data.get('title', 'Unknown error'))
            print(f" Twitter publish failed: {error_msg}")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None if id_mode else (False, error_msg)
            
    except requests.exceptions.Timeout:
        error_msg = "Twitter API request timed out"
        print(f" {error_msg}")
        return None if id_mode else (False, error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Twitter API request failed: {str(e)}"
        print(f" {error_msg}")
        return None if id_mode else (False, error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f" Twitter publish error: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return None if id_mode else (False, error_msg)


def publish_to_platform(post, account):
    """
    Publish post to a specific platform
    Returns: (success: bool, platform_post_id_or_error: str)
    """
    try:
        platform = dbs.session.get(Platform, account.platform_id)
        
        if not platform:
            return False, "Platform not found"
        
        platform_name = platform.platform_name.lower()
        print(f" Publishing to {platform_name}...")
        
        if platform_name == 'linkedin':
            return publish_to_linkedin(post, account)
        elif platform_name in ('twitter', 'x'):
            return publish_to_twitter(post, account)
        else:
            error_msg = f"Platform {platform.platform_name} not supported for publishing yet"
            print(f" {error_msg}")
            return False, error_msg
        
    except Exception as e:
        error_msg = f"Error publishing to platform: {str(e)}"
        print(f" {error_msg}")
        return False, error_msg


def check_and_publish_scheduled_posts():
    """Check for scheduled posts that are past their scheduled time and publish them to platforms"""
    try:
        # Use local time instead of UTC since scheduled times are in local timezone
        current_time = datetime.now()
        print(f"\n{'='*60}")
        print(f" CHECKING SCHEDULED POSTS")
        print(f"{'='*60}")
        print(f"Current local time: {current_time}")
        
        # Find all scheduled posts where the scheduled time has passed
        scheduled_posts = ScheduledPost.query.filter(
            ScheduledPost.status == 'scheduled',
            ScheduledPost.scheduled_time <= current_time
        ).all()
        
        print(f" Found {len(scheduled_posts)} scheduled posts ready to publish")
        
        if len(scheduled_posts) == 0:
            print(f"{'='*60}\n")
            return 0
        
        for sp in scheduled_posts:
            print(f"   - Post {sp.post_id}: scheduled for {sp.scheduled_time}")
        
        published_count = 0
        failed_count = 0
        
        for sched_post in scheduled_posts:
            try:
                print(f"\n Processing scheduled post {sched_post.post_id} for platform {sched_post.platform_id}...")
                
                # Get the post
                post = Post.query.get(sched_post.post_id)
                if not post:
                    print(f" Post {sched_post.post_id} not found")
                    sched_post.status = 'failed'
                    failed_count += 1
                    continue
                
                # Get the linked account for this platform
                account = LinkedAccount.query.filter_by(
                    user_id=post.user_id,
                    platform_id=sched_post.platform_id
                ).first()
                
                if not account:
                    # Try treating Platform as a linked account directly (for tests)
                    account = dbs.session.get(Platform, sched_post.platform_id)
                    if not account or not hasattr(account, 'access_token') or not account.access_token:
                        print(f" No linked account found for platform {sched_post.platform_id}")
                        sched_post.status = 'failed'
                        sched_post.error_message = "No linked account found"
                        failed_count += 1
                        continue
                
                platform = dbs.session.get(Platform, sched_post.platform_id)
                platform_name = platform.platform_name if platform else "Unknown"
                print(f" Platform: {platform_name}")
                
                # Publish to the platform (handles both signatures)
                result = publish_to_platform(post, account)
                # publish_to_platform returns (success, result_str) always
                # but if called from mocked tests it may return just a string
                if isinstance(result, tuple):
                    success, result_msg = result
                else:
                    # Shouldn't happen in normal usage, but be safe
                    success = bool(result)
                    result_msg = result
                
                if success:
                    # Update the scheduled post status
                    sched_post.status = 'published'
                    sched_post.published_at = current_time
                    
                    # Store the platform post ID if provided
                    if result_msg and result_msg != 'unknown':
                        # You can add a column to store platform_post_id if needed
                        pass
                    
                    # Update the main post status
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
                    print(f" Post {sched_post.post_id} published successfully!")
                else:
                    # Mark as failed
                    sched_post.status = 'failed'
                    sched_post.error_message = str(result_msg) if result_msg else "Publishing failed"
                    failed_count += 1
                    print(f" Failed to publish post {sched_post.post_id}: {result_msg}")
                    
            except Exception as e:
                print(f" Error processing post {sched_post.post_id}: {e}")
                sched_post.status = 'failed'
                sched_post.error_message = str(e)
                failed_count += 1
        
        # Commit all changes
        if published_count > 0 or failed_count > 0:
            dbs.session.commit()
            print(f"\n{'='*60}")
            print(f" Successfully published: {published_count}")
            print(f" Failed: {failed_count}")
            print(f"{'='*60}\n")
        
        return published_count
        
    except Exception as e:
        print(f"\n Error checking scheduled posts: {e}")
        import traceback
        print(traceback.format_exc())
        dbs.session.rollback()
        return 0


# ---------------------------
# IMPORT AUTH BLUEPRINT
# ---------------------------
# Import auth blueprint (from same directory)
from src.auth import auth, init_auth

# Initialize auth with User model and database
init_auth(User, dbs)

app.register_blueprint(auth)


# ---------------------------
# SESSION MANAGEMENT
# ---------------------------
@app.before_request
def make_session_permanent():
    """Ensure all sessions are permanent to prevent expiration"""
    if 'user_id' in session:
        session.permanent = True
        session.modified = True


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
        flash("Access denied  Users only.", "danger")
        return redirect(url_for('auth.login'))
    return redirect(url_for('linked_accounts'))


@app.route('/dashboard/manager')
def manager_dashboard():
    """Manager Dashboard Page"""
    if 'user_id' not in session or session.get('role') != 'manager':
        flash("Access denied  Managers only.", "danger")
        return redirect(url_for('auth.login'))
    
    # Check and publish scheduled posts that are ready
    check_and_publish_scheduled_posts()
    
    # Get stats for dashboard
    total_posts = Post.query.count()
    pending_approvals = Post.query.filter(Post.status == 'pending').count()
    connected_accounts = LinkedAccount.query.count()
    
    # Get notification count (pending + scheduled posts)
    notification_count = Post.query.filter(
        Post.status.in_(['pending', 'scheduled'])
    ).count()
    
    # Get user initial
    full_name = session.get('full_name', 'Manager')
    user_initial = full_name[0].upper() if full_name else 'M'
    
    # Get recent activity (last 5 posts and accounts)
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    recent_accounts = LinkedAccount.query.order_by(LinkedAccount.linked_at.desc()).limit(5).all()
    
    # Combine and sort by date
    activities = []
    
    for post in recent_posts:
        user = dbs.session.get(User, post.user_id)
        activities.append({
            'type': 'post',
            'title': 'New post submitted',
            'description': f"{user.full_name if user else 'Unknown'} submitted a post for approval",
            'timestamp': post.created_at,
            'status': post.status
        })
    
    for account in recent_accounts:
        user = dbs.session.get(User, account.user_id)
        platform = dbs.session.get(Platform, account.platform_id)
        activities.append({
            'type': 'account',
            'title': 'Account connected',
            'description': f"{user.full_name if user else 'Unknown'} connected {platform.platform_name if platform else 'Unknown'} account",
            'timestamp': account.linked_at,
            'status': 'connected'
        })
    
    # Sort by timestamp descending
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    activities = activities[:5]  # Keep only top 5
    
    return render_template(
        'manager_dashboard.html', 
        name=session.get('full_name'),
        notification_count=notification_count,
        user_initial=user_initial,
        total_posts=total_posts,
        pending_approvals=pending_approvals,
        connected_accounts=connected_accounts,
        activities=activities,
        now=datetime.now
    )


# ---------------------------
# TEAM COLLABORATION ROUTES
# ---------------------------
@app.route('/team-collaboration')
def team_collaboration():
    """Team Collaboration Dashboard for Managers"""
    if 'user_id' not in session or session.get('role') != 'manager':
        flash("Access denied  Managers only.", "danger")
        return redirect(url_for('auth.login'))

    # Check and publish scheduled posts that are ready
    check_and_publish_scheduled_posts()
    
    # Auto-reject pending posts where scheduled time has passed
    current_time = datetime.now()
    
    # Find pending posts with expired scheduled times
    expired_posts = dbs.session.query(Post, ScheduledPost).join(
        ScheduledPost, Post.post_id == ScheduledPost.post_id
    ).filter(
        Post.status == 'pending',
        ScheduledPost.scheduled_time < current_time
    ).all()
    
    expired_count = 0
    for post, sched_post in expired_posts:
        post.status = 'rejected'
        sched_post.status = 'failed'
        expired_count += 1
        print(f" Auto-rejected post {post.post_id} - scheduled time {sched_post.scheduled_time} has passed")
    
    if expired_count > 0:
        dbs.session.commit()
        print(f" Auto-rejected {expired_count} expired pending posts")

    # Get all team members
    team_members = User.query.all()
    members_list = [{
        'user_id': user.user_id,
        'name': user.full_name or 'Unknown',
        'email': user.email,
        'role': user.role
    } for user in team_members]

    # Get posts for approval (pending and scheduled posts)
    filter_status = request.args.get('filter', 'all')

    if filter_status == 'all':
        # Show both pending and scheduled posts by default
        posts = dbs.session.query(
            Post.post_id,
            Post.content_text,
            Post.status,
            Post.created_at,
            User.full_name.label('author')
        ).join(User, Post.user_id == User.user_id)\
         .filter(Post.status.in_(['pending', 'scheduled']))\
         .order_by(Post.created_at.desc()).all()
    elif filter_status == 'pending':
        posts = dbs.session.query(
            Post.post_id,
            Post.content_text,
            Post.status,
            Post.created_at,
            User.full_name.label('author')
        ).join(User, Post.user_id == User.user_id)\
         .filter(Post.status == 'pending')\
         .order_by(Post.created_at.desc()).all()
    elif filter_status == 'scheduled':
        posts = dbs.session.query(
            Post.post_id,
            Post.content_text,
            Post.status,
            Post.created_at,
            User.full_name.label('author')
        ).join(User, Post.user_id == User.user_id)\
         .filter(Post.status == 'scheduled')\
         .order_by(Post.created_at.desc()).all()
    else:
        posts = dbs.session.query(
            Post.post_id,
            Post.content_text,
            Post.status,
            Post.created_at,
            User.full_name.label('author')
        ).join(User, Post.user_id == User.user_id)\
         .filter(Post.status == filter_status)\
         .order_by(Post.created_at.desc()).all()

    posts_list = []
    for post in posts:
        post_data = {
            'post_id': post.post_id,
            'content_text': post.content_text or '',
            'status': post.status,
            'created_at': post.created_at,
            'author': post.author or 'Unknown User'
        }

        # Get scheduled time if exists (for both 'pending' and 'scheduled' posts)
        scheduled_post = ScheduledPost.query.filter_by(post_id=post.post_id).first()
        if scheduled_post and scheduled_post.scheduled_time:
            post_data['scheduled_time'] = scheduled_post.scheduled_time

        posts_list.append(post_data)

    # Get notification count (pending + scheduled posts)
    notification_count = Post.query.filter(Post.status.in_(['pending', 'scheduled'])).count()

    # Get user initial for avatar
    user_initial = session.get('full_name', 'M')[0].upper()

    return render_template(
        'team_collaboration.html',
        team_members=members_list,
        pending_posts=posts_list,
        notification_count=notification_count,
        user_initial=user_initial,
        session=session,
        current_time=current_time  # Pass current time for comparison in template
    )


@app.route('/invite_member', methods=['POST'])
def invite_member():
    """Invite a new team member"""
    if 'user_id' not in session or session.get('role') != 'manager':
        return {'success': False, 'message': 'Access denied'}, 403

    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        role = data.get('role', 'user')

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already exists'}), 200

        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        # Hash password
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(temp_password)

        # Create new user
        new_user = User(
            email=email,
            password_hash=hashed_password,
            full_name=name,
            role=role
        )
        
        dbs.session.add(new_user)
        dbs.session.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully invited {name}!',
            'temp_password': temp_password,
            'member': {
                'user_id': new_user.user_id,
                'name': new_user.full_name,
                'email': new_user.email,
                'role': new_user.role
            }
        })

    except Exception as e:
        dbs.session.rollback()
        print(f"Error inviting member: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/search_members')
def search_members():
    """Search team members by name or email"""
    if 'user_id' not in session:
        return [], 403

    query = request.args.get('query', '').lower()

    if not query:
        # Return all members if no query
        members = User.query.all()
    else:
        # Search by name or email
        members = User.query.filter(
            (User.full_name.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%'))
        ).all()

    return [{
        'user_id': user.user_id,
        'name': user.full_name or 'Unknown',
        'email': user.email,
        'role': user.role
    } for user in members]


@app.route('/update_post_status', methods=['POST'])
def update_post_status():
    """Update post approval status"""
    if 'user_id' not in session or session.get('role') != 'manager':
        return {'success': False, 'message': 'Access denied'}, 403

    try:
        data = request.get_json()
        post_id = data.get('post_id')
        action = data.get('action')  # 'approved' or 'rejected'

        post = dbs.session.get(Post, post_id)
        if not post:
            return {'success': False, 'message': 'Post not found'}, 404

        if action == 'approved':
            # Check if this post has a scheduled time
            scheduled_posts = ScheduledPost.query.filter_by(post_id=post_id).all()
            
            if scheduled_posts and len(scheduled_posts) > 0 and scheduled_posts[0].scheduled_time:
                # Post should be scheduled
                post.status = 'scheduled'
                # Update ALL scheduled post entries to 'scheduled'
                for sp in scheduled_posts:
                    sp.status = 'scheduled'
                print(f" Approved post {post_id} - Set to scheduled for {scheduled_posts[0].scheduled_time} ({len(scheduled_posts)} platforms)")
            else:
                # No schedule, mark as approved (can be published immediately)
                post.status = 'approved'
                print(f" Approved post {post_id} - Set to approved")
        elif action == 'rejected':
            post.status = 'rejected'
            # Update ALL scheduled post entries to failed
            scheduled_posts = ScheduledPost.query.filter_by(post_id=post_id).all()
            for sp in scheduled_posts:
                sp.status = 'failed'
            print(f" Rejected post {post_id}")
        
        dbs.session.commit()

        return {'success': True, 'message': f'Post {action} successfully'}

    except Exception as e:
        dbs.session.rollback()
        print(f"Error updating post status: {e}")
        return {'success': False, 'message': str(e)}, 500


# ---------------------------
# POST SCHEDULER ROUTES
# ---------------------------
@app.route('/post-scheduler')
def post_scheduler():
    """Post scheduler page - for users to create and schedule posts"""
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

    # Get notification count (pending + scheduled posts)
    notification_count = Post.query.filter(
        Post.status.in_(['pending', 'scheduled'])
    ).count()
    
    # Get user initial
    full_name = session.get('full_name', user.full_name if user else 'User')
    user_initial = full_name[0].upper() if full_name else 'U'

    return render_template(
        'create_schedule_posts.html', 
        user=user, 
        accounts=account_list,
        notification_count=notification_count,
        user_initial=user_initial
    )


@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Get all posts for current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Check and publish scheduled posts that are past their scheduled time
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
    """Create a new post"""
    print(f"\n POST /api/posts called")
    print(f"Session data: {dict(session)}")
    print(f"Has user_id: {'user_id' in session}")
    print(f"Cookies: {request.cookies}")
    
    if 'user_id' not in session:
        print(f" NO USER_ID IN SESSION - Returning 401")
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        text = request.form.get('text', '')
        account_ids = request.form.getlist('account_ids[]')
        scheduled_time = request.form.get('scheduled_time')
        status = request.form.get('status', 'draft')

        print(f"\n{'='*60}")
        print(f" CREATE POST REQUEST")
        print(f"{'='*60}")
        print(f"User ID: {user_id}")
        print(f"Status: '{status}'")
        print(f"Scheduled time: '{scheduled_time}'")
        print(f"Account IDs: {account_ids}")
        print(f"Text length: {len(text)} chars")
        print(f"Has media: {'Yes' if request.files.get('media') else 'No'}")
        print(f"{'='*60}\n")

        media_file = request.files.get('media')
        
        # Validation
        if not text and not media_file:
            print(" Validation failed: No text or media")
            return jsonify({'error': 'Post must contain text or media'}), 400
        
        # Only require accounts for non-draft posts
        if status != 'draft' and not account_ids:
            print(" Validation failed: No accounts selected for non-draft post")
            return jsonify({'error': 'At least one account must be selected'}), 400
        
        print(f" Validation passed")

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

        # Determine final status based on role and request
        user_role = session.get('role', 'user')
        
        if status == 'draft':
            # Drafts don't need approval
            final_status = 'draft'
        elif user_role == 'manager':
            # Managers can directly publish or schedule without approval
            if status == 'published':
                final_status = 'published'
            elif status == 'scheduled' or scheduled_dt:
                final_status = 'scheduled'
            else:
                final_status = 'draft'
        else:
            # Regular users: all non-draft posts need approval
            if status == 'published' or status == 'scheduled' or scheduled_dt:
                final_status = 'pending'  # Must be approved by manager first
            else:
                final_status = 'draft'

        print(f" User role: {user_role}, Requested status: '{status}', Final status: '{final_status}'")

        # Create post
        print(f" Creating Post object...")
        post = Post(
            user_id=user_id,
            content_text=text,
            media_url=media_url,
            status=final_status
        )
        dbs.session.add(post)
        dbs.session.flush()
        print(f" Post created with ID: {post.post_id}")

        # Link platforms
        for account_id in account_ids:
            try:
                # Convert to int if it's a string
                account_id_int = int(account_id)
                account = dbs.session.get(LinkedAccount, account_id_int)
                
                if not account:
                    print(f" Account {account_id_int} not found")
                    continue
                    
                if account.user_id != user_id:
                    print(f" Account {account_id_int} does not belong to user {user_id}")
                    continue
                
                print(f" Linking post to platform {account.platform_id}")
                pp = PostPlatform(
                    post_id=post.post_id,
                    platform_id=account.platform_id
                )
                dbs.session.add(pp)

                # Create schedule entry if user requested scheduling
                # Store the scheduled time even if status is 'pending' (waiting for approval)
                if scheduled_dt:
                    print(f" Creating scheduled post entry for {scheduled_dt} (current status: {final_status})")
                    sched = ScheduledPost(
                        post_id=post.post_id,
                        platform_id=account.platform_id,
                        scheduled_time=scheduled_dt,
                        status='scheduled' if final_status == 'scheduled' else 'pending'
                    )
                    dbs.session.add(sched)
            except (ValueError, TypeError) as e:
                print(f" Invalid account_id: {account_id}, error: {e}")
                continue

        print(f" Committing to database...")
        dbs.session.commit()
        print(f" Post committed successfully!")

        # If the status is 'published', immediately publish to platforms
        if final_status == 'published':
            print(f"\n Attempting immediate publish to platforms...")
            published_count = 0
            failed_count = 0
            
            for account_id in account_ids:
                try:
                    account_id_int = int(account_id)
                    account = dbs.session.get(LinkedAccount, account_id_int)
                    
                    if account and account.user_id == user_id:
                        success, result = publish_to_platform(post, account)
                        
                        if success:
                            # Update PostPlatform to mark as published
                            pp = PostPlatform.query.filter_by(
                                post_id=post.post_id,
                                platform_id=account.platform_id
                            ).first()
                            if pp:
                                pp.published = True
                                pp.published_at = datetime.now()
                            published_count += 1
                            print(f" Published to platform {account.platform_id}")
                        else:
                            failed_count += 1
                            print(f" Failed to publish to platform {account.platform_id}: {result}")
                except Exception as e:
                    print(f" Error publishing to account {account_id}: {e}")
                    failed_count += 1
            
            if published_count > 0 or failed_count > 0:
                dbs.session.commit()
                print(f" Immediate publish results: {published_count} successful, {failed_count} failed")

        return jsonify({
            'message': 'Post created successfully',
            'post_id': post.post_id
        }), 201

    except Exception as e:
        dbs.session.rollback()
        print(f"\n{'='*60}")
        print(f" ERROR CREATING POST")
        print(f"{'='*60}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    """Update an existing post"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        post = Post.query.filter_by(post_id=post_id, user_id=user_id).first()

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Get form data
        text = request.form.get('text')
        if text is not None:
            post.content_text = text

        status = request.form.get('status', post.status)
        scheduled_time = request.form.get('scheduled_time')

        print(f" Updating post {post_id} - Status: {status}, Scheduled: {scheduled_time}")

        # Handle status changes
        if status == 'published':
            post.status = 'published'
            ScheduledPost.query.filter_by(post_id=post.post_id).delete()
            PostPlatform.query.filter_by(post_id=post.post_id).update({
                'published': True,
                'published_at': datetime.now()
            })

        elif status == 'scheduled' and scheduled_time:
            try:
                scheduled_dt = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
                post.status = 'scheduled'

                scheduled_post = ScheduledPost.query.filter_by(post_id=post.post_id).first()
                if scheduled_post:
                    scheduled_post.scheduled_time = scheduled_dt
                    scheduled_post.status = 'scheduled'
                else:
                    post_platform = PostPlatform.query.filter_by(post_id=post.post_id).first()
                    if post_platform:
                        new_sched = ScheduledPost(
                            post_id=post.post_id,
                            platform_id=post_platform.platform_id,
                            scheduled_time=scheduled_dt,
                            status='scheduled'
                        )
                        dbs.session.add(new_sched)

            except ValueError:
                return jsonify({'error': 'Invalid scheduled time format'}), 400

        elif status == 'draft':
            post.status = 'draft'
            ScheduledPost.query.filter_by(post_id=post.post_id).delete()

        post.updated_at = datetime.now()
        dbs.session.commit()

        print(f" Updated post {post_id} to status: {post.status}")
        return jsonify({'message': 'Post updated successfully'}), 200

    except Exception as e:
        dbs.session.rollback()
        print(f" Error updating post: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """Delete a post"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        post = Post.query.filter_by(post_id=post_id, user_id=user_id).first()

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Delete media file
        if post.media_url and os.path.exists(post.media_url):
            os.remove(post.media_url)

        # Delete scheduled posts first (foreign key constraint)
        ScheduledPost.query.filter_by(post_id=post.post_id).delete()

        # Delete post platforms
        PostPlatform.query.filter_by(post_id=post.post_id).delete()

        # Delete post
        dbs.session.delete(post)
        dbs.session.commit()

        print(f" Deleted post {post_id}")
        return jsonify({'message': 'Post deleted successfully'}), 200

    except Exception as e:
        dbs.session.rollback()
        print(f" Error deleting post: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


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
        now=datetime.utcnow(),
        notification_count=Post.query.filter(Post.status.in_(['pending', 'scheduled'])).count(),
        user_initial=session.get('full_name', user.full_name if user else 'U')[0].upper() if session.get('full_name') or (user and user.full_name) else 'U'
    )

# ---------------------------
# LINKEDIN AUTH
# ---------------------------


@app.route('/connect/linkedin/test')
def connect_linkedin_test():
    """Create a test LinkedIn account without OAuth (for testing only)"""
    if 'user_id' not in session:
        flash("Please log in first", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    active_user = dbs.session.get(User, user_id)

    if not active_user:
        flash("User not found", "danger")
        return redirect(url_for('auth.login'))

    try:
        # Get or create LinkedIn platform
        linkedin = Platform.query.filter_by(platform_name='LinkedIn').first()
        if not linkedin:
            linkedin = Platform(
                platform_name='LinkedIn',
                api_endpoint='https://api.linkedin.com/v2/ugcPosts'
            )
            dbs.session.add(linkedin)
            dbs.session.commit()

        # Check if already linked
        existing = LinkedAccount.query.filter_by(
            user_id=user_id,
            platform_id=linkedin.platform_id
        ).first()

        if existing:
            flash("LinkedIn account already linked!", "info")
            return redirect(url_for('linked_accounts'))

        # Create test LinkedIn account with mock token
        test_account = LinkedAccount(
            user_id=user_id,
            platform_id=linkedin.platform_id,
            access_token='test_token_' + secrets.token_hex(16),  # Mock token
            account_username=f"{active_user.full_name or 'Test User'} (Test Account)",
            linked_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
            follower_count=0,
            post_count=0
        )
        dbs.session.add(test_account)
        dbs.session.commit()

        print(f" Created test LinkedIn account for user {user_id}")
        flash(" Test LinkedIn account created successfully! Note: This won't actually post to LinkedIn.", "success")
        return redirect(url_for('linked_accounts'))

    except Exception as e:
        dbs.session.rollback()
        print(f" Error creating test account: {e}")
        flash("Failed to create test account", "danger")
        return redirect(url_for('linked_accounts'))


@app.route('/connect/linkedin')
def connect_linkedin():
    """Initiate LinkedIn OAuth flow"""
    # Require authentication
    if 'user_id' not in session:
        flash("Please log in first", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    active_user = dbs.session.get(User, user_id)

    if not active_user:
        flash("User not found", "danger")
        return redirect(url_for('auth.login'))

    # Ensure session persists through OAuth redirect
    session.permanent = True
    session.modified = True

    print(f" User {active_user.user_id} starting LinkedIn connection")

    linkedin = Platform.query.filter_by(platform_name='LinkedIn').first()
    if not linkedin:
        linkedin = Platform(
            platform_name='LinkedIn',
            api_endpoint='https://api.linkedin.com/v2/ugcPosts'
        )
        dbs.session.add(linkedin)
        dbs.session.commit()

    state = secrets.token_urlsafe(32)

    # Store state in database
    oauth_state = OAuthState(
        state_id=state,
        user_id=active_user.user_id,
        platform='linkedin'
    )
    dbs.session.add(oauth_state)
    dbs.session.commit()

    cleanup_old_oauth_states()

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        "?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
        "&scope=openid%20profile%20email%20w_member_social"
        f"&state={state}"
    )

    return redirect(auth_url)


@app.route('/callback/linkedin')
def linkedin_callback():
    """Handle LinkedIn OAuth callback"""
    from datetime import datetime  # pylint: disable=reimported
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
        oauth_state = OAuthState.query.filter_by(state_token=state).first()
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

        # Restore session to prevent logout after OAuth
        user = dbs.session.get(User, user_id)
        if user:
            session['user_id'] = user.user_id
            session['full_name'] = user.full_name
            session['role'] = user.role
            session['email'] = user.email
            session.permanent = True
            session.modified = True
            print(f" Session restored for user {user.user_id}")

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
    """Initiate Twitter OAuth flow with PKCE"""
    # Require authentication
    if 'user_id' not in session:
        flash("Please log in first", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    active_user = dbs.session.get(User, user_id)

    if not active_user:
        flash("User not found", "danger")
        return redirect(url_for('auth.login'))

    # Ensure session persists through OAuth redirect
    session.permanent = True
    session.modified = True

    print(f" User {active_user.user_id} starting Twitter connection")

    twitter_platform = Platform.query.filter_by(platform_name='Twitter').first()
    if not twitter_platform:
        twitter_platform = Platform(
            platform_name='Twitter',
            api_endpoint='https://api.twitter.com/2'
        )
        dbs.session.add(twitter_platform)
        dbs.session.commit()

    # Generate PKCE challenge
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')

    state = secrets.token_urlsafe(32)

    # Store in database
    oauth_state = OAuthState(
        state_id=state,
        user_id=active_user.user_id,
        platform='twitter',
        code_verifier=code_verifier
    )
    dbs.session.add(oauth_state)
    dbs.session.commit()

    cleanup_old_oauth_states()

    auth_params = {
        "response_type": "code",
        "client_id": TWITTER_CLIENT_ID,
        "redirect_uri": TWITTER_REDIRECT_URI,
        "scope": "tweet.read tweet.write users.read follows.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }

    auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(auth_params)}"
    print(f" Redirecting to Twitter with state: {state}")
    return redirect(auth_url)


@app.route('/callback/twitter')
def callback_twitter():
    """Handle Twitter OAuth callback"""
    print(" Twitter callback triggered")
    
    try:
        state = request.args.get('state')
        code = request.args.get('code')

        if not state or not code:
            return jsonify({"error": "Missing state or code"}), 400

        # Verify state from DATABASE (not session)
        oauth_state = OAuthState.query.filter_by(state_token=state).first()
        if not oauth_state:
            print(f" Invalid OAuth state: {state}")
            return jsonify({"error": "Invalid OAuth state"}), 400

        user_id = oauth_state.user_id
        code_verifier = oauth_state.code_verifier
        
        print(f" Found state for user {user_id}")

        # Mark oauth_state for deletion (will be committed with account update)
        dbs.session.delete(oauth_state)

        # Exchange code for access token
        token_url = "https://api.twitter.com/2/oauth2/token"
        auth_str = f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()

        payload = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": TWITTER_REDIRECT_URI,
            "code_verifier": code_verifier,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_b64}",
        }

        token_resp = requests.post(token_url, data=payload, headers=headers, timeout=10)
        token_data = token_resp.json()
        print(" Twitter token response received")

        if "access_token" not in token_data:
            print(f" No access token: {token_data}")
            return jsonify({"error": "Failed to get Twitter access token"}), 400

        access_token = token_data["access_token"]

        # Get user info from Twitter
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_resp = requests.get(
            "https://api.twitter.com/2/users/me",
            headers=headers,
            params={"user.fields": "public_metrics,username,name"},
            timeout=10
        )
        profile_data = profile_resp.json()
        
        external_id = profile_data.get("data", {}).get("id")
        username = profile_data.get("data", {}).get("username", "Unknown")
        name = profile_data.get("data", {}).get("name", "Twitter User")
        metrics = profile_data.get("data", {}).get("public_metrics", {})
        
        print(f" Fetched: {name} (@{username})")

        if not external_id:
            return jsonify({"error": "Failed to fetch Twitter profile"}), 400

        # Get or create Twitter platform
        twitter_platform = Platform.query.filter_by(platform_name="Twitter").first()
        if not twitter_platform:
            twitter_platform = Platform(
                platform_name="Twitter",
                api_endpoint="https://api.twitter.com/2"
            )
            dbs.session.add(twitter_platform)
            dbs.session.commit()

        # Check if user already linked this platform
        existing = LinkedAccount.query.filter_by(
            user_id=user_id,
            platform_id=twitter_platform.platform_id
        ).first()

        if existing:
            # Update existing entry
            existing.account_username = f"{name} (@{username})"
            existing.access_token = access_token
            existing.refresh_token = token_data.get("refresh_token")
            existing.external_id = external_id
            existing.follower_count = metrics.get("followers_count", 0)
            existing.post_count = metrics.get("tweet_count", 0)
            existing.last_synced = datetime.utcnow()
            existing.linked_at = datetime.utcnow()
        else:
            # Create new linked account
            new_acc = LinkedAccount(
                user_id=user_id,
                platform_id=twitter_platform.platform_id,
                account_username=f"{name} (@{username})",
                access_token=access_token,
                refresh_token=token_data.get("refresh_token"),
                external_id=external_id,
                follower_count=metrics.get("followers_count", 0),
                post_count=metrics.get("tweet_count", 0),
                last_synced=datetime.utcnow(),
                linked_at=datetime.utcnow(),
            )
            dbs.session.add(new_acc)

        dbs.session.commit()
        
        # Restore session to prevent logout after OAuth
        user = dbs.session.get(User, user_id)
        if user:
            session['user_id'] = user.user_id
            session['full_name'] = user.full_name
            session['role'] = user.role
            session['email'] = user.email
            session.permanent = True
            session.modified = True
            print(f" Session restored for user {user.user_id}")
        
        print(f" Twitter account linked successfully: {name} (@{username})")
        flash(f"Successfully connected Twitter account: {name} (@{username})", "success")

        return redirect(url_for("linked_accounts"))

    except Exception as e:
        print(f" Twitter callback error: {e}")
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
                print(f" Refreshed LinkedIn: {acc.account_username}")

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
                print(f" Refreshed Twitter: {acc.account_username}")
            else:
                print(f" Twitter refresh failed: {user_response.text}")

    except requests.RequestException as error:
        print(f" Refresh error: {error}")

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
        print(f" Disconnected account {account_id}")

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
# BACKGROUND SCHEDULER SETUP
# ---------------------------
def scheduled_post_checker():
    """Background job that runs every minute to check and publish scheduled posts"""
    with app.app_context():
        try:
            check_and_publish_scheduled_posts()
        except Exception as e:
            print(f" Scheduler error: {e}")

# Initialize the background scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Add job to check every 30 seconds
scheduler.add_job(
    func=scheduled_post_checker,
    trigger=IntervalTrigger(seconds=30),
    id='check_scheduled_posts',
    name='Check and publish scheduled posts',
    replace_existing=True
)

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

print(" Background scheduler started - checking every 30 seconds")


# ---------------------------
# RUN SERVER
# ---------------------------
if __name__ == '__main__':
    with app.app_context():
        dbs.create_all()
    app.run(debug=True, use_reloader=False)  # Disabled auto-reload to prevent constant restarts
