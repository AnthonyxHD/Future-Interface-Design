
import cv2

# 1. Kamera des MacBooks öffnen
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    raise RuntimeError("Kamera konnte nicht geöffnet werden.")

# 2. Kamerabilder laufend anzeigen
while True:
    success, frame = camera.read()

    if not success:
        print("Kein Kamerabild empfangen.")
        break

    cv2.imshow("Mein Yoga Coach", frame)

    # Mit Q das Programm beenden
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# 3. Kamera freigeben und Fenster schliessen
camera.release()
cv2.destroyAllWindows()
