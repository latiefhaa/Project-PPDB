from flask import Blueprint, render_template
from flask_login import login_required, current_user

# Inisialisasi Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html', user=current_user)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Render halaman dashboard dengan data pengguna
    return render_template('dashboard.html', user=current_user)

