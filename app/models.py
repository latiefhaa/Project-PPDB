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

    # Basic relationships
    user = db.relationship('User', backref='forms')
    accepted_record = db.relationship('AcceptedStudent', backref='form', 
                                    uselist=False, cascade='all, delete-orphan')
    rejected_record = db.relationship('RejectedStudent', backref='form', 
                                    uselist=False, cascade='all, delete-orphan')
    # Add this relationship
    spp_payments = db.relationship('PaymentSPP', backref='student', 
                                 lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_payment_completed(self):
        return self.payment_status == "Lunas" and self.status == "Diterima"

    def update_payment_status(self):
        if self.payment_status == "Lunas":
            self.status = "Diterima"
            db.session.add(
                AcceptedStudent(
                    student_form_id=self.id,
                    full_name=self.full_name,
                    birth_date=self.birth_date,
                    father_name=self.father_name,
                    previous_school=self.previous_school
                )
            )

class AcceptedStudent(db.Model):
    __tablename__ = 'accepted_students'
    id = db.Column(db.Integer, primary_key=True)
    student_form_id = db.Column(db.Integer, db.ForeignKey('student_forms.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    father_name = db.Column(db.String(150), nullable=False)
    previous_school = db.Column(db.String(150), nullable=False)
    acceptance_date = db.Column(db.DateTime, default=datetime.utcnow)
    
class RejectedStudent(db.Model):
    __tablename__ = 'rejected_students'
    id = db.Column(db.Integer, primary_key=True)
    student_form_id = db.Column(db.Integer, db.ForeignKey('student_forms.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    father_name = db.Column(db.String(150), nullable=False)
    previous_school = db.Column(db.String(150), nullable=False)
    rejection_date = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=True)

class PaymentSPP(db.Model):
    __tablename__ = 'payment_spp'
    id = db.Column(db.Integer, primary_key=True)
    student_form_id = db.Column(db.Integer, db.ForeignKey('student_forms.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_status = db.Column(db.String(20), default="Belum Bayar")
    proof_of_payment = db.Column(db.String(255))
    verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime, nullable=True)

    def verify_payment(self):
        try:
            self.verified = True
            self.payment_status = "Lunas"
            self.verification_date = datetime.utcnow()
            
            # Get associated student form
            student_form = StudentForm.query.get(self.student_form_id)
            if student_form:
                student_form.payment_status = "Lunas"
                student_form.status = "Diterima"
                
                # Create AcceptedStudent record if not exists
                if not student_form.accepted_record:
                    accepted = AcceptedStudent(
                        student_form_id=student_form.id,
                        full_name=student_form.full_name,
                        birth_date=student_form.birth_date,
                        father_name=student_form.father_name,
                        previous_school=student_form.previous_school
                    )
                    db.session.add(accepted)
            
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error verifying payment: {str(e)}")
            db.session.rollback()
            return False