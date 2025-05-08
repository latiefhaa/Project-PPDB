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
        if user and user.check_password(password):  # Gunakan metode check_password
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
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

auth_bp.route('/register_admin', methods=['GET', 'POST'])
@login_required
def register_admin():
    if not current_user.is_admin:  # Pastikan hanya admin yang bisa mengakses
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Validasi apakah username atau email sudah digunakan
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
            return redirect(url_for('auth_bp.register_admin'))
        elif User.query.filter_by(email=email).first():
            flash('Email sudah digunakan.', 'danger')
            return redirect(url_for('auth_bp.register_admin'))

        # Buat admin baru
        new_admin = User(username=username, email=email, is_admin=True)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()

        flash('Admin berhasil didaftarkan!', 'success')
        return redirect(url_for('auth_bp.login'))

    return render_template('register_admin.html')