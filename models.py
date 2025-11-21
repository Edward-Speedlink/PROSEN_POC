from datetime import datetime
from modules.extensions import db  # ✅ use the same db instance
from flask_bcrypt import generate_password_hash, check_password_hash

# ------------------------------
# User Model
# ------------------------------
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='citizen')  # 'citizen' or 'law_enforcement'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)
    complaints = db.relationship('Complaint', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ------------------------------
# Vehicle Model
# ------------------------------
class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    vin = db.Column(db.String(50))
    engine_number = db.Column(db.String(50))
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    vehicle_type = db.Column(db.String(50))
    year_of_manufacture = db.Column(db.String(10))
    usage = db.Column(db.String(50))
    color = db.Column(db.String(30))
    source = db.Column(db.String(100))
    speedtrack_id = db.Column(db.String(50))
    licensing_office = db.Column(db.String(100))
    state_of_registration = db.Column(db.String(100))
    current_location = db.Column(db.String(255))
    is_stolen = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------------------
# Complaint Model
# ------------------------------
class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(255))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)