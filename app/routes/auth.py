from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth_bp.login'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}
auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):  # Validasi password
            login_user(user)
            flash('Login berhasil!', 'success')

            # Periksa apakah pengguna adalah admin
            if user.is_admin:
                return redirect(url_for('admin_bp.dashboard_admin'))  # Arahkan ke dashboard admin
            else:
                return redirect(url_for('main.dashboard'))  # Arahkan ke dashboard user biasa
        else:
            flash('Login gagal. Periksa username dan password Anda.', 'danger')

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Validasi apakah username atau email sudah digunakan
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth_bp.register'))
        elif User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('auth_bp.register'))

        # Buat user baru
        new_user = User(username=username, email=email, is_admin=False)  # User biasa
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth_bp.login'))

    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth_bp.login'))