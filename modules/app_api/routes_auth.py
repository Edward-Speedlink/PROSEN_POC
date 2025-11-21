from flask import Blueprint, request, jsonify
from models import db, User
from flask_jwt_extended import create_access_token
from flask_bcrypt import Bcrypt

auth_bp = Blueprint("auth_bp", __name__)
bcrypt = Bcrypt()

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    existing_user = User.query.filter(
        (User.email == data.get("email")) | (User.phone == data.get("phone"))
    ).first()
    if existing_user:
        return jsonify({"message": "User already exists"}), 400

    user = User(
        full_name=data["full_name"],
        email=data.get("email"),
        phone=data.get("phone"),
        role=data.get("role", "citizen"),
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Registration successful"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    identifier = data.get("email") or data.get("phone")
    password = data.get("password")

    user = User.query.filter(
        (User.email == identifier) | (User.phone == identifier)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity={"id": user.id, "role": user.role})
    return jsonify({"access_token": access_token, "user": {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role
    }}), 200
