from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    notifications = db.Column(db.JSON, nullable=True, default=list)
    has_submitted_form = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class StudentForm(db.Model):
    __tablename__ = 'student_forms'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(1), nullable=False)
    birth_place = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    religion = db.Column(db.String(20), nullable=False)
    nisn = db.Column(db.String(20), nullable=False)
    father_name = db.Column(db.String(100), nullable=False)
    mother_name = db.Column(db.String(100), nullable=False)
    parent_phone = db.Column(db.String(15), nullable=False)
    parent_occupation = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    previous_school = db.Column(db.String(100), nullable=False)
    achievement_file = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Menunggu')
    payment_proof = db.Column(db.String(255), nullable=True)
    payment_status = db.Column(db.String(20), default='Belum Bayar')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('student_form', uselist=False))

class AcceptedStudent(db.Model):
    __tablename__ = 'accepted_students'
    id = db.Column(db.Integer, primary_key=True)
    student_form_id = db.Column(db.Integer, db.ForeignKey('student_forms.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    parent_name = db.Column(db.String(150), nullable=False)
    previous_school = db.Column(db.String(150), nullable=False)
    acceptance_date = db.Column(db.DateTime, default=datetime.utcnow)
    student_form = db.relationship('StudentForm', backref=db.backref('accepted_student', uselist=False))

class RejectedStudent(db.Model):
    __tablename__ = 'rejected_students'
    id = db.Column(db.Integer, primary_key=True)
    student_form_id = db.Column(db.Integer, db.ForeignKey('student_forms.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    parent_name = db.Column(db.String(150), nullable=False)
    previous_school = db.Column(db.String(150), nullable=False)
    rejection_date = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=True)
    student_form = db.relationship('StudentForm', backref=db.backref('rejected_student', uselist=False))