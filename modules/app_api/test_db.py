from flask import Blueprint, jsonify
from sqlalchemy import inspect
from modules.extensions import db
from models import User, Vehicle, Complaint

test_bp = Blueprint("test_bp", __name__)

@test_bp.route("/test-db")
def test_db():
    try:
        # Use SQLAlchemy inspector for 2.x+
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        # Optional: count records safely
        users_count = User.query.count() if "users" in tables else 0
        vehicles_count = Vehicle.query.count() if "vehicles" in tables else 0
        complaints_count = Complaint.query.count() if "complaints" in tables else 0

        return jsonify({
            "tables": tables,
            "users_count": users_count,
            "vehicles_count": vehicles_count,
            "complaints_count": complaints_count,
            "success": True
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
