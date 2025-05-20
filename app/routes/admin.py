from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, User, StudentForm, AcceptedStudent, RejectedStudent
from datetime import datetime
from flask_mail import Message
from app import mail  # Add this import

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

@admin_bp.route('/dashboard_admin', methods=['GET'])
@login_required
@admin_required
def dashboard_admin():
    return render_template('dashboard_admin.html')

@admin_bp.route('/form_admin', methods=['GET'])
@login_required
@admin_required
def form_admin():
    # Hanya tampilkan formulir dengan status Menunggu
    forms = StudentForm.query.filter_by(status="Menunggu").all()
    return render_template('form_admin.html', forms=forms)

@admin_bp.route('/form_detail/<int:form_id>', methods=['GET'])
@login_required
@admin_required
def form_detail(form_id):
    form = StudentForm.query.get_or_404(form_id)
    return render_template('form_detail.html', form=form)

@admin_bp.route('/accept/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def accept_form(form_id):
    form = StudentForm.query.get_or_404(form_id)
    
    if form.status != "Menunggu":
        flash('Formulir ini sudah diproses sebelumnya.', 'warning')
        return redirect(url_for('admin_bp.form_admin'))
    
    try:
        # Update form status
        form.status = "Menunggu Pembayaran"
        form.payment_status = "Belum Bayar"
        
        # Create accepted student record
        accepted = AcceptedStudent(
            student_form_id=form.id,
            full_name=form.full_name,
            birth_date=form.birth_date,
            parent_name=form.father_name,
            previous_school=form.previous_school
        )
        db.session.add(accepted)
        
        # Add notifications
        user = User.query.get(form.user_id)
        if user.notifications is None:
            user.notifications = []
            
        payment_link = url_for('main.payment_page', form_id=form.id, _external=True)
        
        notifications = [
            {
                'type': 'acceptance',
                'message': 'Selamat! Pendaftaran Anda telah diterima.',
                'timestamp': datetime.utcnow().isoformat(),
                'read': False
            },
            {
                'type': 'payment',
                'message': f'Silakan lakukan pembayaran dengan mengklik link berikut: {payment_link}',
                'timestamp': datetime.utcnow().isoformat(),
                'read': False,
                'action_url': payment_link,
                'action_text': 'Bayar Sekarang'
            }
        ]
        user.notifications.extend(notifications)
        
        # Send email
        try:
            msg = Message(
                'Selamat! Pendaftaran Anda Diterima',
                recipients=[user.email]
            )
            msg.html = f"""
            <h2>Selamat {form.full_name}!</h2>
            <p>Pendaftaran Anda telah diterima di sekolah kami.</p>
            
            <h3>Langkah Selanjutnya:</h3>
            <p>Silakan melakukan pembayaran biaya pendaftaran:</p>
            <ul>
                <li>Nominal: Rp. 500.000</li>
                <li>Bank: BCA</li>
                <li>No. Rekening: 1234567890</li>
                <li>Atas Nama: PPDB Online</li>
            </ul>
            
            <p>
                <a href="{payment_link}" 
                   style="background-color: #4CAF50; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Lakukan Pembayaran
                </a>
            </p>
            """
            mail.send(msg)
        except Exception as mail_error:
            print(f"Email error: {str(mail_error)}")
            flash('Penerimaan berhasil tetapi gagal mengirim email', 'warning')
        
        db.session.commit()
        flash('Siswa berhasil diterima dan notifikasi telah dikirim', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in accept_form: {str(e)}")
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
    
    return redirect(url_for('admin_bp.form_admin'))

@admin_bp.route('/reject/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def reject_form(form_id):
    form = StudentForm.query.get_or_404(form_id)
    
    if form.status != "Menunggu":
        flash('Formulir ini sudah diproses sebelumnya.', 'warning')
        return redirect(url_for('admin_bp.form_admin'))
    
    reason = request.form.get('reason', 'Tidak ada alasan yang diberikan')
    
    try:
        # Update form status
        form.status = "Ditolak"
        
        # Create rejected record
        rejected = RejectedStudent(
            student_form_id=form.id,
            full_name=form.full_name,
            birth_date=form.birth_date,
            parent_name=form.father_name,
            previous_school=form.previous_school,
            reason=reason
        )
        db.session.add(rejected)
        
        # Add notification
        user = User.query.get(form.user_id)
        if user.notifications is None:
            user.notifications = []
        
        notification = {
            'type': 'rejection',
            'message': f'Maaf, pendaftaran Anda ditolak. Alasan: {reason}',
            'timestamp': datetime.utcnow().isoformat(),
            'read': False
        }
        user.notifications.append(notification)
        
        # Send email
        try:
            msg = Message(
                'Status Pendaftaran PPDB',
                recipients=[user.email]
            )
            msg.html = f"""
            <h2>Kepada {form.full_name}</h2>
            <p>Mohon maaf, pendaftaran Anda belum dapat kami terima.</p>
            <p><strong>Alasan:</strong> {reason}</p>
            <p>Anda dapat mencoba mendaftar kembali pada periode berikutnya.</p>
            <br>
            <p>Salam,<br>Tim PPDB Online</p>
            """
            mail.send(msg)
        except Exception as mail_error:
            print(f"Email error: {str(mail_error)}")
            flash('Penolakan berhasil tetapi gagal mengirim email', 'warning')
        
        db.session.commit()
        flash('Siswa telah ditolak dan notifikasi telah dikirim', 'warning')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in reject_form: {str(e)}")
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
    
    return redirect(url_for('admin_bp.form_admin'))

@admin_bp.route('/delete/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def delete_form(form_id):
    form = StudentForm.query.get_or_404(form_id)
    db.session.delete(form)
    db.session.commit()
    flash(f"Formulir atas nama {form.full_name} dihapus.", "danger")
    return redirect(url_for('admin_bp.dashboard_admin'))

@admin_bp.route('/accepted_forms', methods=['GET'])
@login_required
@admin_required
def accepted_forms():
    forms = StudentForm.query.filter_by(status="Diterima").all()
    return render_template('accepted_forms.html', forms=forms)

@admin_bp.route('/rejected_forms', methods=['GET'])
@login_required
@admin_required
def rejected_forms():
    forms = StudentForm.query.filter_by(status="Ditolak").all()
    return render_template('rejected_forms.html', forms=forms)

@admin_bp.route('/accepted_students')
@login_required
@admin_required
def accepted_students():
    accepted = AcceptedStudent.query.all()
    return render_template('accepted_students.html', students=accepted)

@admin_bp.route('/rejected_students')
@login_required
@admin_required
def rejected_students():
    rejected = RejectedStudent.query.all()
    return render_template('rejected_students.html', students=rejected)

@admin_bp.route('/pending_payments')
@login_required
@admin_required
def pending_payments():
    forms = StudentForm.query.filter_by(
        status="Menunggu Pembayaran",
        payment_status="Belum Bayar"
    ).all()
    current_year = datetime.now().year
    return render_template('pending_payments.html', forms=forms, year=current_year)

@admin_bp.route('/completed_payments')
@login_required
@admin_required
def completed_payments():
    forms = StudentForm.query.filter_by(
        payment_status="Lunas"
    ).all()
    return render_template('completed_payments.html', forms=forms)

@admin_bp.route('/verify_payment/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def verify_payment(form_id):
    form = StudentForm.query.get_or_404(form_id)
    try:
        form.payment_status = "Lunas"
        form.status = "Diterima"
        
        # Add notification
        user = User.query.get(form.user_id)
        if user.notifications is None:
            user.notifications = []
            
        notification = {
            'type': 'payment_verified',
            'message': 'Pembayaran Anda telah diverifikasi. Selamat bergabung!',
            'timestamp': datetime.utcnow().isoformat(),
            'read': False
        }
        user.notifications.append(notification)
        
        # Send email
        msg = Message(
            'Pembayaran Berhasil Diverifikasi',
            sender='your-email@gmail.com',
            recipients=[user.email]
        )
        msg.html = f"""
        <h2>Pembayaran Berhasil!</h2>
        <p>Halo {form.full_name},</p>
        <p>Pembayaran Anda telah kami verifikasi. Selamat bergabung sebagai siswa baru!</p>
        <p>Silakan tunggu informasi selanjutnya mengenai jadwal masuk sekolah.</p>
        <br>
        Salam,<br>
        Tim PPDB Online
        """
        mail.send(msg)
        
        db.session.commit()
        flash('Pembayaran berhasil diverifikasi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'error')