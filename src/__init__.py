"""Application initialization and database configuration."""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
# Initialize OAuth
oauth = OAuth(app)

# Register Google OAuth client
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v2/',
    client_kwargs={'scope': 'email profile'}
)


# Base MySQL URI (fixed to use PyMySQL)
DEFAULT_MYSQL_URI = "mysql+pymysql://root:root@localhost/smms_db"

# Use DATABASE_URL if provided, else fallback to MySQL+pymysql
database_uri = os.getenv("DATABASE_URL", DEFAULT_MYSQL_URI)

# Use SQLite for testing
if os.getenv("TESTING") == "true":
    database_uri = "sqlite:///:memory:"

app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
