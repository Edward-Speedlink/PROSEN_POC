from detectors.plate_anpr import PlateANPR
import cv2
anpr = PlateANPR()
frame = cv2.imread('Test_2.jpeg')  # Use a sample image with a car/plate
results = anpr.detect_and_read(frame, 1)
print(results)