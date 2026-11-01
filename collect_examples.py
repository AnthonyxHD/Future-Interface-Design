
import csv
import math
import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Speicherort der Trainingsbeispiele
datei = Path("data/pose_examples.csv")
datei.parent.mkdir(exist_ok=True)

# Spalten: Label und 33 Körperpunkte
spalten = ["label"]
for i in range(33):
    spalten += [f"x_{i}", f"y_{i}", f"visibility_{i}"]

if not datei.exists():
    with datei.open("w", newline="") as f:
        csv.writer(f).writerow(spalten)

# MediaPipe-Modell laden
optionen = vision.PoseLandmarkerOptions(
    base_options=python.BaseOptions(
        model_asset_path="pose_landmarker_lite.task"
    ),
    running_mode=vision.RunningMode.VIDEO,
    num_poses=1
)

kamera = cv2.VideoCapture(0)

if not kamera.isOpened():
    raise RuntimeError("Kamera konnte nicht geöffnet werden.")

label = "baum"
anzahl = 0
start = time.monotonic()
letzter_zeitpunkt = -1

try:
    with vision.PoseLandmarker.create_from_options(optionen) as detector:
        while True:
            erfolg, bild = kamera.read()
            if not erfolg:
                break

            rgb = cv2.cvtColor(bild, cv2.COLOR_BGR2RGB)
            mp_bild = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            zeitpunkt = int((time.monotonic() - start) * 1000)
            zeitpunkt = max(zeitpunkt, letzter_zeitpunkt + 1)
            letzter_zeitpunkt = zeitpunkt

            ergebnis = detector.detect_for_video(
                mp_bild, zeitpunkt
            )

            # Erkannte Gelenke anzeigen
            if ergebnis.pose_landmarks:
                hoehe, breite = bild.shape[:2]

                for punkt in ergebnis.pose_landmarks[0]:
                    if punkt.visibility > 0.5:
                        x = int(punkt.x * breite)
                        y = int(punkt.y * hoehe)
                        cv2.circle(
                            bild, (x, y), 4, (0, 255, 0), -1
                        )

            cv2.putText(
                bild,
                f"Label: {label} | Gespeichert: {anzahl}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (255, 255, 255), 2
            )

            cv2.putText(
                bild,
                "1=Baum  0=Andere  S=Speichern  Q=Ende",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 2
            )

            cv2.imshow("Yoga Trainingsdaten", bild)
            taste = cv2.waitKey(1) & 0xFF

            if taste == ord("q"):
                break
            elif taste == ord("1"):
                label = "baum"
            elif taste == ord("0"):
                label = "andere"
            elif taste == ord("s"):
                if not ergebnis.pose_landmarks:
                    print("Keine Person erkannt.")
                    continue

                punkte = ergebnis.pose_landmarks[0]

                # Wichtige Körperpunkte müssen sichtbar sein
                wichtig = [11, 12, 23, 24, 25, 26, 27, 28]
                if any(punkte[i].visibility < 0.5 for i in wichtig):
                    print("Bitte ganzen Körper zeigen.")
                    continue

                # Hüfte als Mittelpunkt
                mitte_x = (punkte[23].x + punkte[24].x) / 2
                mitte_y = (punkte[23].y + punkte[24].y) / 2

                # Oberkörperlänge als Massstab
                schulter_x = (punkte[11].x + punkte[12].x) / 2
                schulter_y = (punkte[11].y + punkte[12].y) / 2

                skala = math.hypot(
                    schulter_x - mitte_x,
                    schulter_y - mitte_y
                )

                if skala < 0.05:
                    print("Körperposition nicht zuverlässig erkannt.")
                    continue

                zeile = [label]

                for punkt in punkte:
                    zeile.extend([
                        (punkt.x - mitte_x) / skala,
                        (punkt.y - mitte_y) / skala,
                        punkt.visibility
                    ])

                with datei.open("a", newline="") as f:
                    csv.writer(f).writerow(zeile)

                anzahl += 1
                print(f"Gespeichert: {label} ({anzahl})")

finally:
    kamera.release()
    cv2.destroyAllWindows()
