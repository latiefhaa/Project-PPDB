from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import StudentForm
from app import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Inisialisasi Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html', user=current_user)

@main_bp.route('/dashboard')
def dashboard():
    # Render halaman dashboard dengan data pengguna
    return render_template('dashboard.html', user=current_user)

@main_bp.route('/form', methods=['GET'])
@login_required
def form():
    # Render halaman formulir pendaftaran
    return render_template('form.html', user=current_user)

# Route untuk menangani pengiriman formulir pendaftaran
@main_bp.route('/submit_form', methods=['POST'])
@login_required
def submit_form():
    # Ambil data dari form
    full_name = request.form.get('full_name')
    birth_date = request.form.get('birth_date')  # String dari form
    parent_name = request.form.get('parent_name')
    address = request.form.get('address')
    previous_school = request.form.get('previous_school')
    achievement_file = request.files.get('achievement_file')

    # Konversi string tanggal menjadi objek datetime.date
    try:
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Format tanggal tidak valid. Gunakan format YYYY-MM-DD.', 'danger')
        return redirect(url_for('main.form'))

    # Simpan file prestasi
    filename = None
    if achievement_file and achievement_file.filename != '':
        if '.' in achievement_file.filename and \
           achievement_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
            filename = secure_filename(achievement_file.filename)
            achievement_file.save(os.path.join(UPLOAD_FOLDER, filename))
        else:
            flash('Format file tidak valid. Hanya menerima PNG, JPG, JPEG, atau GIF.', 'danger')
            return redirect(url_for('main.form'))

    # Simpan data ke database
    new_student = StudentForm(
        user_id=current_user.id,
        full_name=full_name,
        birth_date=birth_date,
        parent_name=parent_name,
        address=address,
        previous_school=previous_school,
        achievement_file=filename  # Simpan nama file
    )
    db.session.add(new_student)
    db.session.commit()

    flash('Formulir berhasil dikirim!', 'success')
    return redirect(url_for('main.dashboard'))



