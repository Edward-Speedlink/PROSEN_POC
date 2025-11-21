from detectors.face_detector import FaceDetector
import cv2

detector = FaceDetector()
detector.add_known_face("Edward Ndiyo", 24, "HOD Innovations Department", "pic3.jpeg")

frame = cv2.imread("pic4.jpeg")
faces = detector.detect_faces(frame, 1)
print(faces)

# print(detector.detect_faces(frame, 1))

# Draw boxes and text on the frame
for face in faces:
    x1, y1, x2, y2 = face['box']
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green box
    text = f"{face['name']} ({face['role']}, {face['age']}) - Conf: {face['conf']:.2f}"
    cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)  # White text

# Save the annotated image
cv2.imwrite("output_annotated.jpg", frame)
print("Annotated image saved as output_annotated.jpg")