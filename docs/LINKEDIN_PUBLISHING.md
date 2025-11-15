# LinkedIn Publishing Integration

## Overview
This document explains how posts are published to LinkedIn in the Social Media Management System.

## How It Works

### 1. Immediate Publishing ("Post Now")
When a manager clicks "Post Now":
1. Post is created with `status='published'`
2. System immediately calls LinkedIn API via `publish_to_linkedin()`
3. Post appears on LinkedIn within seconds
4. Database is updated to reflect published status

**Code Flow:**
```
create_post() → status='published' → publish_to_platform() → publish_to_linkedin() → LinkedIn API
```

### 2. Scheduled Publishing
When a post is scheduled:
1. Post is created with `status='scheduled'` (if manager) or `status='pending'` (if user)
2. For pending posts: Manager must approve first
3. Once scheduled: `check_and_publish_scheduled_posts()` runs periodically
4. When scheduled time arrives, system publishes to LinkedIn
5. Post status updates to `published`

**Code Flow:**
```
create_post() → status='scheduled' → wait for scheduled_time → 
check_and_publish_scheduled_posts() → publish_to_platform() → 
publish_to_linkedin() → LinkedIn API
```

### 3. Approval Workflow (Regular Users)
When a regular user clicks "Post Now" or "Schedule Post":
1. Post is created with `status='pending'`
2. Manager sees it in Team Collaboration page
3. Manager approves the post
4. If scheduled: Post status becomes `scheduled`, waits for time
5. If immediate: Post status becomes `approved`, can be published manually
6. System publishes when scheduled time arrives

## LinkedIn API Integration

### Authentication
- Uses OAuth 2.0 access tokens stored in `linked_account.access_token`
- Tokens are obtained during the LinkedIn OAuth flow
- Tokens must have `w_member_social` scope for posting

### Publishing Process

#### Step 1: Get LinkedIn User ID
```python
GET https://api.linkedin.com/v2/userinfo
Authorization: Bearer {access_token}
```

Returns user's `sub` (LinkedIn ID)

#### Step 2: Create UGC Post
```python
POST https://api.linkedin.com/v2/ugcPosts
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "author": "urn:li:person:{linkedin_id}",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": "Your post content here"
            },
            "shareMediaCategory": "NONE"
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}
```

Returns `201 Created` with post ID on success

### Key Functions

#### `publish_to_linkedin(post, account)`
- **Purpose**: Publish a single post to LinkedIn
- **Parameters**: 
  - `post`: Post object with content_text
  - `account`: LinkedAccount object with access_token
- **Returns**: `(success: bool, post_id_or_error: str)`

#### `publish_to_platform(post, account)`
- **Purpose**: Route to appropriate platform publisher
- **Supports**: LinkedIn, Twitter/X (coming soon)
- **Returns**: `(success: bool, result: str)`

#### `check_and_publish_scheduled_posts()`
- **Purpose**: Background job to publish scheduled posts
- **Frequency**: Called on every page load (TODO: Use scheduler like APScheduler)
- **Process**:
  1. Find all posts with `status='scheduled'` and `scheduled_time <= now()`
  2. For each post, call `publish_to_platform()`
  3. Update database status to `published` or `failed`

## Error Handling

### Common Errors

1. **"Failed to get LinkedIn user info"**
   - **Cause**: Invalid or expired access token
   - **Solution**: Re-authenticate with LinkedIn

2. **"LinkedIn user ID not found"**
   - **Cause**: API response missing `sub` field
   - **Solution**: Check OAuth scopes

3. **"Status 401: Unauthorized"**
   - **Cause**: Access token expired or invalid
   - **Solution**: Refresh token or re-authenticate

4. **"Status 403: Forbidden"**
   - **Cause**: Missing `w_member_social` scope
   - **Solution**: Re-link account with correct permissions

5. **"LinkedIn API request timed out"**
   - **Cause**: Network issues or LinkedIn API slow
   - **Solution**: Retry after a few seconds

### Failed Posts
- Posts that fail to publish are marked with `status='failed'`
- Error message is logged in Flask console
- Manager can see failed posts in Team Collaboration
- Can retry publishing manually (TODO: Add retry button)

## Database Schema

### Post Table
```sql
post_id INT PRIMARY KEY
status ENUM('draft', 'pending', 'approved', 'scheduled', 'published', 'rejected')
content_text TEXT
media_url VARCHAR(255)
```

### ScheduledPost Table
```sql
schedule_id INT PRIMARY KEY
post_id INT (FK)
platform_id INT (FK)
scheduled_time DATETIME
status ENUM('pending', 'scheduled', 'published', 'failed')
published_at DATETIME
```

### LinkedAccount Table
```sql
account_id INT PRIMARY KEY
user_id INT (FK)
platform_id INT (FK)
access_token TEXT  -- LinkedIn OAuth token
refresh_token TEXT
token_expires_at DATETIME
```

## Testing

### Test Immediate Publishing
1. Login as manager
2. Go to "Create & Schedule Posts"
3. Link your LinkedIn account
4. Write a test post
5. Select LinkedIn platform
6. Click "Post Now"
7. Check your LinkedIn profile - post should appear

### Test Scheduled Publishing
1. Login as manager
2. Create a post
3. Set scheduled time to 2 minutes from now
4. Click "Schedule Post"
5. Wait for 2 minutes
6. Refresh any page (triggers `check_and_publish_scheduled_posts()`)
7. Check LinkedIn - post should appear

### Test Approval Workflow
1. Login as regular user
2. Create a post and click "Post Now" or "Schedule Post"
3. Post status should be 'pending'
4. Logout and login as manager
5. Go to Team Collaboration
6. See pending post with "Requested schedule for" or "Post Now requested"
7. Click "Approve"
8. Post should be published or scheduled

## Future Improvements

### 1. Background Scheduler
Replace page-load trigger with APScheduler:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    check_and_publish_scheduled_posts,
    'interval',
    minutes=1
)
scheduler.start()
```

### 2. Media Support
Add image/video uploading to LinkedIn:
- Register media upload
- Upload media binary
- Attach media URN to post

### 3. Token Refresh
Implement automatic token refresh:
```python
if token_expires_at < now():
    new_token = refresh_linkedin_token(refresh_token)
    account.access_token = new_token
    account.token_expires_at = now() + timedelta(seconds=expires_in)
```

### 4. Retry Failed Posts
Add "Retry" button in Team Collaboration:
```python
@app.route('/api/posts/<post_id>/retry', methods=['POST'])
def retry_post(post_id):
    post = Post.query.get(post_id)
    # Re-attempt publishing
```

### 5. Post Analytics
Track LinkedIn post engagement:
- Impressions
- Likes
- Comments
- Shares

## Troubleshooting

### Posts Not Publishing
1. Check Flask console for error messages
2. Verify LinkedIn account is linked (`linked_accounts` table)
3. Check access token is valid
4. Ensure `scheduled_time` is in the past
5. Verify `status='scheduled'` in database

### LinkedIn Authentication Issues
1. Check OAuth redirect URI matches exactly
2. Verify client ID and secret in `.env` file
3. Ensure scopes include `w_member_social`
4. Check token hasn't expired

### Database Issues
1. Run `python update_db_schema.py` to update schema
2. Check `scheduled_post.status` has 'pending' in ENUM
3. Verify foreign keys are correct

## Support

For LinkedIn API documentation:
- [LinkedIn API Docs](https://docs.microsoft.com/en-us/linkedin/)
- [Share on LinkedIn](https://docs.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/share-api)
- [UGC Posts API](https://docs.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api)

## Logs & Debugging

Enable verbose logging in Flask console:
```python
print(f"🔵 Publishing to LinkedIn for account {account.account_id}")
print(f"✅ Got LinkedIn ID: {linkedin_id}")
print(f"📤 Sending post to LinkedIn API...")
print(f"✅ Successfully published to LinkedIn! Post ID: {linkedin_post_id}")
```

All publishing operations are logged with emojis for easy scanning:
- 🔵 LinkedIn operation started
- ✅ Success
- ❌ Error
- ⚠️ Warning
- 📤 API request sent
- 📊 Results summary
