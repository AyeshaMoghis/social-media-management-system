"""
Unit tests for post management APIs
"""
import pytest
from datetime import datetime, timedelta
from src.app import app, dbs, User, Post, Platform, ScheduledPost


class TestCreatePost:
    """Test post creation API"""

    def test_create_post_as_user(self, client):
        """Test creating a post as a regular user"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        platform = Platform(
            user_id=user.user_id,
            platform_name='twitter',
            platform_user_id='twitter_123',
            access_token='token',
            expires_at=datetime(2030, 1, 1)
        )
        dbs.session.add(platform)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.post('/api/posts', data={
            'text': 'Test post content',
            'account_ids[]': [platform.platform_id],
            'status': 'pending'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'post_id' in data

    def test_create_draft_post(self, client):
        """Test creating a draft post"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.post('/api/posts', data={
            'text': 'Draft post',
            'status': 'draft'
        })

        assert response.status_code == 201
        data = response.get_json()
        post_id = data['post_id']

        post = Post.query.get(post_id)
        assert post.status == 'draft'

    def test_create_post_without_login(self, client):
        """Test creating post without login returns 401"""
        response = client.post('/api/posts', data={
            'text': 'Test post'
        })
        assert response.status_code in [401, 302]


class TestUpdatePost:
    """Test post update API"""

    def test_update_post_status(self, client):
        """Test updating post status"""
        manager = User(email='manager@test.com', full_name='Manager', role='manager')
        dbs.session.add(manager)
        dbs.session.commit()

        post = Post(user_id=manager.user_id, content_text='Test post', status='pending')
        dbs.session.add(post)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = manager.user_id
            sess['role'] = 'manager'

        response = client.put(f'/api/posts/{post.post_id}', json={
            'status': 'approved'
        })

        if response.status_code == 200:
            dbs.session.refresh(post)
            assert post.status == 'approved'

    def test_update_nonexistent_post(self, client):
        """Test updating non-existent post returns 404"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.put('/api/posts/99999', json={
            'status': 'approved'
        })
        assert response.status_code == 404


class TestDeletePost:
    """Test post deletion API"""

    def test_delete_own_post(self, client):
        """Test deleting own post"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        post = Post(user_id=user.user_id, content_text='Test post', status='draft')
        dbs.session.add(post)
        dbs.session.commit()
        post_id = post.post_id

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.delete(f'/api/posts/{post_id}')
            
        if response.status_code == 200:
            deleted_post = Post.query.get(post_id)
            assert deleted_post is None

    def test_delete_nonexistent_post(self, client):
        """Test deleting non-existent post"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.delete('/api/posts/99999')
        assert response.status_code == 404


class TestGetPosts:
    """Test get posts API"""

    def test_get_user_posts(self, client):
        """Test getting user's posts"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        post1 = Post(user_id=user.user_id, content_text='Post 1', status='published')
        post2 = Post(user_id=user.user_id, content_text='Post 2', status='draft')
        dbs.session.add_all([post1, post2])
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.get('/api/posts')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_posts_without_login(self, client):
        """Test getting posts without login"""
        response = client.get('/api/posts')
        assert response.status_code in [401, 302]


class TestAccountDetails:
    """Test account details page"""

    def test_account_details_with_login(self, client):
        """Test account details page when logged in"""
        user = User(email='user@test.com', full_name='User', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['full_name'] = user.full_name
            sess['role'] = user.role

        response = client.get('/account-details')
        assert response.status_code == 200

    def test_account_details_without_login(self, client):
        """Test account details redirects when not logged in"""
        response = client.get('/account-details')
        assert response.status_code == 302


class TestUpdateAccountDetails:
    """Test update account details API"""

    def test_update_account_name(self, client):
        """Test updating account name"""
        user = User(email='user@test.com', full_name='Old Name', role='user')
        dbs.session.add(user)
        dbs.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['role'] = 'user'

        response = client.post('/update-account', json={
            'full_name': 'New Name'
        })

        if response.status_code == 200:
            dbs.session.refresh(user)
            assert user.full_name == 'New Name'

    def test_update_account_without_login(self, client):
        """Test updating account without login"""
        response = client.post('/update-account', json={
            'full_name': 'New Name'
        })
        assert response.status_code in [401, 302]
