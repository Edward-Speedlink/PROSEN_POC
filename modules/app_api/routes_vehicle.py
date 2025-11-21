from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Vehicle, User
from datetime import datetime
from flask_socketio import SocketIO, emit

vehicle_bp = Blueprint("vehicle_bp", __name__)

# WebSocket instance (will be initialized from app)
socketio = SocketIO(cors_allowed_origins="*")

# --------------------------------------------------------
# Helper: Get current user
# --------------------------------------------------------
def get_current_user():
    identity = get_jwt_identity()
    if not identity:
        return None
    return User.query.get(identity["id"])

# --------------------------------------------------------
# Add a new vehicle
# --------------------------------------------------------
@vehicle_bp.route("/", methods=["POST"])
@jwt_required()
def add_vehicle():
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()

    existing = Vehicle.query.filter_by(license_plate=data.get("license_plate")).first()
    if existing:
        return jsonify({"message": "Vehicle already registered"}), 400

    vehicle = Vehicle(
        user_id=user.id,
        license_plate=data["license_plate"],
        vin=data.get("vin"),
        engine_number=data.get("engine_number"),
        make=data.get("make"),
        model=data.get("model"),
        vehicle_type=data.get("vehicle_type"),
        year_of_manufacture=data.get("year_of_manufacture"),
        usage=data.get("usage"),
        color=data.get("color"),
        source=data.get("source"),
        speedtrack_id=data.get("speedtrack_id"),
        licensing_office=data.get("licensing_office"),
        state_of_registration=data.get("state_of_registration"),
        current_location=data.get("current_location"),
    )

    db.session.add(vehicle)
    db.session.commit()

    return jsonify({"message": "Vehicle added successfully"}), 201


# --------------------------------------------------------
# Get all vehicles for logged-in user
# --------------------------------------------------------
@vehicle_bp.route("/", methods=["GET"])
@jwt_required()
def get_user_vehicles():
    user = get_current_user()
    vehicles = Vehicle.query.filter_by(user_id=user.id).all()
    return jsonify([
        {
            "id": v.id,
            "license_plate": v.license_plate,
            "make": v.make,
            "model": v.model,
            "color": v.color,
            "usage": v.usage,
            "is_stolen": v.is_stolen
        } for v in vehicles
    ]), 200


# --------------------------------------------------------
# Edit vehicle details
# --------------------------------------------------------
@vehicle_bp.route("/<int:vehicle_id>", methods=["PUT"])
@jwt_required()
def update_vehicle(vehicle_id):
    user = get_current_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.user_id != user.id:
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    for key, value in data.items():
        if hasattr(vehicle, key):
            setattr(vehicle, key, value)

    db.session.commit()
    return jsonify({"message": "Vehicle updated successfully"}), 200


# --------------------------------------------------------
# Delete a vehicle
# --------------------------------------------------------
@vehicle_bp.route("/<int:vehicle_id>", methods=["DELETE"])
@jwt_required()
def delete_vehicle(vehicle_id):
    user = get_current_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.user_id != user.id:
        return jsonify({"message": "Unauthorized"}), 403

    db.session.delete(vehicle)
    db.session.commit()
    return jsonify({"message": "Vehicle deleted successfully"}), 200


# --------------------------------------------------------
# Report a vehicle as stolen
# --------------------------------------------------------
@vehicle_bp.route("/report-stolen/<int:vehicle_id>", methods=["POST"])
@jwt_required()
def report_stolen(vehicle_id):
    user = get_current_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.user_id != user.id:
        return jsonify({"message": "Unauthorized"}), 403

    if vehicle.is_stolen:
        return jsonify({"message": "Vehicle already reported stolen"}), 400

    vehicle.is_stolen = True
    db.session.commit()

    # Broadcast alert to law enforcement dashboards
    alert_data = {
        "event": "vehicle_reported_stolen",
        "license_plate": vehicle.license_plate,
        "owner": user.full_name,
        "make": vehicle.make,
        "model": vehicle.model,
        "color": vehicle.color,
        "location": vehicle.current_location,
        "reported_at": datetime.utcnow().isoformat()
    }

    socketio.emit("stolen_vehicle_alert", alert_data, namespace="/alerts")

    return jsonify({
        "message": "Vehicle reported as stolen",
        "alert_sent": True,
        "vehicle": alert_data
    }), 200
