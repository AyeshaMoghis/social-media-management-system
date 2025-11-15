import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Base MySQL URI (fixed to use PyMySQL)
default_mysql_uri = "mysql+pymysql://root:root@localhost/smms_db"

# Use DATABASE_URL if provided, else fallback to MySQL+pymysql
database_uri = os.getenv("DATABASE_URL", default_mysql_uri)

# Use SQLite for testing
if os.getenv("TESTING") == "true":
    database_uri = "sqlite:///:memory:"

app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
