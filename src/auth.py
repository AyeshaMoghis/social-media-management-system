"""Authentication module for user signup, login, and logout."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

auth = Blueprint('auth', __name__, template_folder='templates')

# These will be set by the main app
User = None
dbs = None


def init_auth(user_model, database):
    """Initialize auth with User model and database from main app"""
    global User, dbs
    User = user_model
    dbs = database


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user signup with form validation and database insertion."""
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_pw = generate_password_hash(password)

        if not User or not dbs:
            flash("Database error. Please try again.", "danger")
            return render_template('signup.html')

        try:
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered. Please login.", "danger")
                return render_template('signup.html')

            # Create new user using SQLAlchemy
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
    """Handle user login with email and password authentication."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not User or not dbs:
            flash("Database error. Please try again.", "danger")
            return render_template('login.html')

        try:
            # Query user using SQLAlchemy
            user = User.query.filter_by(email=email).first()

            if user:
                # Get password_hash from database using raw query (in case model doesn't have it)
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
    """Handle user logout by clearing session."""
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for('auth.login'))
