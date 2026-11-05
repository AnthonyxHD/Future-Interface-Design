
import time
from threading import Lock
from uuid import uuid4

import cv2
import mediapipe as mp

from flask import (
    Flask,
    Response,
    jsonify,
    request,
    send_from_directory,
)

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from pose_definitions import POSEN as POSEN_REGELN

from yoga_coach import (
    MODELLPFAD,
    CoachZustand,
    erkenne_pose,
    zeichne_skelett,
)


# --------------------------------------------------
# 1. FLASK UND YOGA-POSEN
# --------------------------------------------------

app = Flask(__name__)

POSEN = [
    "Arme oben",
    "Warrior II",
    "Baum",
    "Stuhl",
    "Dreieck",
]

status_lock = Lock()
kamera_lock = Lock()


def leerer_status(pose=None, versuch_id=None):
    haltezeit = (
        float(POSEN_REGELN[pose]["haltezeit"])
        if pose in POSEN_REGELN
        else 0.0
    )

    return {
        "pose": pose,
        "versuch_id": versuch_id,
        "status": "Nimm deine Pose ein",
        "dauer": 0.0,
        "haltezeit": haltezeit,
        "prozent": 0,
        "erfolg": False,
    }


fortschritt = leerer_status()


# --------------------------------------------------
# 2. HTML, CSS UND JAVASCRIPT
# --------------------------------------------------

@app.route("/")
def startseite():
    return send_from_directory(".", "index.html")


@app.route("/style.css")
def stylesheet():
    return send_from_directory(".", "style.css")


@app.route("/app.js")
def javascript():
    return send_from_directory(".", "app.js")


# --------------------------------------------------
# 3. POSE AUSWÄHLEN / VERSUCH STARTEN
# --------------------------------------------------

@app.route("/api/pose", methods=["POST"])
def pose_auswaehlen():
    daten = request.get_json(silent=True) or {}
    pose = daten.get("pose")

    if pose not in POSEN or pose not in POSEN_REGELN:
        return jsonify({
            "error": "Unbekannte Pose"
        }), 400

    # Jeder Versuch bekommt eine neue Kennung.
    # Das gilt auch beim Wiederholen derselben Pose.
    versuch_id = uuid4().hex

    with status_lock:
        fortschritt.update(
            leerer_status(pose, versuch_id)
        )

    print(
        f"Neuer Versuch: {pose} | ID: {versuch_id[:8]}",
        flush=True,
    )

    return jsonify({
        "status": "ok",
        "pose": pose,
        "versuch_id": versuch_id,
    })


# --------------------------------------------------
# 4. AKTUELLEN FORTSCHRITT ABRUFEN
# --------------------------------------------------

@app.route("/api/status")
def pose_status():
    with status_lock:
        daten = fortschritt.copy()

    response = jsonify(daten)
    response.headers["Cache-Control"] = "no-store"
    return response


# --------------------------------------------------
# 5. KAMERA UND MEDIAPIPE
# --------------------------------------------------

def kamera_frames(pose, versuch_id):

    # Verhindert, dass zwei Streams gleichzeitig
    # dieselbe MacBook-Kamera verwenden.
    if not kamera_lock.acquire(timeout=5):
        print("Kamera noch durch alten Stream belegt.")
        return

    kamera = None

    try:
        # Alten Versuch nicht erneut starten
        with status_lock:
            if fortschritt["versuch_id"] != versuch_id:
                return

        kamera = cv2.VideoCapture(0)

        if not kamera.isOpened():
            print(
                "Kamera konnte nicht geöffnet werden.",
                flush=True,
            )
            return

        # Tatsächliche Kameraauflösung anfordern
        kamera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print(
            "Kameraauflösung:",
            kamera.get(cv2.CAP_PROP_FRAME_WIDTH),
            "x",
            kamera.get(cv2.CAP_PROP_FRAME_HEIGHT),
            flush=True,
        )

        # MediaPipe konfigurieren
        optionen = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(
                model_asset_path=str(MODELLPFAD)
            ),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
        )

        # Eigener Zustand für jeden neuen Versuch
        zustand = CoachZustand(pose_namen=POSEN)
        zustand.waehle_pose(POSEN.index(pose))

        beginn = time.monotonic()
        letzter_timestamp = -1
        letzter_debug = 0.0

        with vision.PoseLandmarker.create_from_options(
            optionen
        ) as detector:

            while True:

                # Prüfen, ob dieser Versuch noch aktiv ist
                with status_lock:
                    if fortschritt["versuch_id"] != versuch_id:
                        break

                erfolg, bild = kamera.read()

                if not erfolg:
                    print("Kein Kamerabild empfangen.")
                    break

                jetzt = time.monotonic()

                # Bild für MediaPipe in RGB umwandeln
                rgb = cv2.cvtColor(
                    bild,
                    cv2.COLOR_BGR2RGB,
                )

                mp_bild = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=rgb,
                )

                # Fortlaufende Zeitstempel für MediaPipe
                timestamp = max(
                    int((jetzt - beginn) * 1000),
                    letzter_timestamp + 1,
                )

                letzter_timestamp = timestamp

                # Körperpunkte erkennen
                ergebnis = detector.detect_for_video(
                    mp_bild,
                    timestamp,
                )

                pose_ok = False

                if ergebnis.pose_landmarks:
                    punkte = ergebnis.pose_landmarks[0]

                    hoehe, breite = bild.shape[:2]

                    # Yoga-Pose überprüfen
                    pose_ok = erkenne_pose(
                        punkte,
                        zustand.regel,
                        breite,
                        hoehe,
                    )

                    # Skelett auf das Bild zeichnen
                    zeichne_skelett(bild, punkte)

                # ----------------------------------
                # 6. HALTEZEIT UND ERFOLG
                # ----------------------------------

                bereits_erfolgreich = (
                    zustand.erfolg_gespeichert
                )

                status = zustand.aktualisiere_status(
                    pose_ok,
                    jetzt,
                )

                haltezeit = float(
                    zustand.regel["haltezeit"]
                )

                if zustand.erfolg_gespeichert:
                    dauer = haltezeit

                elif zustand.hold_start is not None:
                    dauer = min(
                        jetzt - zustand.hold_start,
                        haltezeit,
                    )

                else:
                    dauer = 0.0

                if haltezeit > 0:
                    prozent = round(
                        100 * dauer / haltezeit
                    )
                else:
                    prozent = 0

                prozent = max(
                    0,
                    min(100, prozent),
                )

                # Fortschritt an Flask übergeben
                with status_lock:
                    if (
                        fortschritt["pose"] == pose
                        and fortschritt["versuch_id"]
                        == versuch_id
                    ):
                        fortschritt.update({
                            "status": status,
                            "dauer": round(dauer, 2),
                            "haltezeit": haltezeit,
                            "prozent": prozent,
                            "erfolg": (
                                zustand.erfolg_gespeichert
                            ),
                        })

                # Erfolg nur einmal ausgeben
                if (
                    zustand.erfolg_gespeichert
                    and not bereits_erfolgreich
                ):
                    print(
                        f"ERFOLG! Pose geschafft: {pose}",
                        flush=True,
                    )

                # Diagnose ungefähr einmal pro Sekunde
                if jetzt - letzter_debug >= 1.0:
                    print(
                        f"Pose: {pose} | "
                        f"Körper: "
                        f"{bool(ergebnis.pose_landmarks)} | "
                        f"Pose korrekt: {pose_ok} | "
                        f"Fortschritt: {prozent}% | "
                        f"Status: {status}",
                        flush=True,
                    )
                    letzter_debug = jetzt

                # ----------------------------------
                # 7. BILD AN DEN BROWSER SENDEN
                # ----------------------------------

                ok, buffer = cv2.imencode(
                    ".jpg",
                    bild,
                    [cv2.IMWRITE_JPEG_QUALITY, 90],
                )

                if not ok:
                    continue

                frame = buffer.tobytes()

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )

    finally:
        if kamera is not None:
            kamera.release()

        kamera_lock.release()

        print(
            "Kamera freigegeben.",
            flush=True,
        )


# --------------------------------------------------
# 8. KAMERASTREAM BEREITSTELLEN
# --------------------------------------------------

@app.route("/video_feed")
def video_feed():

    pose = request.args.get("pose")
    versuch_id = request.args.get("versuch_id")

    if pose not in POSEN:
        return jsonify({
            "error": "Unbekannte Pose"
        }), 400

    with status_lock:
        gueltig = (
            versuch_id is not None
            and fortschritt["pose"] == pose
            and fortschritt["versuch_id"] == versuch_id
        )

    if not gueltig:
        return jsonify({
            "error": "Ungültiger Versuch"
        }), 409

    return Response(
        kamera_frames(pose, versuch_id),
        mimetype=(
            "multipart/x-mixed-replace; boundary=frame"
        ),
        headers={"Cache-Control": "no-store"},
    )


# --------------------------------------------------
# 9. FLASK STARTEN
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,
        threaded=True,
    )
