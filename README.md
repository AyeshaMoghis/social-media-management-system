# Social Media Management System (SMMS)

**Project ID:** P10  
**Course:** UE23CS341A  
**Academic Year:** 2025  
**Semester:** 5th Sem  
**Campus:** EC  
**Branch:** AIML  
**Section:** B  
**Team:** WECODE

## 📋 Project Description

A comprehensive social media management platform that integrates multiple social media accounts (Twitter, LinkedIn) with features for:
- 🔗 Multi-platform account linking via OAuth 2.0
- 📅 Post scheduling and publishing
- 👥 Team collaboration and approval workflows
- 📊 Manager dashboard for oversight
- ✅ Post approval/rejection system
- 🔄 Background scheduler for automated publishing

## ✨ Features

- **Social Media Integration**: Connect Twitter and LinkedIn via OAuth 2.0
- **Post Scheduler**: Create, schedule, and publish posts across multiple platforms
- **Team Collaboration**: Invite team members, manage roles (User/Manager)
- **Approval Workflow**: Managers approve/reject scheduled posts before publishing
- **Account Management**: View and manage all linked social media accounts
- **Real-time Notifications**: Track pending posts and team activities
- **Background Scheduler**: Automated publishing every 30 seconds for scheduled posts
- **Media Upload**: Support for images and videos (up to 50MB)

## 🧑‍💻 Development Team (WECODE)

- [@sansgitbug](https://github.com/sansgitbug) - Scrum Master
- [@lavlovesgit](https://github.com/lavlovesgit) - Developer Team
- [@saffiyaaaa](https://github.com/saffiyaaaa) - Developer Team
- [@tvishasharma8-code](https://github.com/tvishasharma8-code) - Developer Team

## 👨‍🏫 Teaching Assistants

- [@ApekshaMathapati](https://github.com/ApekshaMathapati)
- [@swathanthrashree](https://github.com/swathanthrashree)
- [@Neha20704](https://github.com/Neha20704)
- [@atulpatra28](https://github.com/atulpatra28)
- [@arpitguptaitis](https://github.com/arpitguptaitis)

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- MySQL 8.0 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/pestechnology/PESU_EC_AIML_B_P10_WECODE.git
   cd PESU_EC_AIML_B_P10_WECODE
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # Database Configuration
   MYSQL_HOST=127.0.0.1
   MYSQL_USER=root
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DB=smms
   
   # Flask Configuration
   SECRET_KEY=your-secret-key-here
   FLASK_ENV=development
   
   # LinkedIn OAuth Credentials
   LINKEDIN_CLIENT_ID=your_linkedin_client_id
   LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
   LINKEDIN_REDIRECT_URI=http://127.0.0.1:5000/callback/linkedin
   
   # Twitter OAuth Credentials
   TWITTER_CLIENT_ID=your_twitter_client_id
   TWITTER_CLIENT_SECRET=your_twitter_client_secret
   TWITTER_REDIRECT_URI=http://127.0.0.1:5000/callback/twitter
   ```

5. **Initialize the database**
   ```bash
   mysql -u root -p < database/schema.sql
   ```

6. **Run the application**
   ```bash
   python src/app.py
   ```

7. **Access the application**
   
   Open your browser and navigate to: `http://127.0.0.1:5000`

## 📁 Project Structure

```
PESU_EC_AIML_B_P10_WECODE/
├── src/
│   ├── app.py                    # Main Flask application
│   ├── auth.py                   # Authentication blueprint
│   ├── static/
│   │   ├── css/                 # Stylesheets
│   │   │   ├── styles.css       # Global styles
│   │   │   └── team_collaboration.css
│   │   └── js/                  # JavaScript files
│   │       └── script.js        # Client-side utilities
│   └── templates/
│       ├── login.html           # Login page
│       ├── signup.html          # Signup page
│       ├── manager_dashboard.html
│       ├── team_collaboration.html
│       ├── linked_accounts.html
│       ├── account_details.html
│       └── create_schedule_posts.html
├── tests/
│   ├── unit/                    # Unit tests
│   │   ├── test_unit_login_signup.py
│   │   ├── test_unit_connect_social.py
│   │   └── test_unit_post_scheduler.py
│   ├── integration/             # Integration tests
│   │   ├── test_integration_login_signup.py
│   │   └── test_integration_connect_social.py
│   └── conftest.py             # Test configuration
├── database/                    # Database schemas and migrations
│   ├── schema.sql              # Main database schema
│   ├── DATABASE_UPDATE.sql     # Schema updates
│   ├── add_post_platform_table.sql
│   ├── notif_db.sql            # Notification schema
│   └── update_db_schema.py     # Migration script
├── docs/                        # Documentation
│   ├── APPROVAL_WORKFLOW.md
│   ├── BACKEND_INTEGRATION.md
│   └── LINKEDIN_PUBLISHING.md
├── scripts/                     # Utility scripts
│   ├── run_tests.py
│   └── test_system.py
├── coverage_reports/            # Test coverage (git-ignored)
├── uploads/                     # Uploaded media files
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── pytest.ini                   # Pytest configuration
├── .env                        # Environment variables (not in repo)
├── .gitignore
└── README.md
```

## 🛠️ Technology Stack

- **Backend**: Flask (Python 3.8+)
- **Database**: MySQL 8.0 with SQLAlchemy ORM
- **Authentication**: OAuth 2.0 with PKCE (Twitter, LinkedIn)
- **Background Tasks**: APScheduler for post scheduling
- **Testing**: pytest, pytest-cov
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **File Upload**: Flask file handling (images, videos up to 50MB)

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_unit_post_scheduler.py

# Run with verbose output
pytest -v
```

**Current Test Coverage: 76%**
- `src/__init__.py`: 100%
- `src/app.py`: 77%
- `src/auth.py`: 62%

Coverage reports are generated in `coverage_reports/htmlcov/`

## 📊 Database Schema

The application uses MySQL with the following main tables:
- `user` - User accounts (managers and regular users)
- `platform` - Social media platforms (Twitter, LinkedIn)
- `linked_account` - User-platform OAuth connections
- `post` - Post content and metadata
- `post_platform` - Many-to-many relationship between posts and platforms
- `scheduled_post` - Scheduled post information with timestamps
- `oauth_state` - OAuth flow state management with PKCE

See `database/schema.sql` for the complete schema.

## 🔐 Authentication & Security

- Password hashing using Werkzeug security
- OAuth 2.0 for social media authentication (Twitter, LinkedIn)
- PKCE (Proof Key for Code Exchange) for enhanced OAuth security
- Session-based authentication with secure cookies
- Role-based access control (Manager/User)
- Database-based OAuth state management
- Automatic cleanup of expired OAuth states (10-minute timeout)

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

## 🔄 Future Enhancements

- [ ] Twitter media upload (requires API Pro)
- [ ] Facebook/Instagram integration
- [ ] Analytics dashboard with post performance metrics
- [ ] Post templates for quick content creation
- [ ] Bulk post scheduling from CSV
- [ ] Mobile responsive design improvements
- [ ] Email notifications for approvals
- [ ] Rich text editor for post content
- [ ] Post preview before publishing
- [ ] Hashtag suggestions

## 📄 License

This project is developed for educational purposes as part of the PES University UE23CS341A curriculum.

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Contact the development team

---

**Course:** UE23CS341A  
**Institution:** PES University  
**Academic Year:** 2025  
**Semester:** 5th Sem  
**Test Coverage:** 76%

**Made with ❤️ by Team WECODE**
