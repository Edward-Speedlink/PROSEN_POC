# streams.py
import os
import cv2
import numpy as np
import math
from collections import Counter
from dotenv import load_dotenv
from flask import Response
from ultralytics import YOLO

load_dotenv()

# Load all RTSP entries from .env
CAMERAS = {
    key.lower(): value
    for key, value in os.environ.items()
    if value.startswith("rtsp://")
}

# Example keys from your .env: 'nvr1_main', 'room_varenda', etc.
MODEL_PATHS = {
    'plate': 'detectors/models/license_plate_detector.pt',
    'vehicle': 'yolov8n.pt'  # Auto-downloads if missing
}
CONF_THRESHOLD = 0.5
SKIP_FRAMES = 5  # Process every 5th frame for CPU efficiency

model = YOLO(MODEL_PATHS['vehicle'])

def generate_stream(rtsp_url):
    """Yield frames from RTSP stream as MJPEG."""
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)  # Force FFMPEG backend for RTSP
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        _, jpeg = cv2.imencode(".jpg", frame)
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               jpeg.tobytes() + b"\r\n")
    cap.release()

def get_stream_response(camera_id):
    """Return a Flask Response for given camera id."""
    rtsp_url = CAMERAS.get(camera_id.lower())
    if not rtsp_url:
        return None
    return Response(generate_stream(rtsp_url),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

def get_current_detections(rtsp_url):
    """Grab a single frame and run lightweight object detection to count people, vehicles, animals."""
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    ret, frame = cap.read()
    if not ret:
        cap.release()
        return {"people": 0, "vehicles": 0, "animals": 0}
    
    results = model(frame, conf=CONF_THRESHOLD)
    class_counts = Counter()
    for box in results[0].boxes:
        cls = int(box.cls)
        class_name = model.names[cls]
        if class_name == 'person':
            class_counts['people'] += 1
        elif class_name in ['car', 'motorcycle', 'bus', 'truck']:
            class_counts['vehicles'] += 1
        elif class_name in ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe']:
            class_counts['animals'] += 1
    
    cap.release()
    return dict(class_counts)

def generate_multi_stream():
    """Yield a combined MJPEG stream of all cameras in a grid layout."""
    rtsp_urls = list(CAMERAS.values())
    caps = [cv2.VideoCapture(url, cv2.CAP_FFMPEG) for url in rtsp_urls]
    num_cams = len(caps)
    if num_cams == 0:
        return
    
    cols = math.ceil(math.sqrt(num_cams))
    rows = math.ceil(num_cams / cols)
    width, height = 320, 240  # Resize each feed to small dimensions for efficiency
    
    try:
        while True:
            frames = []
            for cap in caps:
                ret, frame = cap.read()
                if ret:
                    frame = cv2.resize(frame, (width, height))
                    frames.append(frame)
                else:
                    blank = np.zeros((height, width, 3), np.uint8)
                    frames.append(blank)
            
            # Pad with blanks if needed
            while len(frames) < rows * cols:
                blank = np.zeros((height, width, 3), np.uint8)
                frames.append(blank)
            
            # Build grid
            row_frames = []
            for r in range(rows):
                row_img = np.hstack(frames[r * cols : (r + 1) * cols])
                row_frames.append(row_img)
            big_frame = np.vstack(row_frames)
            
            _, jpeg = cv2.imencode(".jpg", big_frame)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" +
                   jpeg.tobytes() + b"\r\n")
    finally:
        for cap in caps:
            cap.release()







# import os
# import cv2
# from dotenv import load_dotenv
# from flask import Response
# import numpy as np



# load_dotenv()

# # Load all RTSP entries from .env
# CAMERAS = {
#     key.lower(): value
#     for key, value in os.environ.items()
#     if value.startswith("rtsp://")
# }

# # Example keys from your .env: 'nvr1_main', 'room_varenda', etc.
# MODEL_PATHS = {
#     'plate': 'detectors/models/license_plate_detector.pt',
#     'vehicle': 'yolov8n.pt'  # Auto-downloads if missing
# }
# CONF_THRESHOLD = 0.5
# SKIP_FRAMES = 5  # Process every 5th frame for CPU efficiency


# # def generate_stream(rtsp_url):
# #     """Yield frames from RTSP stream as MJPEG."""
# #     cap = cv2.VideoCapture(rtsp_url)
# #     while True:
# #         ret, frame = cap.read()
# #         if not ret:
# #             break
# #         _, jpeg = cv2.imencode(".jpg", frame)
# #         yield (b"--frame\r\n"
# #                b"Content-Type: image/jpeg\r\n\r\n" +
# #                jpeg.tobytes() + b"\r\n")
# #     cap.release()


# def generate_stream(rtsp_url):
#     """Yield frames from RTSP stream as MJPEG."""
#     cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)  # Force FFMPEG backend for RTSP
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         _, jpeg = cv2.imencode(".jpg", frame)
#         yield (b"--frame\r\n"
#                b"Content-Type: image/jpeg\r\n\r\n" +
#                jpeg.tobytes() + b"\r\n")
#     cap.release()
    
# def get_stream_response(camera_id):
#     """Return a Flask Response for given camera id."""
#     rtsp_url = CAMERAS.get(camera_id.lower())
#     if not rtsp_url:
#         return None
#     return Response(generate_stream(rtsp_url),
#                     mimetype="multipart/x-mixed-replace; boundary=frame")



