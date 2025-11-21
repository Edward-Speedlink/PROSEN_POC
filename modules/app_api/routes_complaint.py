from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Complaint, User
from datetime import datetime

complaint_bp = Blueprint("complaint_bp", __name__)

def get_current_user():
    identity = get_jwt_identity()
    if not identity:
        return None
    return User.query.get(identity["id"])

# --------------------------------------------------------
# Submit a complaint
# --------------------------------------------------------
@complaint_bp.route("/", methods=["POST"])
@jwt_required()
def submit_complaint():
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    complaint = Complaint(
        user_id=user.id,
        subject=data.get("subject"),
        description=data.get("description"),
        status="pending"
    )

    db.session.add(complaint)
    db.session.commit()

    return jsonify({"message": "Complaint submitted successfully"}), 201


# --------------------------------------------------------
# Get all complaints by logged-in user
# --------------------------------------------------------
@complaint_bp.route("/", methods=["GET"])
@jwt_required()
def get_user_complaints():
    user = get_current_user()
    complaints = Complaint.query.filter_by(user_id=user.id).order_by(Complaint.created_at.desc()).all()

    return jsonify([
        {
            "id": c.id,
            "subject": c.subject,
            "description": c.description,
            "status": c.status,
            "created_at": c.created_at.isoformat()
        } for c in complaints
    ]), 200


# --------------------------------------------------------
# Update complaint status (for law enforcement)
# --------------------------------------------------------
@complaint_bp.route("/<int:complaint_id>", methods=["PUT"])
@jwt_required()
def update_complaint(complaint_id):
    user = get_current_user()
    data = request.get_json()
    complaint = Complaint.query.get_or_404(complaint_id)

    # Only law enforcement should change status
    if user.role != "law_enforcement":
        return jsonify({"message": "Unauthorized"}), 403

    complaint.status = data.get("status", complaint.status)
    db.session.commit()
    return jsonify({"message": "Complaint status updated"}), 200
