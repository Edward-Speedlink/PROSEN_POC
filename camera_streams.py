# import os
# import cv2
# from dotenv import load_dotenv
# from flask import Response

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



