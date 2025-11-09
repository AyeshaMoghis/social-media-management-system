"""
Social Media Management System - Flask Application
Handles OAuth authentication for Twitter and LinkedIn platforms,
and integrates authentication + role-based dashboards.
"""

# ---------------------------
# Standard library imports
# ---------------------------
import os
import secrets
import hashlib
import base64
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

# ---------------------------
# Third-party imports
# ---------------------------
from flask import (
    Flask, render_template, redirect, url_for,
    session, request, flash
)
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


# ---------------------------
# HELPER FUNCTIONS
# ---------------------------
def current_user():
    """Ensures a user always exists and is stored in session."""
    session.permanent = True
    uid = session.get('user_id')

    if uid:
        user = dbs.session.get(User, uid)
        if user:
            return user

    user = User.query.first()
    if not user:
        user = User(email="demo@user.com", full_name="Demo User")
        dbs.session.add(user)
        dbs.session.commit()

    session['user_id'] = user.user_id
    session['full_name'] = user.full_name
    session['role'] = user.role
    return user


def cleanup_old_oauth_states():
    """Remove OAuth states older than 10 minutes"""
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    OAuthState.query.filter(OAuthState.created_at < cutoff).delete()
    dbs.session.commit()


# ---------------------------
# IMPORT AUTH BLUEPRINT
# ---------------------------
from src.auth import auth
app.register_blueprint(auth)


# ---------------------------
# ROLE-BASED DASHBOARDS
# ---------------------------
@app.route('/')
def home():
    """Landing page redirects based on session."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('dashboard_redirect'))


@app.route('/dashboard')
def dashboard_redirect():
    """Redirect user to their role dashboard."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role') == 'manager':
        return redirect(url_for('manager_dashboard'))
    return redirect(url_for('linked_accounts'))


@app.route('/dashboard/user')
def user_dashboard():
    """Redirects user dashboard → Linked Accounts."""
    if 'user_id' not in session or session.get('role') != 'user':
        flash("Access denied — Users only.", "danger")
        return redirect(url_for('auth.login'))
    return redirect(url_for('linked_accounts'))


@app.route('/dashboard/manager')
def manager_dashboard():
    """Simple Manager Dashboard Page"""
    if 'user_id' not in session or session.get('role') != 'manager':
        flash("Access denied — Managers only.", "danger")
        return redirect(url_for('auth.login'))
    return render_template('manager_dashboard.html', name=session.get('full_name'))


# ---------------------------
# LINKED ACCOUNTS DASHBOARD
# ---------------------------
@app.route('/linked-accounts')
def linked_accounts():
    """Display all linked social media accounts for current user"""
    active_user = current_user()
    accounts = LinkedAccount.query.filter_by(user_id=active_user.user_id).all()

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
            'follower_count': acc.follower_count,  # Remove the condition here
            'post_count': acc.post_count,          # Remove the condition here
            'is_connected': bool(acc.access_token),
            'last_synced': acc.last_synced,
            'show_stats': show_stats               # ADD THIS LINE - was missing!
        })

    return render_template(
        'linked_accounts.html',
        user=active_user,
        accounts=account_list,
        now=datetime.utcnow()
    )
# ---------------------------
# LINKEDIN AUTH
# ---------------------------
@app.route('/connect/linkedin')
def connect_linkedin():
    """Initiate LinkedIn OAuth flow"""
    active_user = current_user()
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
        "&scope=openid%20profile%20email"
        f"&state={state}"
    )

    return redirect(auth_url)


@app.route('/callback/linkedin')
def linkedin_callback():
    """Handle LinkedIn OAuth callback"""
    print("🟢 LinkedIn callback triggered")

    code = request.args.get('code')
    state = request.args.get('state')

    if not code or not state:
        return "Authorization failed - missing parameters.", 400

    # Retrieve state from database
    oauth_state = dbs.session.get(OAuthState, state)
    if not oauth_state:
        return "Invalid or expired state parameter", 400

    user_id = oauth_state.user_id

    # Delete used state
    dbs.session.delete(oauth_state)
    dbs.session.commit()

    # Exchange code for token
    try:
        token_response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            },
            timeout=10
        )

        if token_response.status_code != 200:
            print(f"❌ Token error: {token_response.text}")
            return f"LinkedIn OAuth failed: {token_response.text}", 400

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        id_token = token_data.get("id_token")

        if not access_token:
            return "Failed to get access token", 400

        print("✅ Access token received")

    except requests.RequestException as error:
        print(f"❌ Token exchange error: {error}")
        return f"Error during token exchange: {str(error)}", 500

    # Get user info
    name = "LinkedIn User"

    if id_token:
        try:
            payload = id_token.split('.')[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            name = decoded.get("name", name)
            email = decoded.get("email", "unknown")
            print(f"✅ Info from ID token: {name} ({email})")
        except (ValueError, KeyError) as error:
            print(f"⚠️ Could not decode ID token: {error}")

    # Save to database
    linkedin = Platform.query.filter_by(platform_name="LinkedIn").first()
    if not linkedin:
        linkedin = Platform(
            platform_name='LinkedIn',
            api_endpoint='https://api.linkedin.com/v2/ugcPosts'
        )
        dbs.session.add(linkedin)
        dbs.session.commit()

    acc = LinkedAccount.query.filter_by(
        user_id=user_id,
        platform_id=linkedin.platform_id
    ).first()

    if not acc:
        acc = LinkedAccount(user_id=user_id, platform_id=linkedin.platform_id)
        dbs.session.add(acc)

    acc.access_token = access_token
    acc.account_username = name
    acc.linked_at = datetime.utcnow()
    acc.last_synced = datetime.utcnow()
    # LinkedIn doesn't provide follower/post counts easily
    acc.follower_count = 0
    acc.post_count = 0
    dbs.session.commit()

    print(f"✅ Successfully linked LinkedIn for {name}")
    return redirect(url_for("linked_accounts"))


# ---------------------------
# TWITTER AUTH (FIXED)
# ---------------------------
@app.route('/connect/twitter')
def connect_twitter():
    """Initiate Twitter OAuth flow with PKCE"""
    active_user = current_user()
    print(f"✅ User {active_user.user_id} starting Twitter connection")

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

    # Store in database instead of session
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
        "scope": "tweet.read users.read follows.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }

    auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(auth_params)}"
    print(f"➡️ Redirecting to Twitter with state: {state}")
    return redirect(auth_url)


@app.route('/callback/twitter')
def callback_twitter():
    """Handle Twitter OAuth callback"""
    print("🟢 Twitter callback triggered")

    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return "Missing code or state parameter", 400

    # Retrieve state from database
    oauth_state = dbs.session.get(OAuthState, state)
    if not oauth_state:
        print("❌ Invalid or expired state")
        return "Invalid or expired state parameter", 400

    user_id = oauth_state.user_id
    code_verifier = oauth_state.code_verifier

    print(f"✅ Found state for user {user_id}")

    # Delete used state
    dbs.session.delete(oauth_state)
    dbs.session.commit()

    # Exchange for access token
    try:
        # Twitter requires Basic Auth with client_id:client_secret
        auth_header = base64.b64encode(
            f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}".encode()
        ).decode()

        token_response = requests.post(
            "https://api.twitter.com/2/oauth2/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth_header}"
            },
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TWITTER_REDIRECT_URI,
                "code_verifier": code_verifier
            },
            timeout=10
        )

        token_data = token_response.json()

        if token_response.status_code != 200:
            print(f"❌ Token error: {token_data}")
            error_desc = token_data.get('error_description', 'Unknown error')
            return f"Token exchange failed: {error_desc}", 400

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            return "No access token received", 400

        print("✅ Twitter access token received")

    except requests.RequestException as error:
        print(f"❌ Token exchange failed: {error}")
        return f"Error during token exchange: {str(error)}", 500

    # Get Twitter user info using API v2 directly
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
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
            followers = metrics.get("followers_count", 0)
            tweets = metrics.get("tweet_count", 0)

            print(f"✅ Fetched: {name} (@{username})")
            print(f"   📊 Followers: {followers:,}")
            print(f"   📝 Tweets: {tweets:,}")
        else:
            print(f"⚠️ Twitter API response: {user_response.text}")
            username, name, followers, tweets = "Unknown", "Twitter User", 0, 0

        print(f"✅ Fetched: {name} (@{username}) | Followers: {followers}")

        # Save in database
        twitter_platform = Platform.query.filter_by(platform_name="Twitter").first()
        if not twitter_platform:
            twitter_platform = Platform(
                platform_name='Twitter',
                api_endpoint='https://api.twitter.com/2'
            )
            dbs.session.add(twitter_platform)
            dbs.session.commit()

        acc = LinkedAccount.query.filter_by(
            user_id=user_id,
            platform_id=twitter_platform.platform_id
        ).first()

        if not acc:
            acc = LinkedAccount(user_id=user_id, platform_id=twitter_platform.platform_id)
            dbs.session.add(acc)

        acc.access_token = access_token
        acc.refresh_token = refresh_token
        acc.account_username = f"{name} (@{username})"
        acc.follower_count = followers
        acc.post_count = tweets
        acc.last_synced = datetime.utcnow()
        acc.linked_at = datetime.utcnow()

        dbs.session.commit()
        print("✅ Twitter account linked successfully")

        return redirect(url_for("linked_accounts"))

    except requests.RequestException as error:
        dbs.session.rollback()
        print(f"❌ Twitter fetch failed: {error}")
        return f"Twitter API error: {str(error)}", 500


# ---------------------------
# ACCOUNT MANAGEMENT
# ---------------------------
@app.route('/refresh-account/<int:account_id>')
def refresh_account(account_id):
    """Refresh account data from social media platform"""
    active_user = current_user()
    acc = LinkedAccount.query.filter_by(
        account_id=account_id,
        user_id=active_user.user_id
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
    active_user = current_user()
    acc = LinkedAccount.query.filter_by(
        account_id=account_id,
        user_id=active_user.user_id
    ).first()

    if acc:
        dbs.session.delete(acc)
        dbs.session.commit()
        print(f"✅ Disconnected account {account_id}")

    return redirect(url_for('linked_accounts'))


@app.route('/account-details/<int:account_id>')
def account_details(account_id):
    """Display detailed information for a linked account"""
    active_user = current_user()
    acc = LinkedAccount.query.filter_by(
        account_id=account_id,
        user_id=active_user.user_id
    ).first()

    if not acc:
        return "Account not found", 404

    platform = dbs.session.get(Platform, acc.platform_id)

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


if not os.getenv('TESTING'):
    with app.app_context():
        dbs.create_all()
        print("✅ Database tables created/verified")
# ---------------------------
# RUN SERVER
# ---------------------------
if __name__ == '__main__':
    with app.app_context():
        dbs.create_all()
    app.run(debug=True)
