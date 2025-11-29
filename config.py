import os
import cv2
from dotenv import load_dotenv
from flask import Response

load_dotenv()

# ===========================
# Database & ORM Config
# ===========================
basedir = os.path.abspath(os.path.dirname(__file__))

# Default: SQLite (development)
SQLALCHEMY_DATABASE_URI = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(basedir, 'prosen.db')}"
)

SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key")


# Add: for drone integrations
DRONE_MAVLINK_CONNECTION = os.getenv('DRONE_MAVLINK_CONNECTION', 'udp:127.0.0.1:14550')
DRONE_HOME_LAT = float(os.getenv('DRONE_HOME_LAT', 0.0))
DRONE_HOME_LON = float(os.getenv('DRONE_HOME_LON', 0.0))
DRONE_HOME_ALT = float(os.getenv('DRONE_HOME_ALT', 0.0))
DRONE_VIDEO_UDP = os.getenv('DRONE_VIDEO_UDP', 'udp://127.0.0.1:5600')
DRONE_MIN_BATTERY = int(os.getenv('DRONE_MIN_BATTERY', 20))
DRONE_CONNECTION_RETRIES = int(os.getenv('DRONE_CONNECTION_RETRIES', 3))

# personal mail credentials from tests
# EMAIL_SERVER = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USERNAME = 'ndiyoedward@gmail.com'
# EMAIL_PASSWORD = 'nhta zxnx xdas bngl' 

EMAIL_SERVER='speedkonnectng.com'
EMAIL_PORT=587
EMAIL_USERNAME='support@speedkonnectng.com'
EMAIL_PASSWORD='tqooklujxewoeooj'
SUPPORT_EMAIL='support@speedkonnectng.com'


 # Use app password for Gmail
CEO_EMAIL =  "daniel@speedlinkng.com" # 'ndiyoedward@icloud.com'  # 'danieluokon@gmail.com' #get mr. dan's mail to put here
CEO_PHONE = "07067281841"
WATCHLIST_PLATES = ['BER631NR', 'SKP343CW', 'KMK404AE']  # CEO's plate(s) for special alerts
# WATCHLIST_FACES = {"John Doe", "Jane Smith", "Mike Ross"}  # set of known names
# config.py
WATCHLIST_FACES = set()  # ← will be populated via API


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

# temp thresshoodl for cardboard test - 
CONF_THRESHOLD = 0.25  # Lower from 0.5

# actual threshold for production
# CONF_THRESHOLD = 0.5

# SKIP_FRAMES = 5  # Process every 5th frame for CPU efficiency
SKIP_FRAMES = 10 # Process every 5th frame for CPU efficiency

# Whatsapp configs
WHATSAPP_PHONE_NUMBER_ID=808921198974802
WHATSAPP_TOKEN="EAAZAErWsgvsIBPlmpJAo1tGuVxXaLDcjyPAuNAlQfZBG1w4U337P1etgINLjLlOCLbtWqttnmsIpTXqn9vjKqAajjoUHjTFpUHZC2M1ex62ZBRPLqXuolfzFIyZClYgmurq4fG4kRYrZBrRey2h3QFJvR7ODlHaIB9QBM7t8jU0wpTi0z8QteN64nX4PPNlVf31gZDZD"
CEO_PHONE = "07067281841"

# Existing email/plate configs...
# WATCHLIST_FACES = ['Mr. Daniel Okon']  # CEO's name for special alerts
# Define location names for each camera
LOCATION_NAMES = {
    'nvr1_main': 'Main NVR Stream',
    'nvr1_sub': 'Sub NVR Stream',
    'room_varenda': 'Room Veranda',
    'nepa_bush_view': 'NEPA Bush View',
    'nepa_street_view': 'NEPA Street View',
    'dining_view': 'Dining View',
    'staff_room': 'Staff Room',
    'inverter_room': 'Office Building, Room 101',
    'camera01': 'Camera 01',
    'parlour_side_back': 'Parlour Side Back',
    'carport': 'Parking Lot',
    'entrance_corridor': 'Entrance Corridor',
    'backyard_watertank': 'Backyard Water Tank',
    'kitchen_side_back': 'Kitchen Side Back',
    'gate_view': 'Gate View',
    'dining': 'Dining Area',
    'backyard_mast': 'Backyard Mast',
    'server_room': 'Server Room'
}

# Populate CAMERA_LOCATIONS dynamically
CAMERA_LOCATIONS = {
    key.lower(): {'url': value, 'location': LOCATION_NAMES.get(key.lower(), 'Unknown Location')}
    for key, value in os.environ.items()
    if value.startswith("rtsp://")
}


def generate_stream(rtsp_url):
    """Yield frames from RTSP stream as MJPEG."""
    cap = cv2.VideoCapture(rtsp_url)
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



