from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, User, StudentForm

# Inisialisasi Blueprint untuk admin
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

# Middleware untuk memastikan hanya admin yang dapat mengakses
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Anda tidak memiliki akses ke halaman ini.", "danger")
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@admin_bp.route('/admin/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:  # Pastikan hanya admin yang bisa mengakses
        return redirect(url_for('main.index'))
    return render_template('admin_dashboard.html')