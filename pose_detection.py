
import cv2
import mediapipe as mp
import time

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Vortrainiertes Modell laden
options = vision.PoseLandmarkerOptions(
    base_options=python.BaseOptions(
        model_asset_path="pose_landmarker_lite.task"
    ),
    running_mode=vision.RunningMode.VIDEO,
    num_poses=1
)

# 2. Kamera starten
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    raise RuntimeError("Kamera konnte nicht geöffnet werden.")

start_time = time.monotonic()
last_timestamp = -1

try:
    with vision.PoseLandmarker.create_from_options(options) as detector:

        while True:
            success, frame = camera.read()

            if not success:
                break

            # OpenCV-Bild für MediaPipe vorbereiten
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            # Zeitpunkt des aktuellen Videobildes
            timestamp = int(
                (time.monotonic() - start_time) * 1000
            )
            timestamp = max(timestamp, last_timestamp + 1)
            last_timestamp = timestamp

            # 3. Körperpunkte erkennen
            result = detector.detect_for_video(image, timestamp)

            if result.pose_landmarks:
                points = result.pose_landmarks[0]
                height, width = frame.shape[:2]

                # 4. Gelenke miteinander verbinden
                connections = (
                    vision.PoseLandmarksConnections.POSE_LANDMARKS
                )

                for connection in connections:
                    a = points[connection.start]
                    b = points[connection.end]

                    if min(a.visibility, b.visibility) < 0.5:
                        continue

                    p1 = (int(a.x * width), int(a.y * height))
                    p2 = (int(b.x * width), int(b.y * height))

                    cv2.line(frame, p1, p2, (0, 255, 0), 2)

                # Gelenkpunkte einzeichnen
                for point in points:
                    if point.visibility < 0.5:
                        continue

                    x = int(point.x * width)
                    y = int(point.y * height)
                    cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)

            cv2.imshow("Yoga Coach - Pose Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

finally:
    camera.release()
    cv2.destroyAllWindows()
