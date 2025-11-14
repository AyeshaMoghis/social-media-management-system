"""
Social Media Management System - Flask Application
Integrates authentication + social media OAuth connections
"""
# Standard library imports
from auth import auth, init_auth
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
    from urllib.parse import quote_plus
    user = os.getenv('MYSQL_USER', 'root')
    pw = os.getenv('MYSQL_PASSWORD', '')
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    db_name = os.getenv('MYSQL_DB', 'smms')
    # URL-encode the password to handle special characters
    encoded_pw = quote_plus(pw) if pw else ''
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{encoded_pw}@{host}/{db_name}'
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
# Import auth blueprint (from same directory)

# Initialize auth with User model and database
init_auth(User, dbs)

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
        flash("Access denied — Managers only.", "danger")
        return redirect(url_for('auth.login'))

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
        session=session
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
            return {'success': False, 'message': 'Email already registered'}, 400

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
            full_name=name,
            role=role
        )

        # Add password_hash column if doesn't exist in model
        # For now, we'll use SQLAlchemy raw SQL to insert
        from sqlalchemy import text
        query = text("""
            INSERT INTO user (email, password_hash, full_name, role)
            VALUES (:email, :password_hash, :full_name, :role)
        """)

        dbs.session.execute(query, {
            'email': email,
            'password_hash': hashed_password,
            'full_name': name,
            'role': role
        })
        dbs.session.commit()

        # Get the newly created user
        new_user = User.query.filter_by(email=email).first()

        return {
            'success': True,
            'message': f'Successfully invited {name}!',
            'temp_password': temp_password,
            'member': {
                'user_id': new_user.user_id,
                'name': new_user.full_name,
                'email': new_user.email,
                'role': new_user.role
            }
        }

    except Exception as e:
        dbs.session.rollback()
        print(f"Error inviting member: {e}")
        return {'success': False, 'message': str(e)}, 500


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
            scheduled_post = ScheduledPost.query.filter_by(post_id=post_id).first()
            
            if scheduled_post and scheduled_post.scheduled_time:
                # Post should be scheduled
                post.status = 'scheduled'
                scheduled_post.status = 'scheduled'
                print(f"✅ Approved post {post_id} - Set to scheduled for {scheduled_post.scheduled_time}")
            else:
                # No schedule, mark as approved (can be published immediately)
                post.status = 'approved'
                print(f"✅ Approved post {post_id} - Set to approved")
        elif action == 'rejected':
            post.status = 'rejected'
            # Update scheduled post status if exists
            ScheduledPost.query.filter_by(post_id=post_id).update({'status': 'failed'})
            print(f"❌ Rejected post {post_id}")
        
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
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user_id = session['user_id']
        text = request.form.get('text', '')
        account_ids = request.form.getlist('account_ids[]')
        scheduled_time = request.form.get('scheduled_time')
        status = request.form.get('status', 'draft')

        print(f"📝 Creating post - Status: '{status}', Scheduled time: '{scheduled_time}'")

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

        print(f"✅ User role: {user_role}, Requested status: '{status}', Final status: '{final_status}'")

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

                # Create schedule entry if user requested scheduling
                # Store the scheduled time even if status is 'pending' (waiting for approval)
                if scheduled_dt:
                    print(f"📅 Creating scheduled post entry for {scheduled_dt} (current status: {final_status})")
                    sched = ScheduledPost(
                        post_id=post.post_id,
                        platform_id=account.platform_id,
                        scheduled_time=scheduled_dt,
                        status='scheduled' if final_status == 'scheduled' else 'pending'
                    )
                    dbs.session.add(sched)

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

        print(f"📝 Updating post {post_id} - Status: {status}, Scheduled: {scheduled_time}")

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

        print(f"✅ Updated post {post_id} to status: {post.status}")
        return jsonify({'message': 'Post updated successfully'}), 200

    except Exception as e:
        dbs.session.rollback()
        print(f"❌ Error updating post: {e}")
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

        print(f"✅ Deleted post {post_id}")
        return jsonify({'message': 'Post deleted successfully'}), 200

    except Exception as e:
        dbs.session.rollback()
        print(f"❌ Error deleting post: {e}")
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

    oauth_state = dbs.session.get(OAuthState, state)
    if not oauth_state:
        return "Invalid or expired state parameter", 400

    user_id = oauth_state.user_id
    dbs.session.delete(oauth_state)
    dbs.session.commit()

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
    acc.follower_count = 0
    acc.post_count = 0
    dbs.session.commit()

    print(f"✅ Successfully linked LinkedIn for {name}")
    flash(f"Successfully connected LinkedIn account: {name}", "success")
    return redirect(url_for("linked_accounts"))


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

    oauth_state = dbs.session.get(OAuthState, state)
    if not oauth_state:
        print("❌ Invalid or expired state")
        return "Invalid or expired state parameter", 400

    user_id = oauth_state.user_id
    code_verifier = oauth_state.code_verifier

    print(f"✅ Found state for user {user_id}")

    dbs.session.delete(oauth_state)
    dbs.session.commit()

    try:
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
        flash(f"Successfully connected Twitter account: {name} (@{username})", "success")

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
# RUN SERVER
# ---------------------------
if __name__ == '__main__':
    with app.app_context():
        dbs.create_all()
    app.run(debug=True)
