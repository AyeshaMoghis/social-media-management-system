# Social Media Management System (SMMS)

**Project ID:** P10  
**Course:** UE23CS341A  
**Academic Year:** 2025  
**Semester:** 5th Sem  
**Campus:** EC  
**Branch:** AIML  
**Section:** B  
**Team:** WECODE

# Social Media Management System (SMMS)

[![CI Pipeline](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/your-repo/actions)
[![Coverage](https://img.shields.io/badge/coverage-75%25+-green)](https://github.com/your-repo)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A comprehensive Flask-based social media management platform that enables teams to schedule, manage, and publish content across multiple social media platforms (LinkedIn, Twitter/X) with built-in approval workflows and team collaboration features.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

### 🔐 Authentication & Authorization
- **Multi-method Authentication**: Email/password, Google OAuth 2.0
- **Role-based Access Control**: User and Manager roles with different permissions
- **Secure Password Reset**: OTP-based password recovery via email
- **Session Management**: Persistent sessions with 24-hour expiration

### 🔗 Social Media Integration
- **OAuth Connections**: Seamless LinkedIn and Twitter/X account linking
- **PKCE Flow**: Secure Twitter OAuth with Proof Key for Code Exchange
- **Multi-platform Publishing**: Post to multiple platforms simultaneously
- **Account Management**: Connect, refresh, and disconnect social accounts

### 📝 Content Management
- **Post Creation & Editing**: Rich text content with media support (images/videos)
- **Draft System**: Save and edit posts before publishing
- **Scheduling**: Schedule posts for future publishing with automatic execution
- **Multi-platform Posts**: Single post to multiple social networks

### 👥 Team Collaboration
- **Approval Workflow**: User posts require manager approval before publishing
- **Team Management**: Invite and manage team members
- **Post Status Tracking**: Draft → Pending → Approved/Rejected → Scheduled → Published
- **Activity Dashboard**: Real-time view of team activity and pending approvals

### 📊 Monitoring & Analytics
- **Account Metrics**: Track follower count, post count (Twitter)
- **Post Status**: Monitor published, scheduled, and pending posts
- **Background Scheduler**: Automatic publishing of scheduled posts every 30 seconds

---

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP/HTTPS
       ▼
┌─────────────────────────────────┐
│      Flask Application          │
│  ┌──────────────────────────┐   │
│  │  Routes & Controllers    │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  Authentication Module   │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  OAuth Integration       │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  Post Management         │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  Background Scheduler    │   │
│  └──────────────────────────┘   │
└───────────┬─────────────────────┘
            │
            ▼
    ┌──────────────┐
    │    MySQL     │
    │   Database   │
    └──────────────┘
            │
            ▼
┌───────────────────────────────┐
│   External APIs               │
│  - LinkedIn API               │
│  - Twitter/X API              │
│  - Google OAuth               │
└───────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3.0+
- **Database**: MySQL 8.0 / SQLite (testing)
- **ORM**: SQLAlchemy 2.0+
- **Authentication**: Werkzeug, Authlib
- **Background Jobs**: APScheduler

### Frontend
- **Templating**: Jinja2
- **CSS Framework**: Tailwind CSS
- **Icons**: Lucide Icons
- **JavaScript**: Vanilla JS with Fetch API

### Testing & Quality
- **Testing**: pytest, pytest-flask, pytest-cov
- **Linting**: pylint
- **Security**: Bandit, pip-audit
- **CI/CD**: GitHub Actions

### External Services
- **Social Media**: LinkedIn API v2, Twitter API v2
- **Email**: SMTP (Gmail)
- **OAuth**: Google OAuth 2.0

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **MySQL**: 8.0 or higher (optional for development)
- **pip**: Latest version
- **Virtual Environment**: venv or virtualenv

### System Requirements

- **OS**: macOS, Linux, or Windows
- **RAM**: 4GB minimum
- **Storage**: 500MB free space

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/social-media-management-system.git
cd social-media-management-system
```

### 2. Create Virtual Environment

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Database Setup

#### Option A: MySQL (Production)

```bash
# Create database
mysql -u root -p
CREATE DATABASE smms_db;
EXIT;

# Import schema
mysql -u root -p smms_db < database/schema.sql
mysql -u root -p smms_db < database/DATABASE_UPDATE.sql
```

#### Option B: SQLite (Development)

```bash
# Set environment variable
export TESTING=true

# Database will be created automatically
```

---

## ⚙️ Configuration

### 1. Change the password in the `.env` File

Create a `.env` file in the project root:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database Configuration (MySQL)
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_HOST=127.0.0.1
MYSQL_DB=smms_db

# OR use SQLite for testing
TESTING=true

# Email Configuration (for password reset)
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-app-password
EMAIL_FROM=noreply@yourdomain.com

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
LINKEDIN_REDIRECT_URI=http://localhost:5000/callback/linkedin

# Twitter OAuth
TWITTER_CLIENT_ID=your-twitter-client-id
TWITTER_CLIENT_SECRET=your-twitter-client-secret
TWITTER_REDIRECT_URI=http://localhost:5000/callback/twitter

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 2. Obtain OAuth Credentials

#### LinkedIn
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Create an app and get Client ID/Secret
3. Add redirect URI: `http://localhost:5000/callback/linkedin`
4. Required scopes: `openid`, `profile`, `email`, `w_member_social`

#### Twitter/X
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create an app with OAuth 2.0 enabled
3. Add redirect URI: `http://localhost:5000/callback/twitter`
4. Required scopes: `tweet.read`, `tweet.write`, `users.read`, `offline.access`

#### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add redirect URI: `http://localhost:5000/google/callback`

---

## 🎯 Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run Flask app
export FLASK_APP=src.app.py
export FLASK_ENV=development
flask run

# Access at: http://localhost:5000
```

## 🧪 Testing

### Run All Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run pytest
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Authentication tests
pytest tests/test_system_workflow.py::TestAuthenticationWorkflow -v

# OAuth tests
pytest tests/test_system_workflow.py::TestOAuthWorkflow -v

# Post management tests
pytest tests/test_system_workflow.py::TestPostWorkflow -v

# Scheduling tests
pytest tests/test_system_workflow.py::TestSchedulingWorkflow -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html tests/

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Test Coverage Requirements

- **Minimum Coverage**: 75%
- **Target Coverage**: 85%+
- **Critical Paths**: 90%+ (authentication, posting, scheduling)

---

## 🔄 CI/CD Pipeline

Our CI/CD pipeline ensures code quality and reliability through automated testing and validation.

### Pipeline Stages

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  BUILD   │→→→│   TEST   │→→→│ COVERAGE │→→→│   LINT   │→→→│ SECURITY │→→→│  DEPLOY  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### 1️⃣ Build Stage
- **Purpose**: Verify Python syntax and compile code
- **Tools**: Python compileall
- **Success Criteria**: No syntax errors

### 2️⃣ Test Stage
- **Purpose**: Run all unit and integration tests
- **Tools**: pytest, MySQL 8.0
- **Success Criteria**: All tests pass
- **Environment**: MySQL service container

### 3️⃣ Coverage Stage
- **Purpose**: Ensure adequate test coverage
- **Tools**: pytest-cov, coverage.py
- **Threshold**: ≥75% code coverage
- **Artifacts**: HTML coverage report

### 4️⃣ Lint Stage
- **Purpose**: Enforce code quality standards
- **Tools**: pylint
- **Threshold**: ≥7.5/10 score
- **Artifacts**: Pylint report

### 5️⃣ Security Stage
- **Purpose**: Identify security vulnerabilities
- **Tools**: 
  - Bandit (code security scanner)
  - pip-audit (dependency vulnerabilities)
- **Artifacts**: Security reports

### 6️⃣ Deploy Stage
- **Purpose**: Package deployment artifacts
- **Output**: Deployment package with code and reports
- **Artifacts**: Timestamped deployment ZIP

### Running CI/CD Locally

```bash
# Install CI tools
pip install pytest coverage pylint bandit pip-audit

# Run build check
python -m compileall src

# Run tests
pytest --maxfail=1 --disable-warnings -q

# Run coverage
coverage run -m pytest
coverage report -m --fail-under=75

# Run linting
pylint src/ --exit-zero

# Run security scan
bandit -r . -f html -o bandit-report.html
pip-audit -r requirements.txt
```

### Pipeline Triggers

- **Push**: Triggers on `dev` and `feature/*` branches
- **Pull Request**: Triggers on PRs to `dev` branch
- **Manual**: Can be triggered manually from GitHub Actions

### Success Metrics

- **Total Runs**: 10+ pipeline executions
- **Success Rate**: >80% from last 15 runs
- **Average Duration**: <10 minutes
- **Coverage Trend**: Increasing over time

---

## 📚 API Documentation

### Authentication Endpoints

#### `POST /signup`
Register a new user account.

**Request Body:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "securepass123",
  "role": "user"
}
```

**Response:** 302 Redirect to login

---

#### `POST /login`
Authenticate user and create session.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepass123"
}
```

**Response:** 302 Redirect to dashboard

---

### OAuth Endpoints

#### `GET /connect/linkedin`
Initiate LinkedIn OAuth flow.

**Response:** 302 Redirect to LinkedIn

---

#### `GET /connect/twitter`
Initiate Twitter OAuth flow with PKCE.

**Response:** 302 Redirect to Twitter

---

### Post Management Endpoints

#### `GET /api/posts`
Retrieve all posts for current user.

**Query Parameters:**
- `status`: Filter by status (draft, pending, scheduled, published)
- `limit`: Maximum number of posts (default: 50)

**Response:**
```json
[
  {
    "id": 1,
    "text": "Post content",
    "status": "published",
    "created_at": "2024-01-15 10:30:00",
    "platforms": [
      {
        "platform_name": "LinkedIn",
        "published": true,
        "published_at": "2024-01-15 10:30:15"
      }
    ]
  }
]
```

---

#### `POST /api/posts`
Create a new post.

**Request Body (form-data):**
```
text: "Post content"
account_ids[]: [1, 2]
status: "draft" | "published" | "scheduled"
scheduled_time: "2024-01-20T14:30" (optional)
media: <file> (optional)
```

**Response:**
```json
{
  "message": "Post created successfully",
  "post_id": 1
}
```

---

#### `PUT /api/posts/:id`
Update an existing post.

**Request Body:**
```json
{
  "text": "Updated content",
  "status": "published",
  "scheduled_time": "2024-01-20T14:30"
}
```

---

#### `DELETE /api/posts/:id`
Delete a post (also removes from social platforms).

**Response:**
```json
{
  "message": "Post deleted successfully",
  "platform_deletions": [
    {
      "platform": "LinkedIn",
      "success": true,
      "message": "Deleted successfully"
    }
  ]
}
```

---

### Team Collaboration Endpoints

#### `POST /update_post_status`
Approve or reject a pending post (Manager only).

**Request Body:**
```json
{
  "post_id": 1,
  "action": "approved" | "rejected"
}
```

---

#### `POST /invite_member`
Invite a new team member (Manager only).

**Request Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "role": "user"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully invited Jane Smith!",
  "temp_password": "generatedPassword123",
  "member": {
    "user_id": 5,
    "name": "Jane Smith",
    "email": "jane@example.com",
    "role": "user"
  }
}
```

---

## 📁 Project Structure

```
social-media-management-system/
├── .github/
│   └── workflows/
│       └── ci-pipeline.yml        # CI/CD configuration
├── database/
│   └── schema.sql                 # Database schema
├── src/
│   ├── __init__.py
│   ├── app.py                     # Main Flask application
│   ├── auth.py                    # Authentication module
│   └── templates/                 # HTML templates
│       ├── login.html
│       ├── signup.html
│       ├── linked_accounts.html
│       ├── create_schedule_posts.html
│       ├── manager_dashboard.html
│       └── team_collaboration.html
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Test configuration
│   ├── test_system_workflow.py    # System tests
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── uploads/                       # Media uploads
├── .env                          # Environment variables (not in git)
├── .gitignore
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── README.md                     # This file
└── LICENSE
```

---

## 👥 User Roles & Permissions

### User Role
- ✅ Create and edit posts
- ✅ Connect social media accounts
- ✅ Schedule posts (requires manager approval)
- ✅ View own posts and activity
- ❌ Approve/reject posts
- ❌ Invite team members

### Manager Role
- ✅ All user permissions
- ✅ Publish posts immediately (no approval needed)
- ✅ Approve/reject user posts
- ✅ Invite and manage team members
- ✅ View team activity dashboard
- ✅ Access collaboration tools

---

## 🔒 Security Features

- **Password Hashing**: Werkzeug PBKDF2 SHA-256
- **Session Security**: HTTP-only cookies, CSRF protection
- **OAuth Security**: State parameter validation, PKCE for Twitter

---

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check MySQL is running
mysql -u root -p

# Verify credentials in .env file
cat .env | grep MYSQL
```

#### OAuth Redirect URI Mismatch
- Ensure redirect URIs in `.env` match OAuth app configuration
- Check for trailing slashes

#### Module Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Port Already in Use
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9
```

---

## 📈 Performance Optimization

- **Database Indexing**: Indexes on user_id, platform_id, status
- **Query Optimization**: Eager loading for relationships
- **Background Jobs**: APScheduler for scheduled posts
- **Connection Pooling**: SQLAlchemy connection pool

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Run tests**: `pytest tests/ -v`
5. **Check coverage**: `pytest --cov=src tests/`
6. **Run linting**: `pylint src/`
7. **Commit changes**: `git commit -m 'Add amazing feature'`
8. **Push to branch**: `git push origin feature/amazing-feature`
9. **Open Pull Request**

### Code Standards

- **Style Guide**: PEP 8
- **Docstrings**: Google style
- **Test Coverage**: >75% for new code
- **Linting**: pylint score >7.5

### Commit Message Format

```
type(scope): subject

body

footer
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Example:**
```
feat(auth): add Google OAuth integration

- Implement OAuth flow
- Add user creation on first login
- Update documentation

Closes #123
```

---
## 🎯 Usage

### For Users:
1. **Sign up** or **Login** to your account
2. **Link social media accounts** (Twitter, LinkedIn) via OAuth
3. **Create posts** with text and/or media in the Post Scheduler
4. **Schedule posts** for future publishing (must be approved by manager)
5. **Track post status**: Draft → Pending → Scheduled → Published
6. View your **linked accounts** and refresh account stats

### For Managers:
1. Access the **Manager Dashboard** with overview stats
2. View all **team members** and their accounts
3. Review **pending/scheduled posts** in Team Collaboration page
4. **Approve or reject** posts before they go live
5. **Invite new team members** with auto-generated temporary passwords
6. Monitor **recent activity** and notifications

## 🛠️ Development Guidelines

### Branching Strategy
- `main`: Production-ready code
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches

### Code Style
- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Add docstrings for functions and classes
- Code coverage target: 70%+
- All tests must pass before merging

## 🚀 Key Technical Features

### Background Scheduler
- APScheduler runs every 30 seconds
- Automatically publishes approved scheduled posts when time arrives
- Handles timezone conversion
- Auto-rejects pending posts with expired scheduled times

### OAuth Implementation
- LinkedIn: Uses OpenID Connect with userinfo endpoint
- Twitter: OAuth 2.0 with PKCE for enhanced security
- State verification via database for security
- Automatic token refresh and account syncing

### Post Status Flow
1. **Draft**: Saved but not submitted
2. **Pending**: Awaiting manager approval
3. **Scheduled**: Approved, waiting for scheduled time
4. **Published**: Successfully posted to platforms
5. **Rejected**: Declined by manager
6. **Failed**: Publishing error occurred

## 🐛 Known Issues & Limitations

- Twitter media upload requires API Pro tier (currently text-only posting)
- File uploads limited to 50MB
- Background scheduler checks every 30 seconds (not real-time)
- OAuth state cleanup runs periodically (10-minute timeout)





**Built with ❤️ by the SMMS Team**

**Last Updated**: November 2025


