"""
Flask application initialization module.
Configures the Flask app and SQLAlchemy database connection.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Dynamically use SQLite if in TESTING mode
DB_URI = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost/smms_db")
if os.getenv("TESTING") == "true":
    DB_URI = "sqlite:///:memory:"

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
