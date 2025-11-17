"""
Comprehensive System Test - Social Media Management System
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_tests():
    print('='*70)
    print('🧪 SOCIAL MEDIA MANAGEMENT SYSTEM - COMPREHENSIVE TEST')
    print('='*70)
    
    try:
        from app import app, dbs, User, LinkedAccount, Post, ScheduledPost, Platform
        from datetime import datetime, timedelta
        
        with app.app_context():
            # Test 1: Database Connection
            print('\n1️⃣  DATABASE CONNECTION')
            print('-' * 70)
            try:
                user_count = User.query.count()
                print(f'✅ Database connected successfully')
                print(f'   Total users in system: {user_count}')
            except Exception as e:
                print(f'❌ Database connection failed: {e}')
                return
            
            # Test 2: User Accounts
            print('\n2️⃣  USER ACCOUNTS')
            print('-' * 70)
            try:
                manager = User.query.filter_by(email='manager@test.com').first()
                regular_user = User.query.filter_by(email='user@test.com').first()
                
                if manager:
                    print(f'✅ Manager Account Found')
                    print(f'   Email: {manager.email}')
                    print(f'   Name: {manager.full_name}')
                    print(f'   Role: {manager.role}')
                    print(f'   User ID: {manager.user_id}')
                else:
                    print(f'❌ Manager account (manager@test.com) NOT FOUND')
                
                if regular_user:
                    print(f'\n✅ Regular User Account Found')
                    print(f'   Email: {regular_user.email}')
                    print(f'   Name: {regular_user.full_name}')
                    print(f'   Role: {regular_user.role}')
                    print(f'   User ID: {regular_user.user_id}')
                else:
                    print(f'❌ Regular user account (user@test.com) NOT FOUND')
                    
            except Exception as e:
                print(f'❌ Error checking users: {e}')
            
            # Test 3: Social Media Platforms
            print('\n3️⃣  SOCIAL MEDIA PLATFORMS')
            print('-' * 70)
            try:
                platforms = Platform.query.all()
                print(f'✅ Found {len(platforms)} platform(s) configured:')
                for p in platforms:
                    print(f'   • {p.platform_name} (ID: {p.platform_id}, Active: {p.is_active})')
                    print(f'     API Endpoint: {p.api_endpoint}')
            except Exception as e:
                print(f'❌ Error checking platforms: {e}')
            
            # Test 4: Linked Accounts (CRITICAL TEST)
            print('\n4️⃣  LINKED SOCIAL MEDIA ACCOUNTS')
            print('-' * 70)
            try:
                all_accounts = LinkedAccount.query.all()
                print(f'✅ Total linked accounts in database: {len(all_accounts)}')
                
                if len(all_accounts) == 0:
                    print('⚠️  No accounts linked yet!')
                else:
                    print('\n📋 Detailed Account Information:')
                    for i, acc in enumerate(all_accounts, 1):
                        user = User.query.get(acc.user_id)
                        platform = Platform.query.get(acc.platform_id)
                        
                        print(f'\n   Account #{i}:')
                        print(f'   ├─ User: {user.email if user else "Unknown"} ({user.full_name if user else "N/A"})')
                        print(f'   ├─ Platform: {platform.platform_name if platform else "Unknown"}')
                        print(f'   ├─ Username: {acc.account_username}')
                        print(f'   ├─ Has Token: {"✓ YES" if acc.access_token else "✗ NO"}')
                        if acc.access_token:
                            token_preview = acc.access_token[:15] + '...' if len(acc.access_token) > 15 else acc.access_token
                            print(f'   ├─ Token Preview: {token_preview}')
                        print(f'   ├─ Linked At: {acc.linked_at}')
                        print(f'   ├─ Last Synced: {acc.last_synced}')
                        print(f'   ├─ Followers: {acc.follower_count}')
                        print(f'   └─ Posts: {acc.post_count}')
                
                # Check manager's accounts specifically
                if manager:
                    manager_accounts = LinkedAccount.query.filter_by(user_id=manager.user_id).all()
                    print(f'\n📊 Manager ({manager.email}) has {len(manager_accounts)} linked account(s):')
                    for acc in manager_accounts:
                        platform = Platform.query.get(acc.platform_id)
                        print(f'   • {platform.platform_name if platform else "Unknown"} - {acc.account_username}')
                
            except Exception as e:
                print(f'❌ Error checking linked accounts: {e}')
            
            # Test 5: Posts
            print('\n5️⃣  POSTS')
            print('-' * 70)
            try:
                all_posts = Post.query.all()
                print(f'✅ Total posts in database: {len(all_posts)}')
                
                if len(all_posts) > 0:
                    status_counts = {}
                    for post in all_posts:
                        status_counts[post.status] = status_counts.get(post.status, 0) + 1
                    
                    print('\n📊 Posts by Status:')
                    for status, count in status_counts.items():
                        print(f'   • {status.upper()}: {count}')
                    
                    # Show recent posts
                    recent = Post.query.order_by(Post.created_at.desc()).limit(3).all()
                    print(f'\n📝 Most Recent Posts:')
                    for i, post in enumerate(recent, 1):
                        user = User.query.get(post.user_id)
                        content_preview = post.content_text[:60] + '...' if len(post.content_text) > 60 else post.content_text
                        print(f'   {i}. [{post.status.upper()}] {content_preview}')
                        print(f'      By: {user.email if user else "Unknown"} | Created: {post.created_at}')
                else:
                    print('⚠️  No posts created yet!')
                    
            except Exception as e:
                print(f'❌ Error checking posts: {e}')
            
            # Test 6: Scheduled Posts
            print('\n6️⃣  SCHEDULED POSTS')
            print('-' * 70)
            try:
                all_scheduled = ScheduledPost.query.all()
                print(f'✅ Total scheduled posts: {len(all_scheduled)}')
                
                if len(all_scheduled) > 0:
                    now = datetime.now()
                    past_due = [s for s in all_scheduled if s.scheduled_time and s.scheduled_time < now and s.status == 'scheduled']
                    upcoming = [s for s in all_scheduled if s.scheduled_time and s.scheduled_time > now and s.status == 'scheduled']
                    
                    print(f'\n📊 Scheduled Post Status:')
                    print(f'   • Past Due (should auto-publish): {len(past_due)}')
                    print(f'   • Upcoming: {len(upcoming)}')
                    print(f'   • Total: {len(all_scheduled)}')
                    
                    if past_due:
                        print(f'\n⚠️  Posts that should have published:')
                        for sp in past_due[:3]:
                            post = Post.query.get(sp.post_id)
                            if post:
                                print(f'   • Post ID {sp.post_id}: Scheduled for {sp.scheduled_time}')
                                print(f'     Status: {sp.status} | Content: {post.content_text[:50]}...')
                    
                    if upcoming:
                        print(f'\n📅 Upcoming Posts:')
                        for sp in upcoming[:3]:
                            post = Post.query.get(sp.post_id)
                            if post:
                                time_until = sp.scheduled_time - now
                                minutes = int(time_until.total_seconds() / 60)
                                print(f'   • Post ID {sp.post_id}: In {minutes} minutes ({sp.scheduled_time})')
                else:
                    print('⚠️  No scheduled posts!')
                    
            except Exception as e:
                print(f'❌ Error checking scheduled posts: {e}')
            
            # Test 7: Flask Configuration
            print('\n7️⃣  FLASK CONFIGURATION')
            print('-' * 70)
            try:
                print(f'✅ Flask App Configuration:')
                print(f'   • Secret Key: {"✓ SET" if app.secret_key else "✗ MISSING"}')
                print(f'   • Session Lifetime: {app.config.get("PERMANENT_SESSION_LIFETIME")}')
                print(f'   • Debug Mode: {app.debug}')
                print(f'   • Database: {"✓ CONFIGURED" if app.config.get("SQLALCHEMY_DATABASE_URI") else "✗ MISSING"}')
                print(f'   • Session Cookie SameSite: {app.config.get("SESSION_COOKIE_SAMESITE")}')
                print(f'   • Session Cookie Secure: {app.config.get("SESSION_COOKIE_SECURE")}')
            except Exception as e:
                print(f'❌ Error checking Flask config: {e}')
            
            # Test 8: OAuth Configuration
            print('\n8️⃣  OAUTH CREDENTIALS')
            print('-' * 70)
            try:
                from dotenv import load_dotenv
                load_dotenv()
                
                linkedin_client = os.getenv('LINKEDIN_CLIENT_ID')
                linkedin_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
                linkedin_redirect = os.getenv('LINKEDIN_REDIRECT_URI')
                twitter_client = os.getenv('TWITTER_CLIENT_ID')
                twitter_secret = os.getenv('TWITTER_CLIENT_SECRET')
                
                print(f'LinkedIn OAuth:')
                print(f'   • Client ID: {"✓ SET (" + linkedin_client[:20] + "...)" if linkedin_client else "✗ MISSING"}')
                print(f'   • Client Secret: {"✓ SET" if linkedin_secret else "✗ MISSING"}')
                print(f'   • Redirect URI: {linkedin_redirect if linkedin_redirect else "✗ MISSING"}')
                
                print(f'\nTwitter OAuth:')
                print(f'   • Client ID: {"✓ SET (" + twitter_client[:20] + "...)" if twitter_client else "✗ MISSING"}')
                print(f'   • Client Secret: {"✓ SET" if twitter_secret else "✗ MISSING"}')
                
                all_configured = linkedin_client and linkedin_secret and twitter_client and twitter_secret
                if all_configured:
                    print(f'\n✅ All OAuth credentials configured')
                else:
                    print(f'\n⚠️  Some OAuth credentials missing')
                    
            except Exception as e:
                print(f'❌ Error checking OAuth config: {e}')
            
            # Test 9: Server Status
            print('\n9️⃣  SERVER STATUS')
            print('-' * 70)
            try:
                import requests
                response = requests.get('http://127.0.0.1:5000', timeout=2)
                print(f'✅ Flask server is running!')
                print(f'   • Status Code: {response.status_code}')
                print(f'   • Server accessible at: http://127.0.0.1:5000')
            except requests.exceptions.ConnectionError:
                print(f'❌ Flask server is NOT running!')
                print(f'   • Please start the server: python src/app.py')
            except Exception as e:
                print(f'⚠️  Could not check server: {e}')
            
            # Final Summary
            print('\n' + '='*70)
            print('📋 TEST SUMMARY')
            print('='*70)
            print(f'✅ Database: Connected')
            print(f'✅ Users: {user_count} total')
            print(f'✅ Platforms: {len(platforms) if "platforms" in locals() else 0} configured')
            print(f'✅ Linked Accounts: {len(all_accounts) if "all_accounts" in locals() else 0} total')
            print(f'✅ Posts: {len(all_posts) if "all_posts" in locals() else 0} total')
            print(f'✅ Scheduled: {len(all_scheduled) if "all_scheduled" in locals() else 0} total')
            
            # Check critical issues
            issues = []
            if manager and len(manager_accounts) == 0:
                issues.append('Manager has no linked accounts')
            if len(all_accounts) == 0:
                issues.append('No social media accounts linked')
            if not (linkedin_client and linkedin_secret):
                issues.append('LinkedIn OAuth not configured')
            if not (twitter_client and twitter_secret):
                issues.append('Twitter OAuth not configured')
            
            if issues:
                print(f'\n⚠️  WARNINGS:')
                for issue in issues:
                    print(f'   • {issue}')
            else:
                print(f'\n🎉 ALL SYSTEMS OPERATIONAL!')
            
            print('='*70)
            
    except ImportError as e:
        print(f'❌ Failed to import application modules: {e}')
        print(f'   Make sure you are running from the project root directory')
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_tests()
