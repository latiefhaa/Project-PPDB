from flask import Blueprint, render_template, redirect, url_for, request, flash, Flask, jsonify
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
@login_required
def dashboard():
    user_form = StudentForm.query.filter_by(user_id=current_user.id).first()
    return render_template('dashboard.html', user=current_user, form=user_form)

@main_bp.route('/form', methods=['GET'])
@login_required
def form():
    # Render halaman formulir pendaftaran
    return render_template('form.html', user=current_user)

# Route untuk menangani pengiriman formulir pendaftaran
@main_bp.route('/submit_form', methods=['POST'])
@login_required
def submit_form():
    if current_user.has_submitted_form:
        flash('Anda sudah pernah mengirimkan formulir sebelumnya.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Ambil data dari form
    full_name = request.form.get('full_name')
    gender = request.form.get('gender')
    birth_place = request.form.get('birth_place')
    birth_date = request.form.get('birth_date')
    religion = request.form.get('religion')
    nisn = request.form.get('nisn')
    father_name = request.form.get('father_name')
    mother_name = request.form.get('mother_name')
    parent_phone = request.form.get('parent_phone')
    parent_occupation = request.form.get('parent_occupation')
    address = request.form.get('address')
    previous_school = request.form.get('previous_school')

    # Validasi field yang wajib diisi
    if not all([full_name, gender, birth_place, birth_date, religion, nisn, father_name, mother_name, parent_phone, parent_occupation, address, previous_school]):
        flash('Semua field harus diisi', 'danger')
        return redirect(url_for('main.form'))

    # Simpan file prestasi
    filename = None
    achievement_file = request.files.get('achievement_file')
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
            gender=gender,
            birth_place=birth_place,
            birth_date=datetime.strptime(birth_date, '%Y-%m-%d').date(),
            religion=religion,
            nisn=nisn,
            father_name=father_name,
            mother_name=mother_name,
            parent_phone=parent_phone,
            parent_occupation=parent_occupation,
            address=address,
            previous_school=previous_school,
            achievement_file=filename,
            status="Menunggu"
        )
        db.session.add(new_student)
        
        # Set flag has_submitted_form
        current_user.has_submitted_form = True
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

@main_bp.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html', notifications=current_user.notifications or [])

@main_bp.route('/mark-notification-as-read', methods=['POST'])
@login_required
def mark_notification_as_read():
    data = request.get_json()
    notification_id = data.get('notification_id')
    
    if current_user.notifications:
        for notification in current_user.notifications:
            if notification.get('id') == notification_id:
                notification['read'] = True
                break
        
        db.session.commit()
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error'}), 400

@main_bp.route('/get-notifications')
@login_required
def get_notifications():
    """Get unread notifications for pop-up display"""
    if current_user.notifications:
        unread = [n for n in current_user.notifications if not n.get('read', False)]
        return jsonify(unread)
    return jsonify([])

@main_bp.route('/payment/<int:form_id>')
@login_required
def payment_page(form_id):
    form = StudentForm.query.get_or_404(form_id)
    
    # Verify the form belongs to current user
    if form.user_id != current_user.id:
        flash('Anda tidak memiliki akses ke halaman ini', 'danger')
        return redirect(url_for('main.dashboard'))
        
    return render_template('payment.html', form=form)



