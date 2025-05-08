from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, User, StudentForm, AcceptedStudent

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
    forms = StudentForm.query.all()
    return render_template('dashboard_admin.html', forms=forms)

# Middleware untuk memastikan hanya admin yang dapat mengakses
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Anda tidak memiliki akses ke halaman ini.", "danger")
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@admin_bp.route('/accept/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def accept_form(form_id):
    form = StudentForm.query.get_or_404(form_id)

    # Perbarui status di tabel StudentForm
    form.status = "Diterima"

    # Tambahkan data ke tabel AcceptedStudent
    accepted_student = AcceptedStudent(
        student_form_id=form.id,
        full_name=form.full_name,
        birth_date=form.birth_date,
        parent_name=form.parent_name,
        address=form.address,
        previous_school=form.previous_school,
        achievements=form.achievements,
        achievement_file=form.achievement_file
    )
    db.session.add(accepted_student)
    db.session.commit()

    flash(f"Formulir atas nama {form.full_name} diterima.", "success")
    return redirect(url_for('admin_bp.dashboard_admin'))


@admin_bp.route('/reject/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def reject_form(form_id):
    form = StudentForm.query.get_or_404(form_id)
    form.status = "Ditolak"
    db.session.commit()
    flash(f"Formulir atas nama {form.full_name} ditolak.", "warning")
    return redirect(url_for('admin_bp.dashboard_admin'))


@admin_bp.route('/delete/<int:form_id>', methods=['POST'])
@login_required
@admin_required
def delete_form(form_id):
    form = StudentForm.query.get_or_404(form_id)
    db.session.delete(form)
    db.session.commit()
    flash(f"Formulir atas nama {form.full_name} dihapus.", "danger")
    return redirect(url_for('admin_bp.dashboard_admin'))