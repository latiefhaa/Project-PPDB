from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app.models import db, User, StudentForm, AcceptedStudent, RejectedStudent, PaymentSPP
from datetime import datetime
from flask_mail import Message
from app import mail  # Add this import
from flask_wtf.csrf import generate_csrf
import pandas as pd
import io
from app.utils.email import send_email  # Add this import

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
    # Get accepted students
    accepted_students = StudentForm.query.filter_by(status="Diterima").all()
    
    # Get statistics
    stats = {
        'total': {
            'registrations': StudentForm.query.count(),
            'accepted': StudentForm.query.filter_by(status="Diterima").count(),
            'pending': StudentForm.query.filter_by(status="Menunggu").count(),
            'rejected': StudentForm.query.filter_by(status="Ditolak").count()
        },
        'payment': {
            'completed': StudentForm.query.filter_by(payment_status="Lunas").count(),
            'pending': StudentForm.query.filter_by(payment_status="Menunggu Verifikasi").count(),
            'not_paid': StudentForm.query.filter_by(payment_status="Belum Bayar").count()
        },
        'email': {
            'sent': 0  # We'll update this once email tracking is implemented
        }
    }
    
    return render_template('dashboard_admin.html', 
                         students=accepted_students,
                         stats=stats)

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
    try:
        # Get form
        form = StudentForm.query.get_or_404(form_id)

        # Update status
        form.status = "Menunggu Pembayaran"
        form.payment_status = "Belum Bayar"

        # Add notification for user
        user = User.query.get(form.user_id)
        if not user.notifications:
            user.notifications = []
            
        # Update notification with correct URL and action
        payment_url = url_for('main.payment_info', _external=True)  # Make sure this route exists
        notification = {
            'id': len(user.notifications) + 1,
            'type': 'acceptance',
            'message': 'Selamat! Pendaftaran Anda telah diterima. Silakan lakukan pembayaran dalam waktu 3x24 jam.',
            'timestamp': datetime.utcnow().isoformat(),
            'read': False,
            'has_action': True,
            'action_url': payment_url,  # Make sure this points to payment page
            'action_text': 'Bayar Sekarang',
            'is_important': True
        }
        user.notifications.append(notification)

        # Send email notification
        try:
            msg = Message(
                'Pendaftaran Diterima - PPDB Online',
                recipients=[user.email]
            )
            msg.html = f"""
            <h2>Selamat {form.full_name}!</h2>
            <p>Pendaftaran Anda telah diterima di sekolah kami.</p>
            <p>Silakan melakukan pembayaran sebesar Rp. 500.000 dalam waktu 3x24 jam.</p>
            <p>Klik link berikut untuk melakukan pembayaran:</p>
            <a href="{payment_url}" style="background-color: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                Bayar Sekarang
            </a>
            <br><br>
            <p>Terima kasih,<br>Tim PPDB Online</p>
            """
            mail.send(msg)
        except Exception as mail_error:
            print(f"Failed to send email: {str(mail_error)}")

        # Save changes
        db.session.commit()
        
        flash('Siswa berhasil diterima dan pemberitahuan telah dikirim', 'success')
        return redirect(url_for('admin_bp.form_admin'))

    except Exception as e:
        db.session.rollback()
        flash('Gagal memproses penerimaan siswa', 'error')
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
    # Add debug prints
    all_forms = StudentForm.query.all()
    print("\nAll forms in database:")
    for f in all_forms:
        print(f"ID: {f.id}, Name: {f.full_name}, Status: {f.status}, Payment: {f.payment_status}")

    # Get accepted forms
    forms = StudentForm.query.filter(
        StudentForm.status.in_(["Diterima", "Menunggu Pembayaran"])
    ).all()
    
    print("\nAccepted forms:")
    for f in forms:
        print(f"ID: {f.id}, Name: {f.full_name}, Status: {f.status}, Payment: {f.payment_status}")
    
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
    # Get forms waiting for payment verification
    pending_forms = StudentForm.query.filter_by(
        status="Menunggu Pembayaran",
        payment_status="Menunggu Verifikasi"
    ).all()
    
    return render_template('pending_payments.html', forms=pending_forms)

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
        # Update status
        form.payment_status = "Lunas"
        form.status = "Diterima"
        
        # Get user
        user = User.query.get(form.user_id)
        
        # Add notification
        if not user.notifications:
            user.notifications = []
            
        notification = {
            'type': 'payment_verified',
            'message': 'Pembayaran Anda telah diverifikasi. Selamat bergabung!',
            'timestamp': datetime.utcnow().isoformat(),
            'read': False
        }
        user.notifications.append(notification)
        
        # Send email notification using SMTP
        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a56db;">Selamat {form.full_name}!</h2>
            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="color: #1f2937; font-size: 16px;">
                    Pembayaran Anda telah berhasil diverifikasi. Anda resmi diterima di sekolah kami!
                </p>
                <h3 style="color: #1f2937;">Informasi Penting:</h3>
                <ul style="color: #4b5563;">
                    <li>Nomor Pendaftaran: {form.id}</li>
                    <li>Status: Diterima</li>
                    <li>Pembayaran: Lunas</li>
                </ul>
            </div>
            
            <div style="background-color: #e5edff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1e40af;">Langkah Selanjutnya:</h3>
                <ol style="color: #1e40af;">
                    <li>Simpan email ini sebagai bukti pembayaran</li>
                    <li>Tunggu informasi lebih lanjut mengenai jadwal orientasi</li>
                    <li>Persiapkan dokumen-dokumen yang diperlukan</li>
                </ol>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #4b5563; font-size: 14px;">
                    Terima kasih atas kepercayaan Anda.<br>
                    Tim PPDB Online
                </p>
            </div>
        </div>
        """
        
        success, message = send_email(
            user.email,
            'Pembayaran Diterima - PPDB Online',
            html_content
        )
        
        if not success:
            print(f"Failed to send email: {message}")
            
        # Commit changes to database
        db.session.commit()
        flash('Pembayaran berhasil diverifikasi dan email notifikasi telah dikirim', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in verify_payment: {str(e)}")
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        
    return redirect(url_for('admin_bp.pending_payments'))  # Fixed endpoint reference

@admin_bp.route('/manage_users')
@login_required
@admin_required
def manage_users():
    users = User.query.filter_by(is_admin=False).all()
    return render_template('manage_users.html', users=users)

@admin_bp.route('/manage_forms')
@login_required
@admin_required
def manage_forms():
    try:
        # Add debug logging
        all_forms = StudentForm.query.all()
        print("\nAll forms in database:")
        for form in all_forms:
            print(f"ID: {form.id}, Name: {form.full_name}, Status: {form.status}")
        
        csrf_token = generate_csrf()
        return render_template('manage_forms.html', forms=all_forms, csrf_token=csrf_token)
    except Exception as e:
        print(f"Error in manage_forms: {str(e)}")
        return f"Error: {str(e)}", 500

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if user.is_admin:
            return jsonify({'success': False, 'message': 'Tidak dapat menghapus akun admin'})
        
        # Delete associated forms first
        StudentForm.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'User {user.username} berhasil dihapus'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/delete_form/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def delete_form_ajax(form_id):
    try:
        print(f"\n=== Deleting form ID: {form_id} ===")
        
        # Get form and user
        form = StudentForm.query.get_or_404(form_id)
        print(f"Found form: {form.full_name}")
        
        # Begin transaction
        db.session.begin_nested()
        
        try:
            # 1. Delete all SPP records
            spp_count = PaymentSPP.query.filter_by(student_form_id=form.id).delete()
            print(f"Deleted {spp_count} SPP records")
            
            # 2. Delete accepted student record if exists
            acc_count = AcceptedStudent.query.filter_by(student_form_id=form.id).delete()
            print(f"Deleted {acc_count} accepted records")
            
            # 3. Delete rejected student record if exists
            rej_count = RejectedStudent.query.filter_by(student_form_id=form.id).delete()
            print(f"Deleted {rej_count} rejected records")
            
            # 4. Clean up user data
            user = User.query.get(form.user_id)
            if user:
                print(f"Cleaning up user data for: {user.username}")
                if user.notifications:
                    user.notifications = [n for n in user.notifications 
                                        if not any(str(form.id) in str(v) for v in n.values())]
                user.has_submitted_form = False
            
            # 5. Delete the form itself
            db.session.delete(form)
            print("Form deleted")
            
            # Commit the nested transaction
            db.session.commit()
            print("Transaction committed successfully")
            
            return jsonify({
                'success': True,
                'message': f'Formulir {form.full_name} berhasil dihapus',
                'csrf_token': generate_csrf()
            })
            
        except Exception as inner_error:
            # Rollback the nested transaction
            db.session.rollback()
            raise inner_error
            
    except Exception as e:
        # Rollback the main transaction
        db.session.rollback()
        error_msg = f"Error: {str(e)}"
        print(f"Failed to delete form: {error_msg}")
        return jsonify({
            'success': False,
            'message': f'Gagal menghapus formulir: {error_msg}'
        }), 500

@admin_bp.route('/spp_payments/<int:student_id>')
@login_required
@admin_required
def spp_payments(student_id):
    student = StudentForm.query.get_or_404(student_id)
    payments = PaymentSPP.query.filter_by(student_form_id=student_id).all()
    
    # Generate payment records for 12 months if not exists
    current_year = datetime.now().year
    months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    for month in months:
        existing = PaymentSPP.query.filter_by(
            student_form_id=student_id,
            month=month,
            year=current_year
        ).first()
        
        if not existing:
            payment = PaymentSPP(
                student_form_id=student_id,
                amount=500000,  # Jumlah SPP
                month=month,
                year=current_year,
                payment_status="Belum Bayar"
            )
            db.session.add(payment)
    
    db.session.commit()
    return render_template('spp_payments.html', student=student, payments=payments)

@admin_bp.route('/verify_spp/<int:payment_id>', methods=['POST'])
@login_required
@admin_required
def verify_spp(payment_id):
    payment = PaymentSPP.query.get_or_404(payment_id)
    
    try:
        payment.payment_status = "Lunas"
        payment.verified = True
        payment.payment_date = datetime.utcnow()
        
        # Add notification
        student = StudentForm.query.get(payment.student_form_id)
        user = User.query.get(student.user_id)
        
        notification = {
            'type': 'spp_verified',
            'message': f'Pembayaran SPP bulan {payment.month} telah diverifikasi',
            'timestamp': datetime.utcnow().isoformat(),
            'read': False
        }
        user.notifications.append(notification)
        
        db.session.commit()
        flash('Pembayaran SPP berhasil diverifikasi', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal memverifikasi pembayaran: {str(e)}', 'error')
    
    return redirect(url_for('admin_bp.spp_payments', student_id=payment.student_form_id))

# Add these new routes
@admin_bp.route('/export_registrations')
@login_required
@admin_required
def export_registrations():
    try:
        # Get all forms
        forms = StudentForm.query.all()
        
        # Create DataFrame
        data = []
        for form in forms:
            data.append({
                'ID': form.id,
                'Nama Lengkap': form.full_name,
                'Jenis Kelamin': 'Laki-laki' if form.gender == 'L' else 'Perempuan',
                'Tempat Lahir': form.birth_place,
                'Tanggal Lahir': form.birth_date.strftime('%d-%m-%Y'),
                'Agama': form.religion,
                'NISN': form.nisn,
                'Nama Ayah': form.father_name,
                'Nama Ibu': form.mother_name,
                'No. HP Orang Tua': form.parent_phone,
                'Pekerjaan Orang Tua': form.parent_occupation,
                'Alamat': form.address,
                'Asal Sekolah': form.previous_school,
                'Status': form.status,
                'Status Pembayaran': form.payment_status,
                'Tanggal Daftar': form.created_at.strftime('%d-%m-%Y %H:%M')
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel buffer
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Data Pendaftaran', index=False)
        
        output.seek(0)
        
        # Generate filename with timestamp
        filename = f'Data_Pendaftaran_PPDB_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Error exporting data: {str(e)}")
        flash('Gagal mengekspor data', 'error')
        return redirect(url_for('admin_bp.dashboard_admin'))

@admin_bp.route('/registration_statistics')
@login_required
@admin_required
def registration_statistics():
    try:
        # Basic statistics
        total_registrations = StudentForm.query.count()
        total_accepted = StudentForm.query.filter_by(status="Diterima").count()
        total_pending = StudentForm.query.filter_by(status="Menunggu").count()
        total_rejected = StudentForm.query.filter_by(status="Ditolak").count()
        
        # Gender statistics
        male_count = StudentForm.query.filter_by(gender="L").count()
        female_count = StudentForm.query.filter_by(gender="P").count()
        
        # Payment statistics
        payment_completed = StudentForm.query.filter_by(payment_status="Lunas").count()
        payment_pending = StudentForm.query.filter_by(payment_status="Menunggu Verifikasi").count()
        payment_not_paid = StudentForm.query.filter_by(payment_status="Belum Bayar").count()
        
        # Religion statistics
        religions = db.session.query(
            StudentForm.religion,
            db.func.count(StudentForm.id)
        ).group_by(StudentForm.religion).all()
        
        religion_labels = [r[0] for r in religions]
        religion_data = [r[1] for r in religions]
        
        stats = {
            'total': {
                'registrations': total_registrations,
                'accepted': total_accepted,
                'pending': total_pending,
                'rejected': total_rejected
            },
            'gender': {
                'male': male_count,
                'female': female_count
            },
            'payment': {
                'completed': payment_completed,
                'pending': payment_pending,
                'not_paid': payment_not_paid
            },
            'religion': {
                'labels': religion_labels,
                'data': religion_data
            }
        }
        
        return render_template('statistics.html', stats=stats)
        
    except Exception as e:
        print(f"Error generating statistics: {str(e)}")
        flash('Gagal memuat statistik', 'error')
        return redirect(url_for('admin_bp.dashboard_admin'))

@admin_bp.route('/send_acceptance_email/<int:form_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def send_acceptance_email(form_id):
    form = StudentForm.query.get_or_404(form_id)
    user = User.query.get(form.user_id)
    
    if request.method == 'POST':
        try:
            # Get custom message from form
            custom_message = request.form.get('custom_message', '')
            
            msg = Message(
                'Informasi Penerimaan Siswa - PPDB Online',
                recipients=[user.email]
            )
            
            msg.html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #1a56db;">Selamat {form.full_name}!</h2>
                
                <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #1f2937; font-size: 16px;">
                        Kami dengan senang hati memberitahukan bahwa Anda telah resmi diterima sebagai siswa baru.
                        Status pembayaran Anda telah dikonfirmasi LUNAS.
                    </p>
                    
                    <h3 style="color: #1f2937;">Detail Siswa:</h3>
                    <ul style="color: #4b5563;">
                        <li>Nomor Pendaftaran: {form.id}</li>
                        <li>Nama: {form.full_name}</li>
                        <li>Status: Diterima</li>
                        <li>Pembayaran: Lunas</li>
                    </ul>
                </div>
                
                <div style="background-color: #e5edff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #1e40af;">Pesan dari Admin:</h3>
                    <p style="color: #1e40af;">{custom_message}</p>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="color: #4b5563; font-size: 14px;">
                        Terima kasih atas kepercayaan Anda.<br>
                        Tim PPDB Online
                    </p>
                </div>
            </div>
            """
            
            mail.send(msg)
            flash('Email berhasil dikirim ke siswa', 'success')
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            flash('Gagal mengirim email', 'error')
            
        return redirect(url_for('admin_bp.accepted_forms'))
        
    return render_template('send_email.html', student=form)

@admin_bp.route('/payment_completed_emails')
@login_required
@admin_required
def payment_completed_emails():
    # Get students who have completed payments
    paid_students = StudentForm.query.filter_by(
        status="Diterima",
        payment_status="Lunas"
    ).all()
    return render_template('payment_completed_emails.html', students=paid_students)

@admin_bp.route('/send_payment_confirmation/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def send_payment_confirmation(form_id):
    form = StudentForm.query.get_or_404(form_id)
    user = User.query.get(form.user_id)
    
    try:
        # Prepare email content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a56db;">Konfirmasi Pembayaran - {form.full_name}</h2>
            
            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="color: #1f2937; font-size: 16px;">
                    Pembayaran Anda telah kami terima dan verifikasi. 
                    Selamat! Anda telah resmi terdaftar sebagai siswa baru.
                </p>
                
                <h3 style="color: #1f2937;">Detail Pembayaran:</h3>
                <ul style="color: #4b5563;">
                    <li>Nomor Pendaftaran: {form.id}</li>
                    <li>Nama Lengkap: {form.full_name}</li>
                    <li>Status: Diterima</li>
                    <li>Pembayaran: Lunas</li>
                </ul>
            </div>
            
            <div style="background-color: #e5edff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1e40af;">Langkah Selanjutnya:</h3>
                <ol style="color: #1e40af;">
                    <li>Simpan email ini sebagai bukti pembayaran</li>
                    <li>Tunggu informasi selanjutnya mengenai jadwal orientasi</li>
                    <li>Persiapkan dokumen-dokumen yang diperlukan</li>
                </ol>
            </div>
            
            <p style="color: #4b5563; font-size: 14px; margin-top: 20px;">
                Terima kasih atas kepercayaan Anda.<br>
                Tim PPDB Online
            </p>
        </div>
        """
        
        try:
            # Send email using Flask-Mail
            msg = Message(
                'Konfirmasi Pembayaran - PPDB Online',
                sender=('PPDB Online', 'noreply@ppdbonline.com'),  # Add sender
                recipients=[user.email]
            )
            msg.html = html_content
            mail.send(msg)
            
            # Update notification only if email sent successfully
            if not user.notifications:
                user.notifications = []
                
            notification = {
                'type': 'payment_confirmation',
                'message': 'Email konfirmasi pembayaran telah dikirim',
                'timestamp': datetime.utcnow().isoformat(),
                'read': False
            }
            user.notifications.append(notification)
            
            db.session.commit()
            flash(f'Email konfirmasi berhasil dikirim ke {form.full_name}', 'success')
            
        except Exception as mail_error:
            print(f"Detailed mail error: {str(mail_error)}")
            # Try alternate email sending method
            try:
                success, message = send_email(
                    user.email,
                    'Konfirmasi Pembayaran - PPDB Online',
                    html_content
                )
                if success:
                    flash(f'Email konfirmasi berhasil dikirim ke {form.full_name}', 'success')
                else:
                    raise Exception(message)
            except Exception as alt_error:
                print(f"Alternative mail method failed: {str(alt_error)}")
                raise Exception("Gagal mengirim email melalui kedua metode")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error sending payment confirmation: {str(e)}")
        flash(f'Gagal mengirim email konfirmasi: {str(e)}', 'error')
    
    return redirect(url_for('admin_bp.payment_completed_emails'))