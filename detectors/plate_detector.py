import cv2
from ultralytics import YOLO
import easyocr
import numpy as np

from config import CONF_THRESHOLD

class PlateDetector:
    def __init__(self):
        self.model = YOLO("detectors/models/license_plate_detector.pt")  # Load once
        self.reader = easyocr.Reader(['en'])  # 'en' for English plates; add langs as needed

    def detect_plates(self, frame, skip_frames=5):
        # Preprocess: Resize for speed, grayscale
        frame_resized = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
        # Optional: Blur/equalize for better detection

        # Detect boxes (YOLO)
        results = self.model(gray)  # Returns boxes, confidences, classes
        plates = []
        for result in results:
            for box in result.boxes:
                if box.conf > CONF_THRESHOLD and box.cls == 0:  # Assume class 0 = plate
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    crop = gray[y1:y2, x1:x2]
                    # OCR
                    ocr_result = self.reader.readtext(crop, detail=0)
                    plate_text = ocr_result[0] if ocr_result else "Unknown"
                    plates.append({
                        "text": plate_text,
                        "conf": float(box.conf),
                        "box": [x1, y1, x2, y2]  # Scaled back if needed
                    })
        return plates