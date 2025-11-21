# using mediapipe for face detection
import mediapipe as mp
import cv2
import numpy as np
import pickle  # For saving known faces
from config import CONF_THRESHOLD
import os


class FaceDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh  # For embeddings
        self.known_faces = {}  # {'name': {'embedding': np.array, 'age': int, 'role': str}}
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.3)
        self.face_mesh = self.mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)
        self.tracked_faces = {}
        self.next_id = 0


    def add_known_face(self, name, age, role, image_path):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load {image_path}")
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Extract embedding (128D vector from face mesh landmarks)
        results = self.face_mesh.process(rgb_image)
        if not results.multi_face_landmarks:
            raise ValueError(f"No face found in {image_path}")
        
        # Simple embedding: average of key landmarks (x,y,z coords)
        landmarks = results.multi_face_landmarks[0].landmark
        embedding = np.array([[lm.x, lm.y, lm.z] for lm in landmarks[:468]]).flatten()  # 1404D, but truncate to 128 for simplicity
        # Normalize embedding
        embedding = embedding / np.linalg.norm(embedding)

        # embedding = embedding[:128]  # Truncate to 128D
        
        self.known_faces[name] = {'embedding': embedding, 'age': age, 'role': role}
        print(f"Added known face: {name}")

    def detect_faces(self, frame, frame_num):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detection_results = self.face_detection.process(rgb_frame)
        faces = []

        # Detection
        detection_results = self.face_detection.process(rgb_frame)
        if detection_results.detections:
            for detection in detection_results.detections:
                bbox = detection.location_data.relative_bounding_box
                h, w = frame.shape[:2]
                x1, y1 = int(bbox.xmin * w), int(bbox.ymin * h)
                x2, y2 = int((bbox.xmin + bbox.width) * w), int((bbox.ymin + bbox.height) * h)
                
                # Extract embedding from mesh
                mesh_results = self.face_mesh.process(rgb_frame)
                if mesh_results.multi_face_landmarks:
                    landmarks = mesh_results.multi_face_landmarks[0].landmark
                    embedding = np.array([[lm.x, lm.y, lm.z] for lm in landmarks[:468]]).flatten()[:128]
                    # Normalize embedding
                    embedding = embedding / np.linalg.norm(embedding)

                    # Match to known
                    name = "Unknown"
                    age, role = None, None
                    best_match = None
                    best_dist = 1e9
                    for known_name, data in self.known_faces.items():
                        dist = np.linalg.norm(embedding - data['embedding'])
                        if dist < best_dist:
                            # best_match = known_name
                            best_dist = dist
                            if dist < 0.6:  # Threshold (tune as needed)
                                name = known_name
                                age, role = data['age'], data['role']
                                best_match = dist
                                # break
                    track_id = self._match_or_create_track(embedding, (x1, y1, x2, y2))
                    
                    faces.append({
                        'id' : track_id,
                        'frame': frame_num,
                        'name': name,
                        'age': age,
                        'role': role,
                        'conf': 1.0 - best_match if best_match else 0.5,  # Simple conf
                        'box': [x1, y1, x2, y2]
                    })

        if faces:
            print(f"Frame {frame_num}: Detected {len(faces)} faces: {faces}")
        return faces

    
    def get_embedding_from_frame(self, frame):
        """
        Accepts a BGR OpenCV frame and returns a 128-d embedding (np.array).
        Reuses same face_mesh pipeline as add_known_face.
        Returns None if no face found.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh_results = self.face_mesh.process(rgb)
        if not mesh_results or not mesh_results.multi_face_landmarks:
            return None
        landmarks = mesh_results.multi_face_landmarks[0].landmark
        embedding = np.array([[lm.x, lm.y, lm.z] for lm in landmarks[:468]]).flatten()[:128]
        # Normalize for stable distance metrics
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def get_embedding_from_image_path(self, image_path):
        """Load image and return embedding or raise if not found."""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load {image_path}")
        emb = self.get_embedding_from_frame(img)
        if emb is None:
            raise ValueError("No face detected in probe image.")
        return emb

    def match_embedding(self, probe_embedding, threshold=0.6):
        """
        Compare probe_embedding to all known faces.
        Returns (name, age, role, distance) for best match; None if no match under threshold.
        """
        best_name = None
        best_dist = float('inf')
        best_meta = None
        for name, data in self.known_faces.items():
            known_emb = data['embedding']
            # ensure known_emb is normalized
            if np.linalg.norm(known_emb) == 0:
                continue
            d = np.linalg.norm(probe_embedding - known_emb)
            if d < best_dist:
                best_dist = d
                best_name = name
                best_meta = data
        if best_name and best_dist <= threshold:
            return {
                'name': best_name,
                'age': best_meta.get('age'),
                'role': best_meta.get('role'),
                'dist': float(best_dist)
            }
        print(f"🔍 Comparing face embedding with {len(self.known_faces)} known faces.")

        return None
    

    def _match_or_create_track(self, embedding, box):
        """Maintains simple short-term tracking of faces based on embedding similarity."""
        best_id, best_dist = None, 1e9
        for tid, data in self.tracked_faces.items():
            dist = np.linalg.norm(embedding - data['embedding'])
            if dist < best_dist:
                best_dist, best_id = dist, tid

        if best_id is not None and best_dist < 0.3:
            # Update tracked position
            self.tracked_faces[best_id] = {'embedding': embedding, 'box': box}
            return best_id
        else:
            # New track
            new_id = self.next_id
            self.next_id += 1
            self.tracked_faces[new_id] = {'embedding': embedding, 'box': box}
            return new_id

    def register_known_face(self, name, image, age=None, role=None, meta=None):
        """
        Add or update a known face profile directly from a BGR OpenCV frame.
        Saves locally and stores embedding in memory.
        """
        base_dir = "data/known_faces"
        os.makedirs(base_dir, exist_ok=True)

        person_dir = os.path.join(base_dir, name)
        os.makedirs(person_dir, exist_ok=True)

        # Save image for record keeping
        save_path = os.path.join(person_dir, f"{len(os.listdir(person_dir))}.jpg")
        cv2.imwrite(save_path, image)

        # Generate embedding using same pipeline
        embedding = self.get_embedding_from_frame(image)
        if embedding is None:
            print(f"[WARN] No face found in the provided image for {name}")
            return False

        # Store embedding and metadata in memory
        self.known_faces[name] = {
            'embedding': embedding,
            'age': age,           # Optional now
            'role': role,         # Optional now
            'meta': meta or {}
        }

        print(f"✅ Registered {name} successfully — embeddings shape: {embedding.shape if embedding is not None else 'None'}")
        return True

    # def register_known_face(self, name, age, role, image, meta = None):
    #     """
    #     Add or update a known face profile directly from a BGR OpenCV frame.
    #     Saves locally and stores embedding in memory.
    #     """
    #     # Create known_faces directory if missing
    #     base_dir = "data/known_faces"
    #     os.makedirs(base_dir, exist_ok=True)
        
    #     person_dir = os.path.join(base_dir, name)
    #     os.makedirs(person_dir, exist_ok=True)
        
    #     # Save image for record keeping
    #     save_path = os.path.join(person_dir, f"{len(os.listdir(person_dir))}.jpg")
    #     cv2.imwrite(save_path, image)
        
    #     # Generate embedding using same pipeline
    #     embedding = self.get_embedding_from_frame(image)
    #     if embedding is None:
    #         print(f"[WARN] No face found in the provided image for {name}")
    #         return False
        
    #     # Store embedding and metadata in memory
    #     self.known_faces[name] = {'embedding': embedding, 'age': age, 'role': role, 'meta': meta or {}}
    #     print(f"✅ Registered {name} successfully — embeddings shape: {embedding.shape if embedding is not None else 'None'}")

    #     print(f"[INFO] Registered new face for {name}")
    #     return True
