"""
Authentication module for user signup, login, and logout.
Handles password hashing and session management.
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from dotenv import load_dotenv

auth = Blueprint('auth', __name__, template_folder='templates')

load_dotenv()


def get_db_connection():
    """Establish and return MySQL database connection"""
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user signup with password hashing"""
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_pw = generate_password_hash(password)
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO user (email, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
                (email, hashed_pw, full_name, role)
            )
            db.commit()
            flash(f"Account created successfully as {role.capitalize()}! Please log in.",
                  "success")
            return redirect(url_for('auth.login'))
        except Exception:
            # This catches both mysql.connector.Error and mocked exceptions
            flash("Error creating account", "danger")
        finally:
            cursor.close()
            db.close()
    return render_template('signup.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with password verification"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash("Login successful!", "success")

            if user['role'] == 'manager':
                return redirect(url_for('manager_dashboard'))
            return redirect(url_for('user_dashboard'))
        flash("Invalid credentials. Try again.", "danger")

    return render_template('login.html')


@auth.route('/logout')
def logout():
    """Clear session and log out user"""
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for('auth.login'))
