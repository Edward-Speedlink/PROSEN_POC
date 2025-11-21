# detectors/object_detector.py
import cv2
import numpy as np
from ultralytics import YOLO
import os

# Add SORT
sort_path = os.path.join(os.path.dirname(__file__), 'sort')
if os.path.exists(sort_path):
    import sys
    sys.path.append(sort_path)
    from sort import Sort
else:
    raise ImportError("SORT directory not found at detectors/sort/")

# ALL classes we care about
TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    14: "tv",
    # add more if needed
}

class ObjectDetector:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.tracker = Sort()

    def preprocess_frame(self, frame):
        resized = cv2.resize(frame, (640, 480))
        orig_h, orig_w = frame.shape[:2]
        return resized, (orig_h, orig_w)

    def detect_and_track(self, frame, frame_num, conf_threshold=0.4):
        resized, (orig_h, orig_w) = self.preprocess_frame(frame)
        results = self.model(resized, conf=conf_threshold)[0]

        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            if cls_id not in TARGET_CLASSES:
                continue
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())

            scale_x, scale_y = orig_w / 640, orig_h / 480
            orig_box = [int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)]

            detections.append([x1, y1, x2, y2, conf])

        # Track
        tracked = self.tracker.update(np.array(detections)) if detections else np.empty((0, 5))

        objects = []
        for i, track in enumerate(tracked):
            x1, y1, x2, y2, track_id = track
            # Find matching detection to get class
            matched = False
            for det in detections:
                if abs(det[0] - x1) < 10 and abs(det[1] - y1) < 10:
                    cls_id = next((int(b.cls[0].item()) for b in results.boxes if 
                                 abs(float(b.xyxy[0][0]) - det[0]) < 10), 0)
                    cls_name = TARGET_CLASSES.get(cls_id, "unknown")
                    conf = det[4]
                    matched = True
                    break
            if not matched:
                cls_name = "unknown"
                conf = 0.0

            scale_x, scale_y = orig_w / 640, orig_h / 480
            orig_box = [int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)]

            objects.append({
                'frame': frame_num,
                'class': cls_name,
                'conf': round(float(conf), 3),
                'box': orig_box,
                'track_id': int(track_id)
            })

        return objects













# # detectors/object_detector.py
# import cv2
# import numpy as np
# from ultralytics import YOLO
# import os

# # Add SORT
# sort_path = os.path.join(os.path.dirname(__file__), 'sort')
# if os.path.exists(sort_path):
#     import sys
#     sys.path.append(sort_path)
#     from sort import Sort
# else:
#     raise ImportError("SORT directory not found at detectors/sort/")

# # Only detect common objects: person, car, truck, motorcycle, bus, bicycle
# TARGET_CLASSES = {
#     0: "person",
#     2: "car",
#     3: "motorcycle",
#     5: "bus",
#     7: "truck",
#     1: "bicycle",
#     14: "tv",
# }

# class ObjectDetector:
#     def __init__(self):
#         # Load YOLOv8 (auto-download if missing)
#         self.model = YOLO('yolov8n.pt')
#         self.tracker = Sort()

#     def preprocess_frame(self, frame):
#         # Resize to 640x480 for speed
#         resized = cv2.resize(frame, (640, 480))
#         orig_h, orig_w = frame.shape[:2]
#         return resized, (orig_h, orig_w)

#     def detect_and_track(self, frame, frame_num, conf_threshold=0.5):
#         resized, (orig_h, orig_w) = self.preprocess_frame(frame)
#         results = self.model(resized, conf=conf_threshold)[0]

#         detections = []
#         for box in results.boxes:
#             cls_id = int(box.cls[0].item())
#             if cls_id not in TARGET_CLASSES:
#                 continue

#             conf = float(box.conf[0].item())
#             x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())

#             # Scale to original frame size
#             scale_x, scale_y = orig_w / 640, orig_h / 480
#             orig_box = [
#                 int(x1 * scale_x), int(y1 * scale_y),
#                 int(x2 * scale_x), int(y2 * scale_y)
#             ]

#             detections.append([x1, y1, x2, y2, conf])

#         # Track
#         tracked = self.tracker.update(np.array(detections)) if detections else np.empty((0, 5))

#         objects = []
#         for track in tracked:
#             x1, y1, x2, y2, track_id = track
#             cls_name = TARGET_CLASSES.get(int(results.boxes[track[:4].astype(int)[0]].cls[0].item()), "unknown")
#             conf = track[4]

#             scale_x, scale_y = orig_w / 640, orig_h / 480
#             orig_box = [
#                 int(x1 * scale_x), int(y1 * scale_y),
#                 int(x2 * scale_x), int(y2 * scale_y)
#             ]

#             objects.append({
#                 'frame': frame_num,
#                 'class': cls_name,
#                 'conf': round(float(conf), 3),
#                 'box': orig_box,
#                 'track_id': int(track_id)
#             })

#         return objects