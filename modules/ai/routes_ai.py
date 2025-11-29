import datetime
from flask import Blueprint, request
from flask_socketio import emit, join_room
from threading import Thread, Event
import time, uuid, cv2, os
from config import (
    WATCHLIST_PLATES, WATCHLIST_FACES, CAMERAS, CAMERA_LOCATIONS,
    CEO_EMAIL, SKIP_FRAMES, EMAIL_PASSWORD, EMAIL_USERNAME
)
from detectors.plate_anpr import PlateANPR
from detectors.face_detector import FaceDetector
from .utils_email import send_email
from flask import current_app as app
from .utils_media import save_frame_as_image, save_video_clip
import threading
from threading import Thread, Event
import time, uuid, cv2, os, base64, io
import numpy as np
from flask import jsonify, Blueprint, current_app 
from detectors.object_detector import ObjectDetector
from datetime import datetime
from difflib import SequenceMatcher
from collections import Counter
from ultralytics import YOLO
import cv2
from utils.notifications import notification_service


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()



ai_bp = Blueprint('ai', __name__)
# socketio = app.extensions.get('socketio')

def get_socketio():
    return current_app.extensions.get('socketio')


anpr = PlateANPR()
face_detector = FaceDetector()
active_sessions = {}
object_detector = ObjectDetector()

# ---- Plate search ----
# @ai_bp.route('/start_plate_search/<camera_id>', methods=['POST'])
# def start_plate_search(camera_id):



@ai_bp.route('/detect_objects', methods=['POST'])
def detect_objects():
    data = request.json
    camera_ids = data.get('camera_ids', [])
    results = {}
    socketio = get_socketio()

    for cam_id in camera_ids:
        rtsp_url = CAMERAS.get(cam_id.lower())
        if not rtsp_url:
            results[cam_id] = {"error": "not found"}
            continue

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            results[cam_id] = {"people": 0, "vehicles": 0}
            continue

        detections = anpr(frame, conf=0.4, verbose=False)[0]
        counts = Counter()

        for box in detections.boxes:
            cls_name = anpr.names[int(box.cls)]
            if cls_name == "person":
                counts['people'] += 1
            elif cls_name in ["car", "truck", "bus", "motorcycle"]:
                counts['vehicles'] += 1

        results[cam_id] = {
            "people": counts['people'],
            "vehicles": counts['vehicles'],
            "total": counts['people'] + counts['vehicles']
        }

        # Emit live update
        socketio.emit('object_update', {
            'camera_id': cam_id,
            'people': counts['people'],
            'vehicles': counts['vehicles'],
            'total': counts['people'] + counts['vehicles']
        }, room=cam_id)

    return jsonify(results)

active_analysis = {}  # cam_id → stop_event

@ai_bp.route('/start_live_analysis', methods=['POST'])
def start_live_analysis():
    data = request.json
    camera_ids = data.get('camera_ids', [])
    interval = data.get('interval', 5)  # seconds

    for cam_id in camera_ids:
        if cam_id.lower() in active_analysis:
            continue

        stop_event = threading.Event()

        def analyze_loop():
            while not stop_event.is_set():
                # Reuse same logic as detect_objects but for one cam
                rtsp_url = CAMERAS.get(cam_id.lower())
                if not rtsp_url:
                    break

                socketio = get_socketio()

                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    time.sleep(1)
                    continue

                results = anpr(frame, conf=0.4, verbose=False)[0]
                counts = Counter()
                for box in results.boxes:
                    cls = anpr.names[int(box.cls)]
                    if cls == "person": counts['people'] += 1
                    if cls in ["car", "truck", "bus", "motorcycle"]: counts['vehicles'] += 1

                socketio.emit('object_update', {
                    'camera_id': cam_id,
                    'people': counts['people'],
                    'vehicles': counts['vehicles'],
                    'total': counts['people'] + counts['vehicles'],
                    'timestamp': time.time()
                })

                time.sleep(interval)

        thread = threading.Thread(target=analyze_loop, daemon=True)
        thread.start()
        active_analysis[cam_id.lower()] = stop_event

    return {"status": "started", "cameras": camera_ids}


@ai_bp.route('/stop_live_analysis', methods=['POST'])
def stop_live_analysis():
    data = request.json or {}
    camera_ids = data.get('camera_ids', list(active_analysis.keys()))

    stopped = []
    for cam_id in camera_ids:
        cam_id = cam_id.lower()
        if cam_id in active_analysis:
            active_analysis[cam_id].set()
            del active_analysis[cam_id]
            stopped.append(cam_id)

    return {"stopped": stopped}


@ai_bp.route('/cameras', methods=['GET'])
def get_cameras():
    """Get available cameras"""
    return jsonify({
        'available_cameras': list(CAMERAS.keys())
    })

    
@ai_bp.route('/active_sessions', methods=['GET'])
def get_active_sessions():
    """Get currently active search sessions"""
    sessions = {}
    for cam_id, session_data in active_sessions.items():
        sessions[cam_id] = {
            'session_id': session_data['session_id'],
            'results_count': len(session_data['results'])
        }
    return jsonify({'active_sessions': sessions})

@ai_bp.route('/start_plate_search', methods=['POST'])
def start_plate_search():
    data = request.json
    camera_ids = data.get('camera_ids', [])
    duration = data.get('duration', 60) #300
    notification_methods = data.get('notification_methods', ['email', 'whatsapp'])  # New parameter

    if not isinstance(camera_ids, list) or not camera_ids:
        return {'error': 'Missing or invalid camera_ids list'}, 400

    started_sessions = {}
    errors = {}

    socketio = get_socketio()

    for camera_id in camera_ids:
        cam_id = camera_id.lower()
        if cam_id in active_sessions:
            errors[camera_id] = 'already_running'
            continue

        rtsp_url = CAMERAS.get(cam_id)
        if not rtsp_url:
            errors[camera_id] = f'Camera "{camera_id}" not found'
            continue

        stop_event = Event()
        results = []
        session_id = str(uuid.uuid4())

        def process_stream(rtsp_url=rtsp_url, cam_id=cam_id, methods=notification_methods):  # Capture vars correctly
            cap = cv2.VideoCapture(rtsp_url)
            frame_num = 0
            start_time = time.time()

            while not stop_event.is_set() and (time.time() - start_time < duration):
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                frame_num += 1
                if frame_num % SKIP_FRAMES != 0:
                    continue

                plates = anpr.detect_and_read(frame, frame_num)
                if plates:
                    # Emit all plates (for drawing)
                    socketio.emit('plate_update', {
                        'camera_id': cam_id,
                        'plates': plates,
                        'watchlist_hit': False
                    }, room=cam_id)

                    for plate in plates:
                        plate_text = plate['text'].upper().replace('?', '')
                        ocr_clean = ''.join(c for c in plate_text if c.isalnum())

                        matched = None
                        for watch in WATCHLIST_PLATES:
                            watch_clean = ''.join(c for c in watch.upper().replace('?', '') if c.isalnum())
                            if len(ocr_clean) >= 5 and similar(ocr_clean, watch_clean) > 0.78:
                                matched = watch
                                break

                        img_path = save_frame_as_image(frame, prefix=f"{cam_id}_{plate_text}")

                        if matched:
                            print(f"WATCHLIST HIT: {plate_text} ≈ {matched}")

                            # Save clip
                            threading.Thread(
                                target=save_video_clip,
                                args=(rtsp_url, 5, f"{cam_id}_{matched}"),
                                daemon=True
                            ).start()

                            # Send nice HTML email
                            subject = f"WATCHLIST MATCH: {matched}"
                            email_body = f"""
                            <h2>Watchlist Plate Detected!</h2>
                            <p><strong>Detected:</strong> {plate_text} → <strong>{matched}</strong></p>
                            <p><strong>Camera:</strong> {cam_id}</p>
                            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                            <p><strong>Confidence:</strong> {plate['conf']:.2%}</p>
                            <hr>
                            <p>See attached snapshot. 5-second clip saved.</p>
                            """

                            whatsapp_body = f"Plate: {plate_text} ≈ {matched}\nCamera: {cam_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nConfidence: {plate['conf']:.2%}"

                            notification_service.send_security_alert(
                                subject=subject,
                                body=whatsapp_body,
                                alert_type="PLATE",
                                attachments=[img_path],
                                html=True,
                                methods=methods
                            )
                            # send_email(subject, email_body, CEO_EMAIL, attachments=[img_path], html=True)

                            # Emit with match info
                            socketio.emit('plate_update', {
                                'camera_id': cam_id,
                                'plates': plates,
                                'watchlist_hit': True,
                                'matched_plate': matched,
                                'snapshot': f"/static/detections/{os.path.basename(img_path)}"
                            }, room=cam_id)

            cap.release()
            socketio.emit('search_complete', {'camera_id': cam_id})

        # Start thread
        thread = threading.Thread(target=process_stream, daemon=True)
        thread.start()

        active_sessions[cam_id] = {
            'thread': thread,
            'stop_event': stop_event,
            'results': results,
            'session_id': session_id
        }
        started_sessions[camera_id] = {'status': 'started', 'session_id': session_id}

    resp = {'started': started_sessions}
    if errors:
        resp['errors'] = errors
    return resp, 200


@ai_bp.route('/stop_plate_search', methods=['POST'])
def stop_plate_search():
    data = request.json or {}
    camera_ids = data.get('camera_ids', list(active_sessions.keys()))
    
    stopped = {}
    for cam_id in camera_ids:
        cam_id = cam_id.lower()
        if cam_id in active_sessions:
            active_sessions[cam_id]['stop_event'].set()
            stopped[cam_id] = "stopped"
            del active_sessions[cam_id]
    
    return {"stopped": stopped}, 200
    
# @ai_bp.route('/stop_plate_search/<camera_id>', methods=['POST'])
# def stop_plate_search(camera_id):
#     if camera_id in active_sessions:
#         active_sessions[camera_id]['stop_event'].set()
#         active_sessions[camera_id]['thread'].join(timeout=5)
#         del active_sessions[camera_id]
#         return {'status': 'stopped'}
#     return {'error': 'not_running'}, 404

# ---- Face search ----
@ai_bp.route('/start_face_search/<camera_id>', methods=['POST'])
def start_face_search(camera_id):
    if camera_id in active_sessions:
        return {'status': 'already_running'}

    camera_info = CAMERA_LOCATIONS.get(camera_id.lower())
    if not camera_info:
        return {'error': 'invalid_camera'}, 404

    rtsp_url = camera_info['url']
    location = camera_info['location']
    duration = request.json.get('duration', 60)
    notification_methods = request.json.get('notification_methods', ['email', 'whatsapp'])  # New parameter

    stop_event = Event()
    results = []
    session_id = str(uuid.uuid4())
    socketio = get_socketio()

    def process_stream(rtsp_url, duration, methods):
        cap = cv2.VideoCapture(rtsp_url)
        frame_num = 0
        start_time = time.time()

        while not stop_event.is_set() and (time.time() - start_time < duration):
            ret, frame = cap.read()

            if not ret:
                print(f"[{camera_id}] Frame read failed.")
            else:
                print(f"[{camera_id}] Frame {frame_num} captured successfully.")

            if not ret:
                time.sleep(0.1)
                continue

            frame_num += 1
            if frame_num % SKIP_FRAMES != 0:
                continue

            faces = face_detector.detect_faces(frame, frame_num)
            print(f"[{camera_id}] Detected faces: {faces}")

            for face in faces:
                x1, y1, x2, y2 = face['box']
                name = face['name']
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{name}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


            for face in faces:
                results.append(face)
                socketio.emit('face_update', {'camera_id': camera_id, 'faces': [face]}, room=camera_id)
                print(f"[{camera_id}] Emitted face_update event for {face['name']}")


                # --- Evidence & Alert for Known Faces ---
                if face['name'] != "Unknown":
                    img_path = save_frame_as_image(frame, prefix=f"{camera_id}_{face['name']}")
                    threading.Thread(target=save_video_clip, args=(rtsp_url, 5, f"{camera_id}_{face['name']}")).start()

                    subject = f"{face['name']} detected at {location}"
                    # body = f"{face['name']} ({face.get('role', 'N/A')}) detected at {location}."
                    email_body = f"{face['name']} ({face.get('role', 'N/A')}) detected at {location}."
                    whatsapp_body = f"Person: {face['name']}\nRole: {face.get('role', 'N/A')}\nLocation: {location}\nCamera: {camera_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    notification_service.send_security_alert(
                        subject=subject,
                        body=whatsapp_body,
                        alert_type="FACE",
                        attachments=[img_path],
                        methods=methods
                    )
                    # send_email(subject, body, CEO_EMAIL, attachments=[img_path])

                    socketio.emit("face_match", {
                        "id": str(uuid.uuid4()),
                        "type": "FACE_MATCH",
                        "name": face['name'],
                        "role": face.get("role", "N/A"),
                        "camera": location,
                        "camera_id": camera_id,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "image": img_path,
                        "confidence": face.get("confidence", 0.0),
                    })


        cap.release()
        socketio.emit('search_complete', {'camera_id': camera_id})

    thread = Thread(target=process_stream, args=(rtsp_url, duration, notification_methods))
    thread.start()
    active_sessions[camera_id] = {
        'thread': thread,
        'stop_event': stop_event,
        'results': results,
        'session_id': session_id
    }

    return {'status': 'started', 'session_id': session_id}



@ai_bp.route('/stop_face_search/<camera_id>', methods=['POST'])
def stop_face_search(camera_id):
    if camera_id in active_sessions:
        active_sessions[camera_id]['stop_event'].set()
        active_sessions[camera_id]['thread'].join(timeout=5)
        del active_sessions[camera_id]
        return {'status': 'stopped'}
    return {'error': 'not_running'}, 404


@ai_bp.route('/search_plate/<plate_text>', methods=['POST'])
def search_plate(plate_text):
    camera_list = request.json.get('cameras', [])
    duration = request.json.get('duration', 60)
    notification_methods = request.json.get('notification_methods', ['email', 'whatsapp'])  # New parameter
    normalized_plate = plate_text.upper().replace(" ", "")
    session_id = str(uuid.uuid4())
    socketio = get_socketio()

    for camera_id in camera_list:
        if camera_id in active_sessions:
            continue

        rtsp_url = CAMERAS.get(camera_id.lower())
        if not rtsp_url:
            continue

        stop_event = Event()
        results = []

        def process_stream(rtsp_url, duration, camera_id, methods):
            cap = cv2.VideoCapture(rtsp_url)
            frame_num = 0
            start_time = time.time()

            while not stop_event.is_set() and (time.time() - start_time < duration):
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                frame_num += 1
                if frame_num % SKIP_FRAMES != 0:
                    continue

                plates = anpr.detect_and_read(frame, frame_num)
                for p in plates:
                    if normalized_plate in p['text']:
                        results.append(p)
                        socketio.emit('plate_match', {
                            'camera_id': camera_id,
                            'plate': p,
                            'session_id': session_id
                        }, room=camera_id)

                        # --- Save Evidence ---
                        image_path = save_frame_as_image(frame, prefix=f"{camera_id}_{p['text']}")
                        threading.Thread(target=save_video_clip, args=(rtsp_url, 5, f"{camera_id}_{p['text']}")).start()

                        # --- Send Email Alert ---
                        subject = f"Plate {p['text']} Detected at {camera_id}"
                        email_body = f"Plate {p['text']} was recognized at camera {camera_id}. See attached snapshot."
                        whatsapp_body = f"Plate: {p['text']}\nCamera: {camera_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nConfidence: {p.get('conf', 0.0):.2%}"

                        notification_service.send_security_alert(
                            subject=subject,
                            body=whatsapp_body,
                            alert_type="PLATE",
                            attachments=[image_path],
                            methods=methods
                        )
                        # body = f"Plate {p['text']} was recognized at camera {camera_id}. See attached snapshot."
                        # send_email(subject, body, CEO_EMAIL, attachments=[image_path])

            cap.release()
            socketio.emit('search_complete', {'camera_id': camera_id, 'session_id': session_id})

        thread = Thread(target=process_stream, args=(rtsp_url, duration, camera_id, notification_methods))
        thread.start()
        active_sessions[camera_id] = {
            'thread': thread,
            'stop_event': stop_event,
            'results': results,
            'session_id': session_id
        }

    return {'status': 'started', 'session_id': session_id, 'cameras': camera_list}



# New endpoint: POST /search_face_probe
@ai_bp.route('/search_face_probe', methods=['POST'])
def search_face_probe():
    """
    Accepts:
      - 'file' multipart form (image) OR 'image_b64' in JSON
      - JSON body / form field 'cameras': ["cam1","cam2"]
      - 'duration' optional seconds (default 60)
      - 'match_threshold' optional (float, default 0.6)
    Emits:
      - 'face_probe_match' with payload {camera_id, face, session_id}
      - 'search_complete' when each camera completes
    """
    # 1) get probe image
    probe_frame = None
    socketio = get_socketio()
    if 'file' in request.files:
        f = request.files['file']
        arr = np.frombuffer(f.read(), np.uint8)
        probe_frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    else:
        data = request.get_json(silent=True) or {}
        b64 = data.get('image_b64')
        if b64:
            try:
                b = base64.b64decode(b64)
                arr = np.frombuffer(b, np.uint8)
                probe_frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            except Exception as e:
                return jsonify({"error": f"invalid base64 image: {e}"}), 400

    if probe_frame is None:
        return jsonify({"error": "No probe image provided (upload 'file' or JSON 'image_b64')."}), 400

    # 2) compute probe embedding
    try:
        probe_emb = face_detector.get_embedding_from_frame(probe_frame)
        if probe_emb is None:
            return jsonify({"error": "No face found in probe image."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # 3) config
    payload = request.get_json(silent=True) or {}
    # support form data for cameras too
    cameras = payload.get('cameras') or request.form.getlist('cameras') or []
    if isinstance(cameras, str):
        # single comma separated
        cameras = [c.strip() for c in cameras.split(',') if c.strip()]
    if not cameras:
        return jsonify({"error": "No cameras provided."}), 400

    duration = int(payload.get('duration', request.form.get('duration', 60)))
    match_threshold = float(payload.get('match_threshold', 0.6))

    session_id = str(uuid.uuid4())

    # For each camera, start a thread that reads frames and compares embeddings
    for camera_id in cameras:
        cam_key = camera_id.lower()
        if cam_key in active_sessions:
            # skip already running camera or optionally add session list
            continue

        rtsp_url = CAMERAS.get(cam_key) or (CAMERA_LOCATIONS.get(cam_key) or {}).get('url')
        if not rtsp_url:
            # skip invalid camera
            continue

        stop_event = Event()
        results = []

        def process_camera_search(rtsp, cam_id, probe_embedding, duration_seconds, threshold, stop_event_local):
            cap = cv2.VideoCapture(rtsp)
            if not cap.isOpened():
                socketio.emit('search_error', {'camera_id': cam_id, 'error': 'stream_unavailable'}, room=cam_id)
                return

            frame_num = 0
            start_time = time.time()
            while not stop_event_local.is_set() and (time.time() - start_time < duration_seconds):
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                frame_num += 1
                if frame_num % SKIP_FRAMES != 0:
                    continue

                # Get embedding of the face(s) in this frame
                emb = face_detector.get_embedding_from_frame(frame)
                if emb is None:
                    continue

                # compare distance
                dist = float(np.linalg.norm(probe_embedding - emb))
                if dist <= threshold:
                    # We have a match — build metadata
                    match_meta = {
                        'camera_id': cam_id,
                        'distance': dist,
                        'frame': frame_num,
                        'timestamp': time.time()
                    }

                    # Try to match to known DB (optional)
                    known_hit = face_detector.match_embedding(emb, threshold=threshold)
                    if known_hit:
                        match_meta.update({
                            'name': known_hit['name'],
                            'age': known_hit.get('age'),
                            'role': known_hit.get('role'),
                            'known_dist': known_hit['dist']
                        })
                    else:
                        match_meta.update({'name': 'ProbeMatch', 'age': None, 'role': None})

                    results.append(match_meta)

                    # Draw box + label (we can reuse detect_faces to get bbox, but simple approach: emit frame as image snapshot)
                    image_path = save_frame_as_image(frame, prefix=f"{cam_id}_face_{int(time.time())}")
                    # Save 5s clip async so we don't block loop
                    Thread(target=save_video_clip, args=(rtsp, 5, f"{cam_id}_face_{int(time.time())}"), daemon=True).start()

                    # Send email with attachment (non-blocking)
                    subject = f"Face match on {cam_id}"
                    body = f"Face probe matched on camera {cam_id}. distance={dist:.3f}"
                    Thread(target=send_email, args=(subject, body, CEO_EMAIL, [image_path]), daemon=True).start()

                    # emit websocket match event to frontend (room per camera)
                    socketio.emit('face_probe_match', {'camera_id': cam_id, 'match': match_meta, 'session_id': session_id}, room=cam_id)

                    # Optionally stop this camera after first match, or keep scanning for more matches. Here we stop this camera:
                    stop_event_local.set()
                    break

            cap.release()
            socketio.emit('search_complete', {'camera_id': cam_id, 'session_id': session_id}, room=cam_id)

        thread = Thread(target=process_camera_search, args=(rtsp_url, camera_id, probe_emb, duration, match_threshold, stop_event))
        thread.daemon = True
        thread.start()

        active_sessions[cam_key] = {'thread': thread, 'stop_event': stop_event, 'results': results, 'session_id': session_id}

    return jsonify({'status': 'started', 'session_id': session_id, 'cameras': cameras})

@ai_bp.route('/add_known_face/<camera_id>', methods=['POST'])
def add_known_face(camera_id):
    """
    Allows user to upload an image and register it as a known face.
    Expects:
        - multipart/form-data with 'file' (image)
        - optional JSON fields: name, role, department, etc.
    """
    # 1. Check if file provided
    if 'file' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['file']
    name = request.form.get('name', 'Unknown')
    # role = request.form.get('role', '')
    # department = request.form.get('department', '')

    # 2. Decode image
    arr = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({'error': 'Invalid image format'}), 400

    # 3. Register directly using the image
    success = face_detector.register_known_face(
        name=name,
        # age=None,  # Optional, depending on your method signature
        # role=role,
        image=frame
    )

    if not success:
        return jsonify({'error': 'No face detected in the uploaded image'}), 400

    # Optionally store extra metadata (e.g., department, camera_id)
    # e.g., you can add this to your face database if needed.

    return jsonify({'status': 'success', 'message': f'{name} added to known faces'}), 200

@ai_bp.route('/start_object_detection/<camera_id>', methods=['POST'])
def start_object_detection(camera_id):
    if camera_id in active_sessions:
        return {'status': 'already_running'}, 400

    rtsp_url = CAMERAS.get(camera_id.lower())
    if not rtsp_url:
        return {'error': 'invalid_camera'}, 404

    duration = request.json.get('duration', 10)  # short default
    stop_event = Event()
    session_id = str(uuid.uuid4())
    socketio = get_socketio()

    def process_object_detection():
        cap = cv2.VideoCapture(rtsp_url)
        frame_num = 0
        start_time = time.time()

        while not stop_event.is_set() and (time.time() - start_time < duration):
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame_num += 1
            if frame_num % SKIP_FRAMES != 0:
                continue

            objects = object_detector.detect_and_track(frame, frame_num, conf_threshold=0.5)
            if objects:
                socketio.emit('object_detection', {
                    'camera_id': camera_id,
                    'objects': objects
                }, room=camera_id)

        cap.release()
        socketio.emit('object_detection_complete', {
            'camera_id': camera_id,
            'session_id': session_id
        }, room=camera_id)

    thread = Thread(target=process_object_detection)
    thread.start()

    active_sessions[camera_id] = {
        'thread': thread,
        'stop_event': stop_event,
        'session_id': session_id
    }

    return {'status': 'started', 'session_id': session_id}


@ai_bp.route('/stop_object_detection/<camera_id>', methods=['POST'])
def stop_object_detection(camera_id):
    if camera_id not in active_sessions:
        return {'error': 'not_running'}, 404

    active_sessions[camera_id]['stop_event'].set()
    active_sessions[camera_id]['thread'].join(timeout=5)
    del active_sessions[camera_id]
    return {'status': 'stopped'}


@ai_bp.route('/watchlist', methods=['GET', 'POST'])
def watchlist():
    if request.method == 'GET':
        return jsonify(WATCHLIST_PLATES)  # List is fine for GET
    elif request.method == 'POST':
        data = request.get_json()
        plate = data.get('plate', '').strip().upper()
        if plate and plate not in WATCHLIST_PLATES:
            WATCHLIST_PLATES.append(plate)  # Use append for list
        return jsonify(WATCHLIST_PLATES)
    

# ---- WATCHLIST FACES ----
@ai_bp.route('/face_watchlist', methods=['GET', 'POST'])
def face_watchlist():
    if request.method == 'GET':
        return jsonify(list(WATCHLIST_FACES))
    elif request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if name and name not in WATCHLIST_FACES:
            WATCHLIST_FACES.add(name)
        return jsonify(list(WATCHLIST_FACES))


@ai_bp.route('/add_known_face', methods=['POST'])
def add_known_faces():
    if 'file' not in request.files:
        return jsonify({'error': 'No image file'}), 400

    file = request.files['file']
    name = request.form.get('name', 'Unknown').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400

    # Decode image
    arr = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({'error': 'Invalid image'}), 400

    # Register face
    success = face_detector.register_known_face(
        name=name,
        image=frame
    )
    if not success:
        return jsonify({'error': 'No face detected'}), 400

    # Add to watchlist
    WATCHLIST_FACES.add(name)

    return jsonify({'status': 'success', 'name': name})


# @ai_bp.route('/watchlist', methods=['GET', 'POST'])
# def watchlist():
#     if request.method == 'GET':
#         return jsonify(list(WATCHLIST_PLATES))
#     elif request.method == 'POST':
#         data = request.get_json()
#         plate = data.get('plate', '').strip().upper()
#         if plate and plate not in WATCHLIST_PLATES:
#             WATCHLIST_PLATES.add(plate)
#         return jsonify(list(WATCHLIST_PLATES))



# @ai_bp.route('/add_known_face/<camera_id>', methods=['POST'])
# def add_known_face(camera_id):
#     """
#     Allows user to upload an image and register it as a known face.
#     Expects:
#         - multipart/form-data with 'file' (image)
#         - optional JSON fields: name, role, department, etc.
#     """
#     # 1. Check if file provided
#     if 'file' not in request.files:
#         return jsonify({'error': 'No image file provided'}), 400

#     file = request.files['file']
#     name = request.form.get('name', 'Unknown')
#     role = request.form.get('role', '')
#     department = request.form.get('department', '')

#     # 2. Decode image
#     arr = np.frombuffer(file.read(), np.uint8)
#     frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
#     if frame is None:
#         return jsonify({'error': 'Invalid image format'}), 400

#     # 3. Extract face embedding
#     emb = face_detector.get_embedding_from_frame(frame)
#     if emb is None:
#         return jsonify({'error': 'No face found in image'}), 400

#     # 4. Register face
#     face_detector.register_known_face(
#         name=name,
#         embedding=emb,
#         meta={'role': role, 'department': department, 'camera_id': camera_id}
#     )

#     return jsonify({'status': 'success', 'message': f'{name} added to known faces'}), 200