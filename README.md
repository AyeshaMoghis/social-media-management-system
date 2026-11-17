# Social Media Management System

A web platform for managing several social media accounts from one place. Users connect their LinkedIn and X (Twitter) accounts through OAuth 2.0, write a post once with optional images, and either publish it immediately or schedule it for later across any of their connected accounts. Teams get a manager role: posts submitted by team members wait in an approval queue until a manager approves or rejects them, and a background scheduler publishes approved posts on time. A separate notification service records what happened to each post and shows it in the app.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask 3, Flask-SQLAlchemy / SQLAlchemy 2 |
| Database | MySQL 8 (PyMySQL driver) |
| Frontend | Server-rendered Jinja2 templates, vanilla JavaScript, CSS |
| Scheduling | APScheduler background job |
| Integrations | LinkedIn API v2 (OAuth 2.0), X API v2 (OAuth 2.0 with PKCE), REST over `requests` |
| Notifications | Separate Flask microservice with REST endpoints, optional SMTP email |
| Testing | pytest, pytest-mock, in-memory SQLite for tests |
| CI | GitHub Actions: build, test, coverage, pylint, Bandit and pip-audit stages |

## Features

- **Account linking.** Connect LinkedIn and X accounts with OAuth 2.0. X uses PKCE. Accounts can be refreshed and disconnected.
- **Cross-posting.** Write one post and publish it to several connected accounts through each platform's REST API.
- **Scheduling.** Pick a future time and a background job checks every 30 seconds and publishes due posts.
- **Media uploads.** Attach images to posts.
- **Role-based access.** Accounts are either `user` or `manager`, each with its own dashboard. Manager-only pages and actions are checked on the server.
- **Approval workflow.** Posts from team members go to a pending queue. Managers approve or reject them, and pending posts whose scheduled time passes are rejected automatically.
- **Team collaboration.** Managers invite members and search the team.
- **Notifications.** The main app sends events such as created, approved, published or failed to the notification service, which stores them and can email the user.
- **Session authentication.** Signup and login with hashed passwords (Werkzeug).

## Screenshots

_Screenshots coming soon. Add images to `docs/screenshots/` and embed them here._

## Architecture

```
 Browser (Jinja2 pages + JS)
    |                 \
    | HTTP             \ fetch() for notification list
    v                   v
 Flask app (src/app.py, :5000)  ---- POST events ---->  Notification service (notifapp.py, :5001)
    |  routes, OAuth flows,                                 |  stores notifications,
    |  SQLAlchemy models,                                   |  optional SMTP email
    |  APScheduler publish job                              |
    v                                                       v
 MySQL database "smms"  <-----------------------------------+
    ^
    |  publish / refresh via REST
 LinkedIn API v2, X API v2
```

- **Flask app.** `src/app.py` holds the routes, SQLAlchemy models, OAuth flows for LinkedIn and X, and the publishing functions. Pages are rendered server-side from `src/templates/`. The JSON endpoints under `/api/posts` back the post scheduler page.
- **Auth blueprint.** Signup, login and logout live in `src/auth_old.py` and are registered as the `auth` blueprint.
- **Scheduler.** An APScheduler job runs inside the Flask process. Every 30 seconds it publishes scheduled posts that are due and rejects expired pending posts.
- **Notification service.** `notifapp.py` is a small standalone Flask app. The main app posts events to it through `src/notification_helper.py`, and the browser reads notifications from it directly.
- **Database.** Both services share one MySQL database. SQL scripts live in `database/`.

## Local setup

### Prerequisites

- Python 3.10 or newer
- MySQL 8
- Developer apps on LinkedIn and X if you want to connect real accounts. Set each app's callback URL to the redirect URI in your `.env`.

### Install

```bash
git clone https://github.com/AyeshaMoghis/social-media-management-system.git
cd social-media-management-system

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install flask-cors mysql-connector-python   # used by the notification service
```

### Environment variables

```bash
cp .env.example .env
```

Fill in `.env`. Every variable the code reads is listed in `.env.example` with a comment. The main app loads `.env` automatically. The notification service does not, so export the `MYSQL_*` variables in its terminal.

### Database

```bash
mysql -u root -p < database/schema.sql            # creates the smms database, core tables, platform rows
mysql -u root -p < database/DATABASE_UPDATE.sql   # adds approval statuses and account columns
mysql -u root -p < database/notif_db.sql          # notification tables
```

The main app creates any remaining tables, such as `post_platform`, the first time it starts.

### Run

Start the notification service in one terminal:

```bash
export MYSQL_USER=root MYSQL_PASSWORD=your-password MYSQL_DB=smms
python notifapp.py                # http://127.0.0.1:5001
```

Start the main app from the repository root in a second terminal. Both the root and `src/` must be on the Python path:

```bash
PYTHONPATH=.:src python src/app.py        # macOS / Linux
```

```powershell
$env:PYTHONPATH = ".;src"; python src/app.py   # Windows PowerShell
```

Open http://127.0.0.1:5000 and sign up. Choose the manager role to see the approval dashboard.

### Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run against an in-memory SQLite database, so MySQL is not needed.

## Known issues

- **Google sign-in and email password reset are not fully wired up.** Both were built on feature branches. In this integrated version the Google OAuth client is registered on a separate Flask app in `src/__init__.py`, and Flask-Mail is never initialised in `src/app.py`. Their tests in `tests/unit/test_unit_auth.py` fail for this reason.
- **The notification service URL is hardcoded** as `http://127.0.0.1:5001` in `src/notification_helper.py` and `src/static/js/notification_script.js`.

## Project structure

```
src/
  app.py                  Flask app: routes, models, OAuth, publishing, scheduler
  auth_old.py             auth blueprint: signup, login, logout
  notification_helper.py  sends events to the notification service
  templates/              Jinja2 pages
  static/                 CSS and JavaScript
notifapp.py               notification microservice
database/                 MySQL schema and migration scripts
tests/                    unit and integration tests
docs/                     design notes: approval workflow, LinkedIn publishing
.github/workflows/ci.yml  CI pipeline
```

## Contributors

This was built as a five-person team project. Contributions below are inferred from each person's commits.

- **[@AyeshaMoghis](https://github.com/AyeshaMoghis)** built the notification system overhaul: the standalone notification service, event hooks from the main app, the notifications page and timestamp fixes.
- **[@lavlovesgit](https://github.com/lavlovesgit)** set up the initial Flask app and database schema, built login, signup and LinkedIn and X account linking, and wrote the CI/CD pipeline and much of the test suite.
- **[@saffiyaaaa](https://github.com/saffiyaaaa)** built post creation and scheduling with media uploads, integrated linked accounts with the scheduler, wrote database schemas, and extended the CI pipeline to five stages.
- **[@tvishasharma8-code](https://github.com/tvishasharma8-code)** built the manager approval workflow and automatic publishing of scheduled posts, and stabilised the test suite and CI.
- **[@sansgitbug](https://github.com/sansgitbug)** built Google sign-in and email OTP password reset.

Initial repository setup: [@mandhara123](https://github.com/mandhara123), [@ApekshaMathapati](https://github.com/ApekshaMathapati), [@Swathanthrashree](https://github.com/Swathanthrashree).
