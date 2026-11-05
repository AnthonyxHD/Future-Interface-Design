
from flask import Flask, send_from_directory, request, jsonify, Response
import cv2

app = Flask(__name__)

POSEN = [
    "Arme oben",
    "Warrior II",
    "Baum",
    "Stuhl",
    "Dreieck"
]


@app.route("/")
def startseite():
    return send_from_directory(".", "index.html")


@app.route("/style.css")
def stylesheet():
    return send_from_directory(".", "style.css")


@app.route("/app.js")
def javascript():
    return send_from_directory(".", "app.js")


@app.route("/api/pose", methods=["POST"])
def pose_auswaehlen():
    daten = request.get_json(silent=True) or {}
    pose = daten.get("pose")

    if pose not in POSEN:
        return jsonify({"error": "Unbekannte Pose"}), 400

    print(f"Gewählte Pose: {pose}", flush=True)

    return jsonify({
        "status": "ok",
        "pose": pose
    })


def kamera_frames():
    kamera = cv2.VideoCapture(0)

    if not kamera.isOpened():
        print("Kamera konnte nicht geöffnet werden.", flush=True)
        return

    try:
        while True:
            erfolg, bild = kamera.read()

            if not erfolg:
                break

            bild = cv2.resize(bild, (640, 480))

            ok, buffer = cv2.imencode(".jpg", bild)

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
        kamera.release()


@app.route("/video_feed")
def video_feed():
    return Response(
        kamera_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
