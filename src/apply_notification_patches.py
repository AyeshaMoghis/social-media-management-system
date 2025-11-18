#!/usr/bin/env python3
"""
Auto-patch script for SMMS Notification Integration
This script automatically adds notification code to your existing app.py

Usage:
    python apply_notification_patches.py

This will:
1. Read your app.py
2. Add notification imports
3. Add notification routes
4. Add notification triggers to existing functions
5. Create app_with_notifications.py (leaves original untouched)

Prerequisites:
- app.py must be in the same directory
- src/notification_helper.py must exist
"""

import re
import os
import shutil
from datetime import datetime

def backup_file(filename):
    """Create a backup of the original file"""
    backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(filename, backup_name)
    print(f"✅ Created backup: {backup_name}")
    return backup_name

def read_file(filename):
    """Read file content"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filename, content):
    """Write content to file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Written: {filename}")

def add_imports(content):
    """Add notification helper imports at the top"""
    
    # Find the imports section - after 'import requests'
    import_code = '''
# Import notification helper
try:
    from notification_helper import (
        notify_post_created,
        notify_post_published,
        notify_post_scheduled,
        notify_post_deleted,
        notify_post_edited,
        notify_account_linked,
        notify_account_unlinked,
        notify_approval_request,
        notify_post_approved,
        notify_post_rejected
    )
    NOTIFICATIONS_ENABLED = True
    print("✅ Notification helper loaded")
except ImportError:
    NOTIFICATIONS_ENABLED = False
    print("⚠️ Notification helper not found - notifications disabled")
'''
    
    # Insert after 'import requests' line
    if 'import requests' in content and 'NOTIFICATIONS_ENABLED' not in content:
        content = content.replace(
            'import requests\n',
            'import requests\n' + import_code
        )
        print("✅ Added notification imports")
    else:
        print("⚠️ Imports already added or 'import requests' not found")
    
    return content

def add_current_user_route(content):
    """Add /api/current-user endpoint"""
    
    route_code = '''
@app.route('/api/current-user', methods=['GET'])
def get_current_user():
    """Get current logged-in user info for frontend"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    return jsonify({
        'user_id': session.get('user_id'),
        'full_name': session.get('full_name', 'User'),
        'email': session.get('email', ''),
        'role': session.get('role', 'user')
    }), 200


'''
    
    if 'def get_current_user' not in content:
        # Add before the background scheduler section
        if '# ---------------------------\n# BACKGROUND SCHEDULER' in content:
            content = content.replace(
                '# ---------------------------\n# BACKGROUND SCHEDULER',
                route_code + '# ---------------------------\n# BACKGROUND SCHEDULER'
            )
            print("✅ Added /api/current-user route")
        else:
            print("⚠️ Could not find BACKGROUND SCHEDULER section")
    else:
        print("⚠️ /api/current-user route already exists")
    
    return content

def add_notifications_page_route(content):
    """Add /notifications page route"""
    
    route_code = '''
@app.route('/notifications')
def notifications_page():
    """Serve the notifications page"""
    if 'user_id' not in session:
        flash("Please log in first", "warning")
        return redirect(url_for('auth.login'))
    return render_template('notifications.html')


'''
    
    if 'def notifications_page' not in content:
        # Add after get_current_user
        if 'def get_current_user' in content:
            # Find the end of get_current_user function
            pattern = r"(def get_current_user\(\):.*?return jsonify\(\{[^}]+\}\), 200\n)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                content = content.replace(
                    match.group(1),
                    match.group(1) + '\n\n' + route_code
                )
                print("✅ Added /notifications route")
        else:
            print("⚠️ Add get_current_user first")
    else:
        print("⚠️ /notifications route already exists")
    
    return content

def add_create_post_notifications(content):
    """Add notifications to create_post function"""
    
    # Find the commit block in create_post
    search = '''        print(f"✅ Committing to database...")
        dbs.session.commit()
        print(f"✅ Post committed successfully!")'''
    
    replacement = '''        print(f"✅ Committing to database...")
        dbs.session.commit()
        print(f"✅ Post committed successfully!")

        # Send notification for post creation
        if NOTIFICATIONS_ENABLED:
            try:
                notify_post_created(user_id, post.post_id, final_status)
            except Exception as e:
                print(f"⚠️ Failed to send creation notification: {e}")'''
    
    if search in content and 'notify_post_created(user_id, post.post_id' not in content:
        content = content.replace(search, replacement)
        print("✅ Added notification to create_post")
    else:
        print("⚠️ create_post notification already added or block not found")
    
    return content

def add_publish_success_notification(content):
    """Add notification for successful publish"""
    
    search = '''                            pp.published = True
                            pp.published_at = datetime.now()
                        published_count += 1
                        print(f"✅ Published to platform {account.platform_id}")'''
    
    replacement = '''                            pp.published = True
                            pp.published_at = datetime.now()
                        published_count += 1
                        print(f"✅ Published to platform {account.platform_id}")
                        # Notify success
                        if NOTIFICATIONS_ENABLED:
                            platform = dbs.session.get(Platform, account.platform_id)
                            notify_post_published(user_id, post.post_id, platform.platform_name if platform else "Platform", True)'''
    
    if search in content and 'notify_post_published(user_id, post.post_id, platform.platform_name' not in content:
        content = content.replace(search, replacement)
        print("✅ Added publish success notification")
    else:
        print("⚠️ Publish success notification already added or block not found")
    
    return content

def add_publish_failure_notification(content):
    """Add notification for failed publish"""
    
    search = '''                    else:
                        failed_count += 1
                        print(f"❌ Failed to publish to platform {account.platform_id}: {result}")'''
    
    replacement = '''                    else:
                        failed_count += 1
                        print(f"❌ Failed to publish to platform {account.platform_id}: {result}")
                        # Notify failure
                        if NOTIFICATIONS_ENABLED:
                            platform = dbs.session.get(Platform, account.platform_id)
                            notify_post_published(user_id, post.post_id, platform.platform_name if platform else "Platform", False, str(result))'''
    
    if search in content and 'notify_post_published(user_id, post.post_id' not in content:
        content = content.replace(search, replacement)
        print("✅ Added publish failure notification")
    
    return content

def add_delete_post_notification(content):
    """Add notification to delete_post"""
    
    search = '''        print(f"✅ Post {post_id} deleted from database")
        print(f"{'='*60}\\n")

        # Return results including platform deletion status
        return jsonify({
            'message': 'Post deleted successfully',
            'platform_deletions': deletion_results
        }), 200'''
    
    replacement = '''        print(f"✅ Post {post_id} deleted from database")
        print(f"{'='*60}\\n")

        # Notify deletion
        if NOTIFICATIONS_ENABLED:
            try:
                notify_post_deleted(user_id, post_id)
            except Exception as e:
                print(f"⚠️ Failed to send deletion notification: {e}")

        # Return results including platform deletion status
        return jsonify({
            'message': 'Post deleted successfully',
            'platform_deletions': deletion_results
        }), 200'''
    
    if search in content and 'notify_post_deleted(user_id, post_id)' not in content:
        content = content.replace(search, replacement)
        print("✅ Added notification to delete_post")
    else:
        print("⚠️ delete_post notification already added or block not found")
    
    return content

def add_linkedin_callback_notification(content):
    """Add notification to linkedin_callback"""
    
    search = '''            session.permanent = True
            session.modified = True
            print(f" Session restored for user {user.user_id}")

        # TEST EXPECTATION 5:
        # Must redirect on success
        return redirect("/linked-accounts")'''
    
    replacement = '''            session.permanent = True
            session.modified = True
            print(f" Session restored for user {user.user_id}")

        # Notify account linked
        if NOTIFICATIONS_ENABLED:
            try:
                notify_account_linked(user_id, "LinkedIn")
            except Exception as e:
                print(f"⚠️ Failed to send link notification: {e}")

        # TEST EXPECTATION 5:
        # Must redirect on success
        return redirect("/linked-accounts")'''
    
    if search in content and 'notify_account_linked(user_id, "LinkedIn")' not in content:
        content = content.replace(search, replacement)
        print("✅ Added notification to linkedin_callback")
    else:
        print("⚠️ linkedin_callback notification already added or block not found")
    
    return content

def add_twitter_callback_notification(content):
    """Add notification to callback_twitter"""
    
    search = '''        print(f" Twitter account linked successfully: {name} (@{username})")
        flash(f"Successfully connected Twitter account: {name} (@{username})", "success")

        return redirect(url_for("linked_accounts"))'''
    
    replacement = '''        print(f" Twitter account linked successfully: {name} (@{username})")
        flash(f"Successfully connected Twitter account: {name} (@{username})", "success")

        # Notify account linked
        if NOTIFICATIONS_ENABLED:
            try:
                notify_account_linked(user_id, "Twitter")
            except Exception as e:
                print(f"⚠️ Failed to send link notification: {e}")

        return redirect(url_for("linked_accounts"))'''
    
    if search in content and 'notify_account_linked(user_id, "Twitter")' not in content:
        content = content.replace(search, replacement)
        print("✅ Added notification to callback_twitter")
    else:
        print("⚠️ Twitter callback notification already added or block not found")
    
    return content

def add_disconnect_notification(content):
    """Add notification to disconnect_account"""
    
    search = '''    if acc:
        dbs.session.delete(acc)
        dbs.session.commit()
        print(f"✅ Disconnected account {account_id}")

    return redirect(url_for('linked_accounts'))'''
    
    replacement = '''    if acc:
        platform = dbs.session.get(Platform, acc.platform_id)
        platform_name = platform.platform_name if platform else "Account"
        dbs.session.delete(acc)
        dbs.session.commit()
        print(f"✅ Disconnected account {account_id}")

        # Notify account unlinked
        if NOTIFICATIONS_ENABLED:
            try:
                notify_account_unlinked(user_id, platform_name)
            except Exception as e:
                print(f"⚠️ Failed to send unlink notification: {e}")

    return redirect(url_for('linked_accounts'))'''
    
    if search in content and 'notify_account_unlinked(user_id' not in content:
        content = content.replace(search, replacement)
        print("✅ Added notification to disconnect_account")
    else:
        print("⚠️ disconnect_account notification already added or block not found")
    
    return content

def main():
    print("=" * 60)
    print("  SMMS Notification Auto-Patcher")
    print("=" * 60)
    print()
    
    # Check if app.py exists
    if not os.path.exists('app.py'):
        print("❌ ERROR: app.py not found in current directory!")
        print("   Make sure you run this script from your project folder.")
        return
    
    # Check if notification helper exists
    if not os.path.exists('src/notification_helper.py'):
        print("⚠️ WARNING: src/notification_helper.py not found!")
        print("   Notifications will be disabled until you add it.")
    
    # Create backup
    print("📦 Creating backup of original app.py...")
    backup_file('app.py')
    print()
    
    # Read original file
    print("📖 Reading app.py...")
    content = read_file('app.py')
    original_size = len(content)
    print(f"   Original size: {original_size:,} bytes")
    print()
    
    # Apply patches
    print("🔧 Applying patches...")
    print("-" * 40)
    
    content = add_imports(content)
    content = add_current_user_route(content)
    content = add_notifications_page_route(content)
    content = add_create_post_notifications(content)
    content = add_publish_success_notification(content)
    content = add_publish_failure_notification(content)
    content = add_delete_post_notification(content)
    content = add_linkedin_callback_notification(content)
    content = add_twitter_callback_notification(content)
    content = add_disconnect_notification(content)
    
    print("-" * 40)
    print()
    
    # Write new file
    new_size = len(content)
    print(f"📝 Writing patched file...")
    print(f"   New size: {new_size:,} bytes (+{new_size - original_size:,} bytes)")
    
    # Ask user whether to overwrite or create new file
    print()
    print("Options:")
    print("  1. Create app_with_notifications.py (safe, original unchanged)")
    print("  2. Overwrite app.py (backup already created)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "2":
        write_file('app.py', content)
        print("\n✅ app.py has been patched!")
    else:
        write_file('app_with_notifications.py', content)
        print("\n✅ app_with_notifications.py created!")
        print("   To use it, rename it to app.py or run:")
        print("   python app_with_notifications.py")
    
    print()
    print("=" * 60)
    print("  Patching Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Make sure src/notification_helper.py exists")
    print("2. Make sure templates/notifications.html exists")
    print("3. Make sure static/notification_*.* files exist")
    print("4. Run: python notifapp.py (Terminal 1, port 5001)")
    print("5. Run: python app.py (Terminal 2, port 5000)")
    print("6. Visit: http://127.0.0.1:5000/notifications")

if __name__ == "__main__":
    main()
