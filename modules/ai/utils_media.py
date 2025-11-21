# modules/ai/utils_media.py
import cv2, time, os
from datetime import datetime

SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)

def save_frame_as_image(frame, prefix="event"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.jpg"
    path = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(path, frame)
    return path

def save_video_clip(rtsp_url, seconds=5, prefix="event_clip"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.mp4"
    path = os.path.join(SAVE_DIR, filename)

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        return None

    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 20
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))

    start = time.time()
    while (time.time() - start) < seconds:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
    
    cap.release()
    out.release()
    return path
