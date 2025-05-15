from flask import Blueprint, render_template, redirect, url_for, request, flash, Flask
from flask_login import login_required, current_user
from app.models import StudentForm
from app import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)

# Set maximum upload size to 16 MB (adjust as needed)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

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
    birth_date = request.form.get('birth_date')
    parent_name = request.form.get('parent_name')
    address = request.form.get('address')
    previous_school = request.form.get('previous_school')
    achievement_file = request.files.get('achievement_file')
    payment_code = request.form.get('payment_code')
    payment_confirmation = request.form.get('payment_confirmation')

    # Validasi data
    if not payment_confirmation:
        flash('Anda harus mencentang kotak konfirmasi pembayaran.', 'danger')
        return redirect(url_for('main.form'))

    if payment_code != "123456":  # Ganti dengan kode pembayaran yang valid
        flash('Kode pembayaran tidak valid.', 'danger')
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
    try:
        new_student = StudentForm(
            user_id=current_user.id,
            full_name=full_name,
            birth_date=datetime.strptime(birth_date, '%Y-%m-%d').date(),
            parent_name=parent_name,
            address=address,
            previous_school=previous_school,
            achievement_file=filename,
            payment_status="Paid"  # Tandai pembayaran sebagai selesai
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Formulir berhasil dikirim!', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        return redirect(url_for('main.form'))

@main_bp.route('/payment_info', methods=['GET', 'POST'])
@login_required
def payment_info():
    if request.method == 'POST':
        # Ambil file bukti pembayaran
        payment_proof = request.files.get('payment_proof')

        # Validasi file
        if payment_proof and payment_proof.filename != '':
            if '.' in payment_proof.filename and \
               payment_proof.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
                filename = secure_filename(payment_proof.filename)
                payment_path = os.path.join(UPLOAD_FOLDER, 'payment_proofs', filename)
                os.makedirs(os.path.dirname(payment_path), exist_ok=True)
                payment_proof.save(payment_path)

                # Simpan bukti pembayaran ke database
                current_user_form = StudentForm.query.filter_by(user_id=current_user.id).first()
                if current_user_form:
                    current_user_form.payment_proof = filename
                    current_user_form.payment_status = "Proof Uploaded"
                    db.session.commit()

                    flash('Bukti pembayaran berhasil diunggah!', 'success')
                    return redirect(url_for('main.dashboard'))
                else:
                    flash('Formulir pendaftaran tidak ditemukan.', 'danger')
                    return redirect(url_for('main.form'))
            else:
                flash('Format file tidak valid. Hanya menerima PNG, JPG, JPEG, atau GIF.', 'danger')
                return redirect(url_for('main.payment_info'))
        else:
            flash('Harap unggah bukti pembayaran.', 'danger')
            return redirect(url_for('main.payment_info'))

    # Jika GET, tampilkan halaman pembayaran
    return render_template('payment_info.html')



