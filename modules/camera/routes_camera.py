# camera_blueprint.py (or wherever your blueprint is defined)
from flask import Blueprint, jsonify, url_for, Response
from .streams import get_stream_response, CAMERAS, get_current_detections, generate_multi_stream

camera_bp = Blueprint('camera', __name__, url_prefix='/cameras')


# camera_blueprint.py → REPLACE build_camera_metadata

def build_camera_metadata(key):
    pretty_name = key.replace("_", " ").title()
    stream_url = url_for("camera.stream", camera_id=key, _external=True)
    return {
        "id": key,
        "name": pretty_name,
        "location": "Unknown",
        "status": "online",
        "quality": "HD",
        "lastActivity": "just now",
        "detections": 0,                    # ← Now just 0 (fast!)
        "people": 0,
        "vehicles": 0,
        "streamUrl": stream_url,
        "detected_objects": {"people": 0, "vehicles": 0, "animals": 0}
    }
# Too much work on the server due to CPU
# def build_camera_metadata(key):
#     pretty_name = key.replace("_", " ").title()
#     stream_url = url_for("camera.stream", camera_id=key, _external=True)
#     rtsp_url = CAMERAS.get(key.lower())
#     detected = get_current_detections(rtsp_url)
#     total_detections = sum(detected.values())
#     return {
#         "id": key,
#         "name": pretty_name,
#         "location": "Unknown",
#         "status": "online",
#         "quality": "HD",
#         "lastActivity": "just now",
#         "detections": total_detections,
#         "streamUrl": stream_url,
#         "detected_objects": detected  # New field with breakdown (e.g., {"people": 4, "vehicles": 2, "animals": 1})
#     }

@camera_bp.route('/', methods=['GET'])
def get_cameras():
    return jsonify([build_camera_metadata(k) for k in CAMERAS.keys()])

@camera_bp.route('/<camera_id>', methods=['GET'])
def get_camera(camera_id):
    key = camera_id.lower()
    if key not in CAMERAS:
        return jsonify({"error": "Camera not found"}), 404
    return jsonify(build_camera_metadata(key))

@camera_bp.route('/<camera_id>/stream')
def stream(camera_id):
    return get_stream_response(camera_id) or ("No camera", 404)

@camera_bp.route('/multi_stream')
def multi_stream():
    return Response(generate_multi_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")








# from flask import Blueprint, Response
# # from .streams import get_stream_response
# from .streams import get_stream_response, CAMERAS


# camera_bp = Blueprint('camera', __name__)

# @camera_bp.route('/stream/<camera_id>')
# def stream(camera_id):
#     return get_stream_response(camera_id) or ("No camera", 404)
