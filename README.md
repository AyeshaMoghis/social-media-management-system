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

A comprehensive social media management platform that integrates multiple social media accounts (Twitter, LinkedIn, Facebook, etc.) with features for:
- 🔗 Multi-platform account linking via OAuth
- 📅 Post scheduling and publishing
- 👥 Team collaboration and approval workflows
- 📊 Manager dashboard for oversight
- ✅ Post approval/rejection system

## ✨ Features

- **Social Media Integration**: Connect Twitter, LinkedIn, and other platforms via OAuth
- **Post Scheduler**: Create, schedule, and publish posts across multiple platforms
- **Team Collaboration**: Invite team members, manage roles (User/Manager)
- **Approval Workflow**: Managers can approve or reject scheduled posts
- **Account Management**: View and manage all linked social media accounts
- **Real-time Notifications**: Track pending posts and team activities

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
   DB_HOST=127.0.0.1
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_NAME=smms
   
   # Flask Configuration
   FLASK_SECRET_KEY=your-secret-key-here
   FLASK_ENV=development
   
   # OAuth Credentials (Twitter)
   TWITTER_CLIENT_ID=your_twitter_client_id
   TWITTER_CLIENT_SECRET=your_twitter_client_secret
   
   # OAuth Credentials (LinkedIn)
   LINKEDIN_CLIENT_ID=your_linkedin_client_id
   LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
   ```

5. **Initialize the database**
   ```bash
   mysql -u root -p < schema.sql
   ```

6. **Run the application**
   ```bash
   cd src
   python app.py
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
│   │   ├── styles.css           # Global styles
│   │   ├── script.js            # JavaScript utilities
│   │   └── team_collaboration.css
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
│   │   ├── test_unit_post_scheduler.py
│   │   └── test_unit_team_collaboration.py
│   ├── integration/             # Integration tests
│   │   ├── test_integration_login_signup.py
│   │   └── test_integration_connect_social.py
│   └── conftest.py             # Test configuration
├── uploads/                     # Uploaded media files
├── schema.sql                   # Database schema
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── pytest.ini                   # Pytest configuration
├── .env                        # Environment variables (not in repo)
├── .gitignore
└── README.md
```

## 🛠️ Technology Stack

- **Backend**: Flask (Python 3.8+)
- **Database**: MySQL 8.0
- **ORM**: SQLAlchemy
- **Authentication**: OAuth 2.0 (Twitter, LinkedIn)
- **Testing**: pytest, pytest-cov
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_unit_post_scheduler.py

# Run with verbose output
pytest tests/ -v
```

**Current Test Coverage: 75%**

## 📊 Database Schema

The application uses MySQL with the following main tables:
- `user` - User accounts (managers and regular users)
- `platform` - Social media platforms
- `linked_account` - User-platform connections
- `post` - Post content and metadata
- `post_platform` - Post-platform associations
- `scheduled_post` - Scheduled post information
- `oauth_state` - OAuth flow state management

See `schema.sql` for the complete schema.

## 🔐 Authentication & Security

- Password hashing using Werkzeug security
- OAuth 2.0 for social media authentication
- Session-based authentication
- Role-based access control (Manager/User)
- PKCE (Proof Key for Code Exchange) for OAuth flows

## 🎯 Usage

### For Users:
1. **Sign up** or **Login** to your account
2. **Link social media accounts** (Twitter, LinkedIn)
3. **Create posts** in the Post Scheduler
4. **Schedule posts** for future publishing
5. View your **linked accounts** and their status

### For Managers:
1. Access the **Manager Dashboard**
2. View all **team members**
3. Review **pending/scheduled posts** in Team Collaboration
4. **Approve or reject** posts
5. **Invite new team members**

## 🛠️ Development Guidelines

### Branching Strategy
- `main`: Production-ready code
- `dev`: Development branch (current)
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches

### Commit Messages
Follow conventional commit format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test-related changes
- `chore:` Maintenance tasks

### Code Style
- Follow PEP 8 guidelines
- Code coverage target: 70%+
- All tests must pass before merging

## 🐛 Known Issues

- OAuth state cleanup runs periodically
- File upload size limited to 50MB
- Some unit tests need updating for new database schema

## 🔄 Future Enhancements

- [ ] Facebook OAuth integration
- [ ] Analytics dashboard
- [ ] Post templates
- [ ] Bulk post scheduling
- [ ] Mobile responsive design improvements
- [ ] Email notifications
- [ ] Post performance metrics

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
**Test Coverage:** 70%

**Made with ❤️ by Team WECODE**
