import cv2
from flask import Flask, Response, jsonify, render_template
from flask_socketio import SocketIO, leave_room
from modules.ai.routes_ai import ai_bp
from modules.camera.routes_camera import camera_bp
# from modules.drone.routes_drone import drone_bp
from modules.app_api.routes_auth import auth_bp
from modules.app_api.routes_vehicle import vehicle_bp
from modules.app_api.routes_complaint import complaint_bp
from flask_cors import CORS
from flask import send_from_directory
# from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
# from flask_bcrypt import Bcrypt
# from flask_jwt_extended import JWTManager
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, JWT_SECRET_KEY, CAMERAS
import os
from modules.app_api.test_db import test_bp
from modules.extensions import db, migrate, bcrypt, jwt
from models import User, Vehicle, Complaint
import eventlet



# # Initialize extensions
# db = SQLAlchemy()
# migrate = Migrate()
# bcrypt = Bcrypt()
# jwt = JWTManager()

# eventlet.monkey_patch()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY

# eventlet.monkey_patch()

socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True, supports_credentials=True,
     expose_headers=["Content-Type"],
     allow_headers=["*"])
# Allow frontend at :5173 to call backend at :5000
CORS(app, origins="*")

# --- CORS Setup ---
# Allow requests from your Vite frontend (localhost:5173)
# CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
#      supports_credentials=True)

# # --- Socket.IO Setup ---
# # Must also explicitly allow the same origins for WebSocket
# socketio = SocketIO(
#     app,
#     cors_allowed_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
#     logger=True,
#     engineio_logger=True,
#     async_mode="threading"  
# )


# Initialize with app
db.init_app(app)
migrate.init_app(app, db)
bcrypt.init_app(app)
jwt.init_app(app)

# Register blueprints
app.register_blueprint(ai_bp, url_prefix='/ai')
app.register_blueprint(camera_bp)
# app.register_blueprint(drone_bp, url_prefix='/drone')
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(vehicle_bp, url_prefix="/api/vehicles")
app.register_blueprint(complaint_bp, url_prefix="/api/complaints")
app.register_blueprint(test_bp, url_prefix="/api")



# Global dictionary to store camera instances
camera_instances = {}

def generate_frames(camera_id):
    """Generate frames from camera for streaming"""
    rtsp_url = CAMERAS.get(camera_id.lower())
    if not rtsp_url:
        return
    
    # Create or reuse camera instance
    if camera_id not in camera_instances:
        camera_instances[camera_id] = cv2.VideoCapture(rtsp_url)
    
    cap = camera_instances[camera_id]
    
    while True:
        success, frame = cap.read()
        if not success:
            # Try to reconnect if frame read fails
            cap.release()
            cap = cv2.VideoCapture(rtsp_url)
            camera_instances[camera_id] = cap
            continue
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/stream/<camera_id>')
def stream_feed(camera_id):
    """Stream camera feed as MJPEG"""
    rtsp_url = CAMERAS.get(camera_id.lower())
    if not rtsp_url:
        return "Camera not found", 404
    
    return Response(generate_frames(camera_id),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/plate_test')
def plate_test():
    return render_template('plate_test.html')

@app.route('/camera_status')
def camera_status():
    """Check if cameras are accessible"""
    status = {}
    for cam_id, rtsp_url in CAMERAS.items():
        try:
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                status[cam_id] = {
                    'status': 'online',
                    'url': rtsp_url
                }
                cap.release()
            else:
                status[cam_id] = {
                    'status': 'offline', 
                    'url': rtsp_url
                }
        except Exception as e:
            status[cam_id] = {
                'status': 'error',
                'error': str(e)
            }
    return jsonify(status)

@app.route('/advanced_plate_search')
def advanced_plate_search():
    return render_template('advanced_plate_search.html')

@app.route('/unified_plate_search')
def unified_plate_search():
    return render_template('unified_plate_search.html')

# @ai_bp.route('/cameras', methods=['GET'])
# def get_cameras():
#     """Get available cameras"""
#     return jsonify({
#         'available_cameras': list(CAMERAS.keys())
#     })

@socketio.on('leave_room')
def handle_leave_room(data):
    """Leave a camera room"""
    camera_id = data.get('camera_id')
    if camera_id:
        leave_room(camera_id)
        print(f"Left room: {camera_id}")
    
# Basic pages (templates)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/drone_control')
def drone_control():
    return render_template('drone_control.html')

@app.route('/plate_search/<camera_id>')
def plate_search(camera_id):
    return render_template('plate_search.html', camera_id=camera_id)

@app.route('/face_search/<camera_id>')
def face_search(camera_id):
    return render_template('face_search.html', camera_id=camera_id)

# Optional: test endpoint
@socketio.on("connect", namespace="/alerts")
def handle_connect():
    print("Law enforcement dashboard connected to /alerts")

if __name__ == "__main__":
    print("🚀 Flask-SocketIO server running at http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True
                #  ,use_reloader=False
                #  , async_mode="eventlet"
                 )











# from flask import Flask, render_template, Response, request  # Assume you have templates for pages
# from flask_socketio import SocketIO, emit, join_room
# from threading import Thread, Event
# import time
# from camera_streams import get_stream_response  # Your existing
# # from config import CAMERAS, SKIP_FRAMES
# from detectors.plate_anpr import PlateANPR
# import uuid  # For session IDs
# import cv2

# import smtplib
# from email.mime.text import MIMEText
# from config import EMAIL_SERVER, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, CEO_EMAIL, WATCHLIST_PLATES, WATCHLIST_FACES, CAMERA_LOCATIONS, CAMERAS, SKIP_FRAMES
# from detectors.face_detector import FaceDetector
# import os
# from detectors.drone_controller import dispatch_drone

# app = Flask(__name__)
# app.config['TEMPLATES_AUTO_RELOAD'] = True
# socketio = SocketIO(app, cors_allowed_origins="*")  # For frontend JS
# anpr = PlateANPR()  # Global detector
# face_detector = FaceDetector()  # New detector
# active_sessions = {}  # {camera_id: {'thread': Thread, 'stop_event': Event, 'results': []}}

# def send_email(subject, body, to_email=CEO_EMAIL):
#     msg = MIMEText(body)
#     msg['Subject'] = subject
#     msg['From'] = EMAIL_USERNAME
#     msg['To'] = to_email

#     try:
#         with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
#             server.starttls()
#             server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
#             server.sendmail(EMAIL_USERNAME, to_email, msg.as_string())
#         print(f"Email sent: {subject}")
#     except Exception as e:
#         print(f"Email error: {e}")


# @app.route('/drone_dispatch', methods=['POST'])
# def drone_dispatch():
#     data = request.json
#     lat = data.get('lat')
#     lon = data.get('lon')
#     follow = data.get('follow', False)
#     if lat and lon:
#         dispatch_drone(lat, lon, follow)
#         return {'status': 'Drone dispatched'}
#     return {'error': 'Missing coords'}, 400

# # # Add drone stream route
# # @app.route('/drone_stream')
# # def drone_stream():
# #     return Response(generate_video_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/drone_control')
# def drone_control():
#     return render_template('drone_control.html')

# # In your alarm logic (e.g., in face_detector.py or plate_anpr):
# # if match_found:
# #     import requests
# #     requests.post('http://localhost:5000/drone_dispatch', json={'lat': cam_lat, 'lon': cam_lon, 'follow': True})

# # Add this route for plate search page
# @app.route('/plate_search/<camera_id>')
# def plate_search(camera_id):
#     if camera_id.lower() not in CAMERAS:
#         return {"error": "Invalid camera ID"}, 404
#     print(f"Rendering plate_search.html for camera_id: {camera_id}")  # Debug
#     return render_template('plate_search.html', camera_id=camera_id)

# # @app.route('/face_search/<camera_id>')
# # def face_search(camera_id):
# #     if camera_id.lower() not in CAMERAS:
# #         return {"error": "Invalid camera ID"}, 404
# #     print(f"Rendering plate_search.html for camera_id: {camera_id}")  # Debug
# #     return render_template('face_search.html', camera_id=camera_id)

# @app.route('/face_search/<camera_id>')
# def render_face_search(camera_id):
#     if camera_id.lower() not in CAMERA_LOCATIONS:
#         return {"error": "Invalid camera ID"}, 404
#     print(f"Rendering face_search.html for camera_id: {camera_id}")
#     return render_template('face_search.html', camera_id=camera_id, camera_locations=CAMERA_LOCATIONS, watchlist_faces=WATCHLIST_FACES)

# @app.route('/watchlist_faces')
# def get_watchlist_faces():
#     from config import WATCHLIST_FACES
#     return {"watchlist_faces": WATCHLIST_FACES}
    
# # Your existing raw stream route (e.g., /stream/<camera_id>)
# @app.route('/stream/<camera_id>')
# def stream(camera_id):
#     return get_stream_response(camera_id) or ("No camera", 404)

# # Trigger plate search
# @app.route('/start_plate_search/<camera_id>', methods=['POST'])
# def start_plate_search(camera_id):
#     print(f"Starting plate search for {camera_id}")  # Debug
#     if camera_id in active_sessions:
#         return {'status': 'already_running'}
#     rtsp_url = CAMERAS.get(camera_id.lower())
#     if not rtsp_url:
#         return {'error': 'invalid_camera'}, 404

#     # Get duration from request BEFORE thread (Flask context-safe)
#     duration = request.json.get('duration', 60)

#     stop_event = Event()
#     results = []
#     session_id = str(uuid.uuid4())

#     def process_stream(rtsp_url, duration):  # Pass duration as arg
#         print(f"Connecting to RTSP: {rtsp_url}")  # Debug
#         cap = cv2.VideoCapture(rtsp_url)
#         frame_num = 0
#         start_time = time.time()

#         while not stop_event.is_set() and (time.time() - start_time < duration):
#             ret, frame = cap.read()
#             if not ret:
#                 print(f"Failed to grab frame from {rtsp_url}")  # Debug
#                 cap.release()
#                 cap = cv2.VideoCapture(rtsp_url)  # Reinitialize
#                 time.sleep(0.1)
#                 continue
#             frame_num += 1
#             if frame_num % SKIP_FRAMES != 0:
#                 continue
#             plates = anpr.detect_and_read(frame, frame_num)
#             if plates:
#                 results.extend(plates)
#                 print(f"Detected plates: {plates}")  # Debug
#                 socketio.emit('plate_update', {'camera_id': camera_id, 'plates': plates}, room=camera_id)

#                 # Email alerts
#                 for plate in plates:
#                     plate_text = plate['text']
#                     body = f"Plate detected: {plate_text} (Conf: {plate['conf']:.2f})\nCamera: {camera_id}\nTime: {time.ctime()}"
#                     if any(watch in plate_text.upper() for watch in WATCHLIST_PLATES):
#                         send_email("Welcome Alert", f"Welcome! Your plate {plate_text} was detected at {camera_id}.", CEO_EMAIL)
#                     else:
#                         send_email("Plate Detection Alert", body, CEO_EMAIL)  # General alert
#         cap.release()
#         socketio.emit('search_complete', {'camera_id': camera_id})

#     thread = Thread(target=process_stream, args=(rtsp_url, duration))  # Pass args
#     thread.start()
#     active_sessions[camera_id] = {'thread': thread, 'stop_event': stop_event, 'results': results, 'session_id': session_id}
#     return {'status': 'started', 'session_id': session_id}

# @app.route('/stop_plate_search/<camera_id>', methods=['POST'])
# def stop_plate_search(camera_id):
#     if camera_id in active_sessions:
#         active_sessions[camera_id]['stop_event'].set()
#         active_sessions[camera_id]['thread'].join(timeout=5)
#         del active_sessions[camera_id]
#         return {'status': 'stopped'}
#     return {'error': 'not_running'}, 404

# # @app.route('/plate_search/<camera_id>')
# # def plate_search(camera_id):
# #     return render_template('plate_search.html', camera_id=camera_id)

# # WS handlers
# @socketio.on('connect_plate_ws')
# def handle_connect(data):
#     try:
#         camera_id = data['camera_id']
#         print(f"WebSocket connected for {camera_id}")
#         join_room(camera_id)
#         emit('connected', {'camera_id': camera_id})
#     except Exception as e:
#         print(f"WS error: {e}")
# # Your other routes (e.g., / for feeds page, /plate_search for search page)


# # Add known face (upload via API)
# @app.route('/add_known_face/<camera_id>', methods=['POST'])
# def add_known_face(camera_id):
#     if 'file' not in request.files or not request.form.get('name'):
#         return {'error': 'Missing file or name'}, 400
#     file = request.files['file']
#     name = request.form['name']
#     age = request.form.get('age', type=int)
#     role = request.form.get('role', 'Unknown')
    
#     temp_path = f"temp_{name}.jpg"
#     file.save(temp_path)
#     try:
#         face_detector.add_known_face(name, age, role, temp_path)
#         os.remove(temp_path)
#         return {'status': 'Face added', 'name': name}
#     except Exception as e:
#         os.remove(temp_path)
#         return {'error': str(e)}, 400

# # Start face search
# @app.route('/start_face_search/<camera_id>', methods=['POST'])
# def start_face_search(camera_id):
#     print(f"Starting face search for {camera_id}")
#     if camera_id in active_sessions:
#         return {'status': 'already_running'}
#     camera_info = CAMERA_LOCATIONS.get(camera_id.lower())
#     if not camera_info:
#         return {'error': 'invalid_camera'}, 404
#     rtsp_url = camera_info['url']
#     location = camera_info['location']

#     duration = request.json.get('duration', 60)
#     stop_event = Event()
#     results = []
#     session_id = str(uuid.uuid4())

#     def process_stream(rtsp_url, duration):
#         print(f"Connecting to RTSP: {rtsp_url}")
#         cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
#         frame_num = 0
#         start_time = time.time()

#         while not stop_event.is_set() and (time.time() - start_time < duration):
#             ret, frame = cap.read()
#             if not ret:
#                 print(f"Failed to grab frame from {rtsp_url}")
#                 time.sleep(0.1)
#                 continue
#             frame_num += 1
#             if frame_num % SKIP_FRAMES != 0:
#                 continue
#             faces = face_detector.detect_faces(frame, frame_num)
#             if faces:
#                 results.extend(faces)
#                 print(f"Detected faces: {faces}")
#                 socketio.emit('face_update', {'camera_id': camera_id, 'faces': faces}, room=camera_id)
#                 for face in faces:
#                     body = f"Face detected: {face['name']} ({face['role']}, {face['age']})\nCamera: {camera_id}\nLocation: {location}\nTime: {time.ctime()}"
#                     if face['name'] in WATCHLIST_FACES:
#                         send_email("Welcome Alert", f"Welcome, {face['name']}! Detected at {location}.", CEO_EMAIL)
#                     else:
#                         send_email("Face Detection Alert", body, CEO_EMAIL)
#         cap.release()
#         socketio.emit('search_complete', {'camera_id': camera_id})

#     thread = Thread(target=process_stream, args=(rtsp_url, duration))
#     thread.start()
#     active_sessions[camera_id] = {'thread': thread, 'stop_event': stop_event, 'results': results, 'session_id': session_id}
#     return {'status': 'started', 'session_id': session_id}

# # Stop face search (same as stop_plate_search)
# @app.route('/stop_face_search/<camera_id>', methods=['POST'])
# def stop_face_search(camera_id):
#     print(f"Stopping face search for {camera_id}")
#     if camera_id in active_sessions:
#         active_sessions[camera_id]['stop_event'].set()
#         active_sessions[camera_id]['thread'].join(timeout=5)
#         del active_sessions[camera_id]
#         return {'status': 'stopped'}
#     return {'error': 'not_running'}, 404

# @socketio.on('connect_face_ws')
# def handle_face_connect(data):
#     camera_id = data['camera_id']
#     print(f"WebSocket connected for face {camera_id}")
#     join_room(camera_id)
#     emit('connected', {'camera_id': camera_id})


# if __name__ == '__main__':
#     socketio.run(app, debug=True, host='0.0.0.0', port=5000)