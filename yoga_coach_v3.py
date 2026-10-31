
import cv2
import mediapipe as mp
import time
import math
from pose_definitions import POSEN

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


def berechne_winkel(a, b, c, breite, hoehe):
    # Koordinaten in Bildpixel umrechnen
    v1 = (
        (a.x - b.x) * breite,
        (a.y - b.y) * hoehe
    )

    v2 = (
        (c.x - b.x) * breite,
        (c.y - b.y) * hoehe
    )

    # Laenge der beiden Vektoren
    laenge1 = math.hypot(*v1)
    laenge2 = math.hypot(*v2)

    if laenge1 * laenge2 < 0.000001:
        return None

    # Winkel zwischen den beiden Vektoren
    cos_winkel = (
        v1[0] * v2[0] + v1[1] * v2[1]
    ) / (laenge1 * laenge2)

    cos_winkel = max(-1.0, min(1.0, cos_winkel))

    return math.degrees(math.acos(cos_winkel))

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
regel = POSEN["Arme oben"]
hold_start = None

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

            # 5. Yoga-Position anhand der Regeln erkennen
            pose_ok = False

            if result.pose_landmarks:
                p = result.pose_landmarks[0]

                sichtbar = all(
                    p[i].visibility > regel["sichtbarkeit"]
                    for i in [11, 12, 13, 14, 15, 16]
                )

                if sichtbar:
                    hoehe, breite = frame.shape[:2]

                    links = berechne_winkel(
                        p[11], p[13], p[15],
                        breite, hoehe
                    )

                    rechts = berechne_winkel(
                        p[12], p[14], p[16],
                        breite, hoehe
                    )

                    abstand = regel["hand_ueber_schulter"]

                    arme_oben = (
                        p[15].y < p[11].y - abstand
                        and p[16].y < p[12].y - abstand
                        and p[13].y < p[11].y
                        and p[14].y < p[12].y
                    )

                    arme_gestreckt = (
                        links is not None
                        and rechts is not None
                        and links >= regel["ellbogen_min"]
                        and rechts >= regel["ellbogen_min"]
                    )

                    pose_ok = arme_oben and arme_gestreckt

            # 6. Prüfen, wie lange die Position gehalten wird
            if pose_ok:
                if hold_start is None:
                    hold_start = time.monotonic()

                dauer = time.monotonic() - hold_start

                if dauer >= regel["haltezeit"]:
                    status = "GUT GEMACHT!"
                else:
                    status = f"Halten: {dauer:.1f} / {regel['haltezeit']:.1f} s"
            else:
                hold_start = None
                status = "Beide Arme nach oben strecken"

            # 7. Feedback auf das Kamerabild schreiben
            cv2.rectangle(
                frame, (10, 10), (560, 70), (0, 0, 0), -1
            )

            cv2.putText(
                frame, status, (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 255, 0), 2
            )


            if result.pose_landmarks:
                points = result.pose_landmarks[0]
                height, width = frame.shape[:2]


                # Winkel der beiden Ellbogen messen
                if all(
                    points[i].visibility > 0.6
                    for i in [11, 12, 13, 14, 15, 16]
                ):
                    links = berechne_winkel(
                        points[11], points[13], points[15],
                        width, height
                    )

                    rechts = berechne_winkel(
                        points[12], points[14], points[16],
                        width, height
                    )

                    if links is not None and rechts is not None:
                        text = (
                            f"Ellbogen: L {links:.0f} "
                            f"| R {rechts:.0f} Grad"
                        )

                        cv2.rectangle(
                            frame, (10, 80), (550, 130),
                            (0, 0, 0), -1
                        )

                        cv2.putText(
                            frame, text, (20, 112),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 255, 255), 2
                        )

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
