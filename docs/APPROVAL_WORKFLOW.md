# Post Scheduler to Team Collaboration Approval Workflow

## Overview
Connected the post scheduler to team collaboration approval workflow. Now when users schedule posts, they need manager approval before being published.

## Changes Made

### 1. Post Status Flow (src/app.py)

**For Regular Users:**
- Draft → stays as `draft` (no approval needed)
- Schedule/Publish Now → changes to `pending` (requires manager approval)

**For Managers:**
- Can directly publish or schedule without approval

### 2. Updated create_post() Function
```python
# Users creating posts
if status == 'draft':
    final_status = 'draft'
elif user_role == 'manager':
    final_status = 'published' or 'scheduled' (direct)
else:
    final_status = 'pending' (needs approval)
```

### 3. Updated update_post_status() Function
When manager approves a pending post:
- **With scheduled_time**: Changes to `'scheduled'` status
- **Without scheduled_time**: Changes to `'approved'` status
- Scheduled post status also updated accordingly

### 4. ScheduledPost Model Update
```python
# Added 'pending' to status ENUM
status = ENUM('pending', 'scheduled', 'published', 'failed')
```

### 5. Database Schema Update
```sql
ALTER TABLE scheduled_post 
MODIFY COLUMN status ENUM('pending', 'scheduled', 'published', 'failed') 
DEFAULT 'scheduled';
```

### 6. Team Collaboration Template
- Shows scheduled time for both pending and scheduled posts
- Different color coding:
  - Orange (#f59e0b) for pending posts with requested schedule
  - Green (#059669) for approved scheduled posts

## Workflow Example

### User Creates Scheduled Post:
1. User fills out post in post scheduler
2. Selects date/time for scheduling
3. Clicks "Schedule Post"
4. **Post is created with status='pending'**
5. **ScheduledPost entry created with status='pending'**
6. Post appears in Team Collaboration for manager review

### Manager Reviews:
1. Manager sees post in Team Collaboration
2. Can see: "Requested schedule for: Nov 15, 2025 at 10:00 AM"
3. Manager clicks "✓ Approve"
4. **Post status changes to 'scheduled'**
5. **ScheduledPost status changes to 'scheduled'**
6. Auto-publish function will publish at scheduled time

### Manager Rejects:
1. Manager clicks "✗ Reject"
2. Post status changes to 'rejected'
3. ScheduledPost status changes to 'failed'
4. Post will not be published

## Benefits

✅ **Approval Control**: All user posts need manager approval before publishing
✅ **Schedule Visibility**: Managers can see requested schedule times
✅ **Status Tracking**: Clear status transitions (pending → scheduled → published)
✅ **Manager Override**: Managers can directly publish without approval
✅ **Audit Trail**: All scheduled posts tracked with timestamps

## Testing Checklist

- [ ] User creates draft - stays as draft ✓
- [ ] User schedules post - goes to pending ✓
- [ ] User publishes now - goes to pending ✓
- [ ] Manager approves scheduled post - changes to scheduled ✓
- [ ] Manager approves immediate post - changes to approved ✓
- [ ] Manager rejects post - changes to rejected ✓
- [ ] Auto-publish runs for scheduled posts ✓
- [ ] Team collaboration shows all pending posts ✓
- [ ] Team collaboration shows scheduled time ✓

## Files Modified

1. `src/app.py` - Main backend logic
2. `src/templates/team_collaboration.html` - Display scheduled time
3. `update_db_schema.py` - Database migration script
4. `DATABASE_UPDATE.sql` - SQL migration documentation

## Next Steps

1. Restart Flask server
2. Test the workflow end-to-end
3. Commit changes to feature branch
4. Create pull request
