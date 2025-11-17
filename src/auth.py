"""Authentication module for user signup, login, logout, Google OAuth and forgot-password (OTP)."""
import os
import random
import time

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from flask_mail import Message
from src import oauth  # your OAuth client configured in src/oauth.py (keep as-is)

auth = Blueprint('auth', __name__, template_folder='templates')

# Will be injected from main app at runtime
User = None
dbs = None

def init_auth(user_model, database):
    """Initialize auth with User model and database from main app"""
    global User, dbs
    User = user_model
    dbs = database


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user signup."""
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')

        hashed_pw = generate_password_hash(password)

        if not User or not dbs:
            flash("Database error. Please try again.", "danger")
            return render_template('signup.html')

        try:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered. Please login.", "danger")
                return render_template('signup.html')

            query = text("""
                INSERT INTO user (email, password_hash, full_name, role)
                VALUES (:email, :password_hash, :full_name, :role)
            """)
            dbs.session.execute(query, {
                'email': email,
                'password_hash': hashed_pw,
                'full_name': full_name,
                'role': role
            })
            dbs.session.commit()
            flash(f"Account created successfully as {role.capitalize()}! Please log in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            dbs.session.rollback()
            flash(f"Error: {e}", "danger")
    return render_template('signup.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not User or not dbs:
            flash("Database error. Please try again.", "danger")
            return render_template('login.html')

        try:
            user = User.query.filter_by(email=email).first()
            if user:
                query = text("SELECT password_hash FROM user WHERE email = :email")
                result = dbs.session.execute(query, {'email': email}).fetchone()
                if result and check_password_hash(result[0], password):
                    session['user_id'] = user.user_id
                    session['full_name'] = user.full_name
                    session['role'] = user.role
                    flash("Login successful!", "success")

                    if user.role == 'manager':
                        return redirect(url_for('manager_dashboard'))
                    return redirect(url_for('user_dashboard'))
                flash("Invalid credentials. Try again.", "danger")
            else:
                flash("Invalid credentials. Try again.", "danger")
        except Exception as e:
            flash(f"Login error: {e}", "danger")
    return render_template('login.html')


@auth.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for('auth.login'))


# -------------------------
# GOOGLE SIGN-IN ROUTES
# Note: this expects `src/oauth.py` to have `oauth` and `oauth.google` configured.
# -------------------------
@auth.route('/login/google')
def login_google():
    """Initiate Google OAuth login."""
    # redirect back to /google/callback
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    # exchange token and fetch userinfo
    oauth.google.authorize_access_token()
    user_info = oauth.google.get('userinfo').json()

    email = user_info.get('email')
    full_name = user_info.get('name', "Google User")

    if not email:
        flash("Failed to get email from Google.", "danger")
        return redirect(url_for('auth.login'))

    existing_user = User.query.filter_by(email=email).first()

    if not existing_user:
        query = text("""
            INSERT INTO user (email, password_hash, full_name, role)
            VALUES (:email, :password_hash, :full_name, :role)
        """)
        dbs.session.execute(query, {
            'email': email,
            'password_hash': generate_password_hash(os.urandom(16).hex()),
            'full_name': full_name,
            'role': 'user'
        })
        dbs.session.commit()
        existing_user = User.query.filter_by(email=email).first()

    # Log in
    session['user_id'] = existing_user.user_id
    session['full_name'] = existing_user.full_name
    session['role'] = existing_user.role
    flash("Logged in with Google!", "success")

    if existing_user.role == "manager":
        return redirect(url_for('manager_dashboard'))
    return redirect(url_for('user_dashboard'))


# -------------------------
# FORGOT PASSWORD (OTP) FLOWS
# -------------------------
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password request and send OTP."""
    # cooldown: 60 seconds between OTPs
    last_time = session.get("otp_last_time")
    if last_time and time.time() - last_time < 60:
        remaining = int(60 - (time.time() - last_time))
        flash(f"Please wait {remaining} seconds before requesting another OTP.", "warning")
        return redirect(url_for('auth.verify_otp'))

    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account with that email exists.", "danger")
            return redirect(url_for('auth.forgot_password'))

        otp = random.randint(100000, 999999)
        session['reset_email'] = email
        session['reset_otp'] = otp
        # send email via Flask-Mail extension (configured in your app)
        msg = Message(
            "Your OTP for Password Reset",
            sender=os.getenv("EMAIL_FROM"),
            recipients=[email]
        )
        msg.body = f"Your OTP is: {otp}"
        # send using flask-mail registered as extension: current_app.extensions['mail']
        current_app.extensions['mail'].send(msg)
        session['otp_last_time'] = time.time()
        flash("OTP has been sent to your email!", "success")
        return redirect(url_for('auth.verify_otp'))

    return render_template('forgot_password.html')


@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Verify OTP for password reset."""
    if request.method == 'POST':
        session['otp_attempts'] = session.get('otp_attempts', 0) + 1
        if session['otp_attempts'] > 5:
            flash("Too many attempts. Request a new OTP.", "danger")
            session.pop('reset_otp', None)
            return redirect(url_for('auth.forgot_password'))

        entered_otp = request.form['otp']
        real_otp = session.get('reset_otp')
        if real_otp and str(entered_otp) == str(real_otp):
            session.pop('otp_attempts', None)
            flash("OTP verified successfully!", "success")
            return redirect(url_for('auth.reset_password'))
        else:
            flash("Invalid OTP. Try again.", "danger")
    return render_template('verify_otp.html')


@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset."""
    if request.method == 'POST':
        new_pw = request.form['password']
        email = session.get('reset_email')

        if not email:
            flash("Session expired. Start again.", "danger")
            return redirect(url_for('auth.forgot_password'))

        hashed = generate_password_hash(new_pw)
        query = text("UPDATE user SET password_hash = :pw WHERE email = :email")
        dbs.session.execute(query, {"pw": hashed, "email": email})
        dbs.session.commit()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        flash("Password reset successful!", "success")
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')
