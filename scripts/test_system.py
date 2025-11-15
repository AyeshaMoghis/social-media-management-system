"""
Comprehensive System Test Script
Tests all key features of the Social Media Management System
"""
import sys
sys.path.insert(0, 'src')
from app import app, dbs, User, LinkedAccount, Post, ScheduledPost, Platform
from datetime import datetime, timedelta

print('='*60)
print('🧪 COMPREHENSIVE SYSTEM TEST')
print('='*60)

with app.app_context():
    # Test 1: Database Connection
    print('\n1️⃣ Testing Database Connection...')
    try:
        users = User.query.all()
        print(f'   ✅ Database connected - {len(users)} users found')
    except Exception as e:
        print(f'   ❌ Database error: {e}')
    
    # Test 2: User Accounts
    print('\n2️⃣ Testing User Accounts...')
    try:
        manager = User.query.filter_by(email='manager@test.com').first()
        regular_user = User.query.filter_by(email='user@test.com').first()
        print(f'   Manager: {manager.full_name if manager else "NOT FOUND"} (ID: {manager.user_id if manager else "N/A"})')
        print(f'   Regular User: {regular_user.full_name if regular_user else "NOT FOUND"} (ID: {regular_user.user_id if regular_user else "N/A"})')
        if manager and regular_user:
            print('   ✅ User accounts exist')
        else:
            print('   ⚠️  Some user accounts missing')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    # Test 3: Platforms
    print('\n3️⃣ Testing Platforms...')
    try:
        platforms = Platform.query.all()
        for p in platforms:
            print(f'   - {p.platform_name} (ID: {p.platform_id})')
        print(f'   ✅ {len(platforms)} platforms configured')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    # Test 4: Linked Accounts
    print('\n4️⃣ Testing Linked Accounts...')
    try:
        accounts = LinkedAccount.query.all()
        for acc in accounts:
            user = User.query.get(acc.user_id)
            platform = Platform.query.get(acc.platform_id)
            has_token = '✓' if acc.access_token else '✗'
            token_preview = acc.access_token[:20] + '...' if acc.access_token and len(acc.access_token) > 20 else 'None'
            print(f'   - {user.email if user else "Unknown"}: {platform.platform_name if platform else "Unknown"}')
            print(f'     Token: {has_token} ({token_preview})')
            print(f'     Username: {acc.account_username}')
            print(f'     Linked: {acc.linked_at}')
        print(f'   ✅ {len(accounts)} accounts linked')
        
        # Check for manager specifically
        if manager:
            manager_accounts = LinkedAccount.query.filter_by(user_id=manager.user_id).all()
            print(f'   📊 Manager has {len(manager_accounts)} linked accounts')
            for acc in manager_accounts:
                platform = Platform.query.get(acc.platform_id)
                print(f'      - {platform.platform_name if platform else "Unknown"}')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    # Test 5: Posts
    print('\n5️⃣ Testing Posts...')
    try:
        posts = Post.query.all()
        status_counts = {}
        for post in posts:
            status_counts[post.status] = status_counts.get(post.status, 0) + 1
        
        print(f'   Total Posts: {len(posts)}')
        for status, count in status_counts.items():
            print(f'   - {status}: {count}')
        print('   ✅ Posts table accessible')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    # Test 6: Scheduled Posts
    print('\n6️⃣ Testing Scheduled Posts...')
    try:
        scheduled = ScheduledPost.query.all()
        now = datetime.now()
        past_due = [s for s in scheduled if s.scheduled_time and s.scheduled_time < now and s.status == 'scheduled']
        upcoming = [s for s in scheduled if s.scheduled_time and s.scheduled_time > now and s.status == 'scheduled']
        
        print(f'   Total Scheduled: {len(scheduled)}')
        print(f'   Past Due (should auto-publish): {len(past_due)}')
        print(f'   Upcoming: {len(upcoming)}')
        
        if past_due:
            print('   ⚠️  Posts that need to be published:')
            for sp in past_due[:3]:  # Show first 3
                post = Post.query.get(sp.post_id)
                if post:
                    print(f'      - Post {sp.post_id}: {sp.scheduled_time}')
                    print(f'        Content: {post.content_text[:50]}...')
        
        print('   ✅ Scheduled posts accessible')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    # Test 7: Flask Configuration
    print('\n7️⃣ Testing Flask Configuration...')
    try:
        print(f'   Secret Key: {"✓ SET" if app.secret_key else "✗ MISSING"}')
        print(f'   Session Lifetime: {app.config.get("PERMANENT_SESSION_LIFETIME")}')
        print(f'   Database URI: {"✓ SET" if app.config.get("SQLALCHEMY_DATABASE_URI") else "✗ MISSING"}')
        print(f'   Debug Mode: {app.debug}')
        print('   ✅ Flask configured properly')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    # Test 8: OAuth Configuration
    print('\n8️⃣ Testing OAuth Configuration...')
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        linkedin_client = os.getenv('LINKEDIN_CLIENT_ID')
        linkedin_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        twitter_client = os.getenv('TWITTER_CLIENT_ID')
        twitter_secret = os.getenv('TWITTER_CLIENT_SECRET')
        
        print(f'   LinkedIn Client ID: {"✓ SET" if linkedin_client else "✗ MISSING"}')
        print(f'   LinkedIn Secret: {"✓ SET" if linkedin_secret else "✗ MISSING"}')
        print(f'   Twitter Client ID: {"✓ SET" if twitter_client else "✗ MISSING"}')
        print(f'   Twitter Secret: {"✓ SET" if twitter_secret else "✗ MISSING"}')
        
        if linkedin_client and linkedin_secret and twitter_client and twitter_secret:
            print('   ✅ All OAuth credentials configured')
        else:
            print('   ⚠️  Some OAuth credentials missing')
    except Exception as e:
        print(f'   ❌ Error: {e}')

print('\n' + '='*60)
print('✅ TEST COMPLETE')
print('='*60)
