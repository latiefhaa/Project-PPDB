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
    is_admin = db.Column(db.Boolean, default=False)  # True untuk admin, False untuk user biasa

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Model untuk Formulir Pendaftaran Siswa
class StudentForm(db.Model):
    __tablename__ = 'student_forms'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    previous_school = db.Column(db.String(100), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Rejected

    # Relasi ke tabel User
    user = db.relationship('User', backref=db.backref('student_forms', lazy=True))