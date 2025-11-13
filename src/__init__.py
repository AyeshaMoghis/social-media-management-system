import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Dynamically use SQLite if in TESTING mode
database_uri = os.getenv("DATABASE_URL", "mysql://root:root@localhost/smms_db")
if os.getenv("TESTING") == "true":
    database_uri = "sqlite:///:memory:"

app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
