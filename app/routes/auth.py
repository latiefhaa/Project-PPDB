from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

# Hapus duplikat Blueprint, gunakan hanya satu
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login berhasil!', 'success')

            if user.is_admin:
                return redirect(url_for('admin_bp.dashboard_admin'))
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash('Login gagal. Periksa username dan password Anda.', 'danger')

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

            # Debug prints
            print(f"Received registration data - username: {username}, email: {email}")

            # Validasi
            if not username or not email or not password:
                flash('Semua field harus diisi', 'danger')
                return redirect(url_for('auth_bp.register'))

            # Cek username dan email yang sudah ada
            if User.query.filter_by(username=username).first():
                flash('Username sudah digunakan', 'danger')
                return redirect(url_for('auth_bp.register'))
            
            if User.query.filter_by(email=email).first():
                flash('Email sudah digunakan', 'danger')
                return redirect(url_for('auth_bp.register'))

            # Buat user baru dengan nilai default
            new_user = User(
                username=username,
                email=email,
                is_admin=False,
                notifications=[],
                has_submitted_form=False
            )
            new_user.set_password(password)
            
            print("Created new user object, attempting database commit")
            
            # Simpan ke database dalam blok try terpisah
            try:
                db.session.add(new_user)
                db.session.commit()
                print("Successfully added user to database")
                flash('Registrasi berhasil! Silakan login.', 'success')
                return redirect(url_for('auth_bp.login'))
            except Exception as db_error:
                print(f"Database error: {str(db_error)}")
                db.session.rollback()
                flash('Gagal menyimpan data ke database', 'danger')
                return redirect(url_for('auth_bp.register'))

        except Exception as e:
            print(f"General registration error: {str(e)}")
            flash('Terjadi kesalahan saat registrasi', 'danger')
            return redirect(url_for('auth_bp.register'))

    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth_bp.login'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}