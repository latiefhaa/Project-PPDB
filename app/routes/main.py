from flask import Blueprint, render_template, redirect, url_for, request, flash, Flask, jsonify
from flask_login import login_required, current_user
from app.models import StudentForm
from app import db
from datetime import datetime
from werkzeug.utils import secure_filename
import os

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = 'app/static/uploads/payments'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html', user=current_user)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get user's form and notifications
    user_form = StudentForm.query.filter_by(user_id=current_user.id).first()
    notifications = current_user.notifications or []
    
    # Get any unread notifications
    unread_notifications = [n for n in notifications if not n.get('read', False)]
    
    # Get payment info if form exists and waiting for payment
    payment_required = False
    if user_form and user_form.status == "Menunggu Pembayaran":
        payment_required = True
    
    return render_template(
        'dashboard.html',
        user=current_user,
        form=user_form,
        notifications=unread_notifications,
        payment_required=payment_required
    )

@main_bp.route('/form', methods=['GET'])
@login_required
def form():
    # Render halaman formulir pendaftaran
    return render_template('form.html', user=current_user)

# Route untuk menangani pengiriman formulir pendaftaran
@main_bp.route('/submit_form', methods=['POST'])
@login_required
def submit_form():
    print("\n=== DEBUG: Form Submission Start ===")
    
    try:
        # Get form data
        form_data = {
            'full_name': request.form.get('full_name'),
            'gender': request.form.get('gender'),
            'birth_place': request.form.get('birth_place'),
            'birth_date': request.form.get('birth_date'),
            'religion': request.form.get('religion'),
            'nisn': request.form.get('nisn'),
            'father_name': request.form.get('father_name'),
            'mother_name': request.form.get('mother_name'),
            'parent_phone': request.form.get('parent_phone'),
            'parent_occupation': request.form.get('parent_occupation'),
            'address': request.form.get('address'),
            'previous_school': request.form.get('previous_school')
        }

        print("Form data received:", form_data)
        
        # Create new form
        new_student = StudentForm(
            user_id=current_user.id,
            full_name=form_data['full_name'],
            gender=form_data['gender'],
            birth_place=form_data['birth_place'],
            birth_date=datetime.strptime(form_data['birth_date'], '%Y-%m-%d').date(),
            religion=form_data['religion'],
            nisn=form_data['nisn'],
            father_name=form_data['father_name'],
            mother_name=form_data['mother_name'],
            parent_phone=form_data['parent_phone'],
            parent_occupation=form_data['parent_occupation'],
            address=form_data['address'],
            previous_school=form_data['previous_school'],
            status="Menunggu"
        )
        
        print("New student object created")
        
        # Add to database
        db.session.add(new_student)
        print("Added to session")
        
        current_user.has_submitted_form = True
        print("User submitted form flag updated")
        
        # Commit changes
        db.session.commit()
        print("Changes committed to database")
        
        flash('Formulir berhasil dikirim!', 'success')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: {str(e)}")
        print(f"Error type: {type(e)}")
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        return redirect(url_for('main.form'))

@main_bp.route('/payment_info', methods=['GET', 'POST'])
@login_required
def payment_info():
    form = StudentForm.query.filter_by(user_id=current_user.id).first()
    
    if not form or form.status != "Menunggu Pembayaran":
        flash('Anda tidak dalam status menunggu pembayaran.', 'warning')
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        sender_name = request.form.get('sender_name')
        payment_proof = request.files.get('payment_proof')
        
        if payment_proof and allowed_file(payment_proof.filename):
            try:
                filename = secure_filename(f"payment_{form.id}_{payment_proof.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, 'payments', filename)
                
                # Simpan bukti pembayaran
                payment_proof.save(filepath)
                
                # Update status form
                form.payment_proof = filename
                form.payment_status = "Menunggu Verifikasi"
                form.payment_sender = sender_name
                
                db.session.commit()
                
                flash('Bukti pembayaran berhasil diunggah dan menunggu verifikasi admin.', 'success')
                return redirect(url_for('main.dashboard'))
                
            except Exception as e:
                flash('Terjadi kesalahan saat upload bukti pembayaran.', 'danger')
                print(f"Error: {str(e)}")
                
        else:
            flash('File tidak valid. Gunakan format JPG, PNG, atau JPEG.', 'warning')
            
    return render_template('payment_info.html', form=form)

@main_bp.route('/notifications')
@login_required
def notifications():
    notifications = sorted(
        current_user.notifications or [], 
        key=lambda x: x.get('timestamp', ''), 
        reverse=True
    )
    return render_template('notifications.html', notifications=notifications)

@main_bp.route('/mark-notification-as-read', methods=['POST'])
@login_required
def mark_notification_as_read():
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        
        if current_user.notifications:
            for notification in current_user.notifications:
                if notification.get('id') == notification_id:
                    notification['read'] = True
                    break
            
            db.session.commit()
            return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error marking notification as read: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return jsonify({'status': 'error', 'message': 'Notification not found'}), 404

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

@main_bp.route('/upload_payment_proof', methods=['POST'])
@login_required
def upload_payment_proof():
    try:
        if 'payment_proof' not in request.files:
            flash('Tidak ada file yang dipilih', 'error')
            return redirect(url_for('main.payment_info'))

        file = request.files['payment_proof']
        if file.filename == '':
            flash('Tidak ada file yang dipilih', 'error')
            return redirect(url_for('main.payment_info'))

        if file and allowed_file(file.filename):
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join('app', 'static', 'uploads', 'payments')
            os.makedirs(upload_dir, exist_ok=True)

            # Get student form
            form = StudentForm.query.filter_by(user_id=current_user.id).first()
            
            # Generate secure filename
            filename = secure_filename(f"payment_{form.id}_{file.filename}")
            filepath = os.path.join(upload_dir, filename)
            
            # Save file
            file.save(filepath)
            
            # Update form payment status
            form.payment_proof = f"uploads/payments/{filename}"
            form.payment_status = "Menunggu Verifikasi"
            
            db.session.commit()
            
            flash('Bukti pembayaran berhasil diupload. Mohon tunggu verifikasi admin.', 'success')
            return redirect(url_for('main.dashboard'))
            
        else:
            flash('Format file tidak diizinkan. Gunakan PNG, JPG, atau JPEG.', 'error')
            return redirect(url_for('main.payment_info'))

    except Exception as e:
        print(f"Error in upload_payment_proof: {str(e)}")
        flash('Terjadi kesalahan saat mengupload bukti pembayaran', 'error')
        return redirect(url_for('main.payment_info'))

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



