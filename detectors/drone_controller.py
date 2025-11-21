# # # this handles connecting and sending commands to the drone
# from dronekit import connect, VehicleMode, LocationGlobalRelative
# import time
# import cv2
# from config import DRONE_MAVLINK_CONNECTION, DRONE_HOME_LAT, DRONE_HOME_LON, DRONE_HOME_ALT, DRONE_MIN_BATTERY, DRONE_CONNECTION_RETRIES, DRONE_VIDEO_UDP
# from threading import Thread

# video_thread = None
# video_cap = None

# def start_video_stream():
#     global video_cap, video_thread
#     if video_thread is not None:
#         return
#     video_cap = cv2.VideoCapture(DRONE_VIDEO_UDP)
#     def run_stream():
#         while True:
#             if video_cap.isOpened():
#                 time.sleep(0.1)  # Keep alive
#             else:
#                 print("Reopening video stream...")
#                 video_cap.open(DRONE_VIDEO_UDP)
#     video_thread = Thread(target=run_stream, daemon=True)
#     video_thread.start()
#     print("Drone video stream started")

# def generate_video_frames():
#     global video_cap
#     if video_cap is None:
#         yield b''
#         return
#     while True:
#         ret, frame = video_cap.read()
#         if ret:
#             ret, jpeg = cv2.imencode('.jpg', frame)
#             if ret:
#                 yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
#         else:
#             time.sleep(0.1)  # Retry on fail

# def connect_drone():
#     for attempt in range(DRONE_CONNECTION_RETRIES):
#         try:
#             print(f"Connecting to drone (attempt {attempt+1})...")
#             vehicle = connect(DRONE_MAVLINK_CONNECTION, wait_ready=True, timeout=60)
#             print("Connected!")
#             return vehicle
#         except Exception as e:
#             print(f"Connection failed: {e}. Retrying...")
#             time.sleep(5)
#     raise Exception("Failed to connect after retries")

# def arm_and_takeoff(vehicle, target_altitude=10):
#     if vehicle.battery.level < DRONE_MIN_BATTERY:
#         raise Exception(f"Battery low: {vehicle.battery.level}% < {DRONE_MIN_BATTERY}%")
#     while not vehicle.is_armable:
#         time.sleep(1)
#     vehicle.mode = VehicleMode("GUIDED")
#     vehicle.armed = True
#     while not vehicle.armed:
#         time.sleep(1)
#     vehicle.simple_takeoff(target_altitude)
#     while vehicle.location.global_relative_frame.alt < target_altitude * 0.95:
#         time.sleep(1)
#     print("Takeoff complete")

# def fly_to_location(vehicle, lat, lon, alt=10):
#     target = LocationGlobalRelative(lat, lon, alt)
#     vehicle.simple_goto(target)
#     print(f"Flying to {lat}, {lon} at {alt}m")

# def follow_target(vehicle):
#     # Trigger ActiveTrack (adapt from RosettaDrone/MAVLink docs; this is placeholder)
#     # vehicle.send_mavlink(...) for custom command if needed
#     print("Starting target follow mode")
#     time.sleep(60)  # Follow for 1 min; monitor in loop
#     # Add monitoring: while following, check vehicle.system_status

# def return_and_land(vehicle):
#     home = LocationGlobalRelative(DRONE_HOME_LAT, DRONE_HOME_LON, DRONE_HOME_ALT)
#     vehicle.simple_goto(home)
#     time.sleep(30)  # Adjust based on distance
#     vehicle.mode = VehicleMode("LAND")
#     while vehicle.mode.name != 'LAND':
#         time.sleep(1)
#     print("Landing")

# def dispatch_drone(lat, lon, follow=False):
#     start_video_stream()  # Start relay if not running
#     vehicle = None
#     try:
#         vehicle = connect_drone()
#         arm_and_takeoff(vehicle)
#         fly_to_location(vehicle, lat, lon)
#         if follow:
#             follow_target(vehicle)
#         return_and_land(vehicle)
#     except Exception as e:
#         print(f"Dispatch error: {e}")
#         if vehicle:
#             vehicle.mode = VehicleMode("RTL")  # Return to launch on error
#             vehicle.armed = False  # Disarm
#     finally:
#         if vehicle:
#             vehicle.close()

            
