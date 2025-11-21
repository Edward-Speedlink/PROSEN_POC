import sys
import os

# Add the cloned 'sort' directory to sys.path (relative to this file)
sort_path = os.path.join(os.path.dirname(__file__), 'sort')
if os.path.exists(sort_path):
    sys.path.append(sort_path)
else:
    raise ImportError("SORT directory not found at detectors/sort/. Ensure it's cloned correctly.")

# Now import Sort
from sort import Sort

import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO
import easyocr
from config import CONF_THRESHOLD, SKIP_FRAMES

class PlateANPR:
    def __init__(self):
        # Load models (once, CPU)
        self.vehicle_model = YOLO('yolov8n.pt')  # Vehicles for ROI; auto-downloads if missing
        self.plate_model = YOLO('detectors/models/license_plate_detector.pt')  # Plates
        self.ocr_reader = easyocr.Reader(['en'], gpu=False)  # Explicit CPU; add langs as needed
        self.mot_tracker = Sort()  # SORT for tracking vehicles/plates

    def preprocess_frame(self, frame):
        # Resize + optional enhancements
        frame_resized = cv2.resize(frame, (640, 480))
        return frame_resized, frame.shape[:2]  # Resized and original dims

# Temporary test without vehicles - 

    def detect_and_read(self, frame, frame_num):
        resized, orig_dims = self.preprocess_frame(frame)
        plates = []
        orig_h, orig_w = orig_dims

        # Skip vehicle detection, go straight to plate detection on full frame
        plate_results = self.plate_model(resized, conf=CONF_THRESHOLD)[0]
        for pbox in plate_results.boxes:
            px1, py1, px2, py2 = map(float, pbox.xyxy[0].tolist())
            pconf = float(pbox.conf[0].item())

            if pconf < 0.7:  # Filter low-conf
                continue

            # Scale box to original frame size for frontend
            scale_x, scale_y = orig_w / 640, orig_h / 480
            orig_box = [
                int(px1 * scale_x), int(py1 * scale_y),
                int(px2 * scale_x), int(py2 * scale_y)
            ]

            # Crop for OCR
            plate_crop = resized[int(py1):int(py2), int(px1):int(px2)]
            if plate_crop.size == 0:
                continue

            # OCR
            ocr_results = self.ocr_reader.readtext(plate_crop, detail=0, paragraph=False)
            plate_text = ' '.join(ocr_results).upper().replace(' ', '') if ocr_results else 'UNKNOWN'

            # Basic tracking with SORT (optional, for moving plates)
            detections = [[px1, py1, px2, py2, pconf]]  # Format for SORT
            tracked_objects = self.mot_tracker.update(np.array(detections)) if detections else []
            track_id = int(tracked_objects[0][4]) if tracked_objects.size > 0 else 0

            plates.append({
                'frame': frame_num,
                'text': plate_text,
                'conf': pconf,
                'box': orig_box,
                'track_id': track_id
            })

        if plates:
            print(f"Frame {frame_num}: Detected {len(plates)} plates: {plates}")  # Debug
        return plates
