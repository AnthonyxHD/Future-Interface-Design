import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from pose_definitions import POSEN


# MediaPipe-Indizes: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
SCHULTER_L, SCHULTER_R = 11, 12
ELLBOGEN_L, ELLBOGEN_R = 13, 14
HAND_L, HAND_R = 15, 16
HUEFTE_L, HUEFTE_R = 23, 24
KNIE_L, KNIE_R = 25, 26
FUSS_L, FUSS_R = 27, 28

ARM_PUNKTE = (SCHULTER_L, SCHULTER_R, ELLBOGEN_L, ELLBOGEN_R, HAND_L, HAND_R)
BEIN_PUNKTE = (HUEFTE_L, HUEFTE_R, KNIE_L, KNIE_R, FUSS_L, FUSS_R)
MODELLPFAD = Path(__file__).resolve().parent / "pose_landmarker_lite.task"


@dataclass
class CoachZustand:
    """Aktuelle Auswahl und Fortschritt – unabhängig von der Eingabemethode.

    Die spätere Touchscreen-Oberfläche kann ebenfalls ``waehle_pose`` aufrufen.
    """

    pose_namen: list[str]
    aktive_pose: int = 0
    hold_start: float | None = None
    erfolg_gespeichert: bool = False

    @property
    def pose_name(self) -> str:
        return self.pose_namen[self.aktive_pose]

    @property
    def regel(self) -> dict:
        return POSEN[self.pose_name]

    def waehle_pose(self, index: int) -> None:
        """Pose auswählen; auch eine erneute Auswahl setzt den Erfolg zurück."""
        if not 0 <= index < len(self.pose_namen):
            raise ValueError(f"Ungültiger Pose-Index: {index}")

        self.aktive_pose = index
        self.hold_start = None
        self.erfolg_gespeichert = False
        print(f"Neue Pose: {self.pose_name}")

    def aktualisiere_status(self, pose_ok: bool, jetzt: float) -> str:
        """Haltezeit überwachen und den Erfolg bis zur nächsten Auswahl merken."""
        if self.erfolg_gespeichert:
            return "GUT GEMACHT!"

        if not pose_ok:
            self.hold_start = None
            return f"{self.pose_name} einnehmen"

        if self.hold_start is None:
            self.hold_start = jetzt

        dauer = jetzt - self.hold_start
        haltezeit = self.regel["haltezeit"]
        if dauer >= haltezeit:
            self.erfolg_gespeichert = True
            self.hold_start = None
            return "GUT GEMACHT!"

        return f"Halten: {dauer:.1f} / {haltezeit:.1f} s"


def berechne_winkel(a, b, c, breite: int, hoehe: int) -> float | None:
    """2D-Winkel ABC in Grad; B ist das Gelenk (der Scheitelpunkt).

    MediaPipe-Koordinaten sind normalisiert. Die Umrechnung in Pixel
    verhindert Verzerrungen durch unterschiedliche Bild-Seitenverhältnisse.
    """
    v1 = ((a.x - b.x) * breite, (a.y - b.y) * hoehe)
    v2 = ((c.x - b.x) * breite, (c.y - b.y) * hoehe)
    laenge1, laenge2 = math.hypot(*v1), math.hypot(*v2)

    if laenge1 * laenge2 < 1e-6:
        return None

    kosinus = (v1[0] * v2[0] + v1[1] * v2[1]) / (laenge1 * laenge2)
    kosinus = max(-1.0, min(1.0, kosinus))
    return math.degrees(math.acos(kosinus))


def punkte_sichtbar(punkte, indices, schwelle: float) -> bool:
    """Nur ausreichend sichtbare Körperpunkte für Regeln verwenden."""
    return all(punkte[i].visibility > schwelle for i in indices)


def kniewinkel(p, breite: int, hoehe: int) -> tuple[float | None, float | None]:
    """Kniewinkel links und rechts (Hüfte – Knie – Fussgelenk)."""
    return (
        berechne_winkel(p[HUEFTE_L], p[KNIE_L], p[FUSS_L], breite, hoehe),
        berechne_winkel(p[HUEFTE_R], p[KNIE_R], p[FUSS_R], breite, hoehe),
    )


def arme_oben(p, abstand: float) -> bool:
    """Handgelenke und Ellbogen liegen oberhalb der Schultern."""
    return (
        p[HAND_L].y < p[SCHULTER_L].y - abstand
        and p[HAND_R].y < p[SCHULTER_R].y - abstand
        and p[ELLBOGEN_L].y < p[SCHULTER_L].y
        and p[ELLBOGEN_R].y < p[SCHULTER_R].y
    )


def arme_seitlich(p, toleranz: float, abstand: float) -> bool:
    """Arme ungefähr waagerecht und seitlich vom Körper entfernt."""
    return (
        abs(p[HAND_L].y - p[SCHULTER_L].y) < toleranz
        and abs(p[HAND_R].y - p[SCHULTER_R].y) < toleranz
        and abs(p[ELLBOGEN_L].y - p[SCHULTER_L].y) < toleranz
        and abs(p[ELLBOGEN_R].y - p[SCHULTER_R].y) < toleranz
        and abs(p[HAND_L].x - p[SCHULTER_L].x) > abstand
        and abs(p[HAND_R].x - p[SCHULTER_R].x) > abstand
    )


def pruefe_krieger_2(p, regel: dict, breite: int, hoehe: int) -> bool:
    """Ein Knie gebeugt, das andere gestreckt; beide Seiten erlaubt."""
    if not punkte_sichtbar(p, BEIN_PUNKTE, regel["sichtbarkeit"]):
        return False

    links, rechts = kniewinkel(p, breite, hoehe)
    if links is None or rechts is None:
        return False

    def gebeugt(winkel: float) -> bool:
        return regel["knie_gebeugt_min"] <= winkel <= regel["knie_gebeugt_max"]

    def gestreckt(winkel: float) -> bool:
        return winkel >= regel["knie_gestreckt_min"]
    return (gebeugt(links) and gestreckt(rechts)) or (gebeugt(rechts) and gestreckt(links))


def pruefe_baum(p, regel: dict, breite: int, hoehe: int) -> bool:
    """Ein Standbein und ein seitlich angewinkeltes Bein; links/rechts möglich."""
    if not punkte_sichtbar(p, BEIN_PUNKTE, regel["sichtbarkeit"]):
        return False

    links, rechts = kniewinkel(p, breite, hoehe)
    if links is None or rechts is None:
        return False

    # Variante A: links stehen, rechten Fuss zum linken Bein anheben.
    links_standbein = (
        links >= regel["knie_gestreckt_min"]
        and regel["knie_gebeugt_min"] <= rechts <= regel["knie_gebeugt_max"]
        and p[FUSS_R].y < p[FUSS_L].y - regel["fuss_hoeher"]
        and abs(p[FUSS_R].x - p[KNIE_L].x) < regel["fuss_nahe_bein"]
        and abs(p[KNIE_R].x - p[HUEFTE_R].x) > regel["knie_seitlich_min"]
    )
    # Variante B: rechts stehen, linken Fuss zum rechten Bein anheben.
    rechts_standbein = (
        rechts >= regel["knie_gestreckt_min"]
        and regel["knie_gebeugt_min"] <= links <= regel["knie_gebeugt_max"]
        and p[FUSS_L].y < p[FUSS_R].y - regel["fuss_hoeher"]
        and abs(p[FUSS_L].x - p[KNIE_R].x) < regel["fuss_nahe_bein"]
        and abs(p[KNIE_L].x - p[HUEFTE_L].x) > regel["knie_seitlich_min"]
    )
    return links_standbein or rechts_standbein


def pruefe_stuhl(p, regel: dict, breite: int, hoehe: int) -> bool:
    """Beide Knie und Hüften gebeugt; Arme werden nicht bewertet."""
    # Hüftwinkel benötigen zusätzlich die Schultern – daher Sichtbarkeit prüfen.
    if not punkte_sichtbar(
        p, (*BEIN_PUNKTE, SCHULTER_L, SCHULTER_R), regel["sichtbarkeit"]
    ):
        return False

    knie_links, knie_rechts = kniewinkel(p, breite, hoehe)
    huefte_links = berechne_winkel(p[SCHULTER_L], p[HUEFTE_L], p[KNIE_L], breite, hoehe)
    huefte_rechts = berechne_winkel(p[SCHULTER_R], p[HUEFTE_R], p[KNIE_R], breite, hoehe)
    if any(w is None for w in (knie_links, knie_rechts, huefte_links, huefte_rechts)):
        return False

    return (
        regel["knie_min"] <= knie_links <= regel["knie_max"]
        and regel["knie_min"] <= knie_rechts <= regel["knie_max"]
        and regel["huefte_min"] <= huefte_links <= regel["huefte_max"]
        and regel["huefte_min"] <= huefte_rechts <= regel["huefte_max"]
    )


def pruefe_dreieck(p, regel: dict, breite: int, hoehe: int) -> bool:
    """Erkennt eine vereinfachte Dreieck-Pose auf beiden Seiten."""

    # 1. Sind Arme und Beine ausreichend sichtbar?
    erforderliche_punkte = (*ARM_PUNKTE, *BEIN_PUNKTE)

    if not punkte_sichtbar(
        p, erforderliche_punkte, regel["sichtbarkeit"]
    ):
        return False

    # 2. Ellbogenwinkel berechnen
    ellbogen_links = berechne_winkel(
        p[SCHULTER_L], p[ELLBOGEN_L], p[HAND_L],
        breite, hoehe
    )
    ellbogen_rechts = berechne_winkel(
        p[SCHULTER_R], p[ELLBOGEN_R], p[HAND_R],
        breite, hoehe
    )

    # 3. Kniewinkel berechnen
    knie_links, knie_rechts = kniewinkel(p, breite, hoehe)

    winkel = (
        ellbogen_links, ellbogen_rechts,
        knie_links, knie_rechts
    )

    if any(w is None for w in winkel):
        return False

    arme_ok = (
        ellbogen_links >= regel["ellbogen_min"]
        and ellbogen_rechts >= regel["ellbogen_min"]
    )

    beine_ok = (
        knie_links >= regel["knie_min"]
        and knie_rechts >= regel["knie_min"]
    )

    # 4. Sind die Fuesse ausreichend weit auseinander?
    fuesse_ok = (
        abs(p[FUSS_L].x - p[FUSS_R].x)
        >= regel["fuss_abstand_min"]
    )

    # 5. Neigung des Oberkoerpers berechnen
    schulter_x = (p[SCHULTER_L].x + p[SCHULTER_R].x) / 2
    schulter_y = (p[SCHULTER_L].y + p[SCHULTER_R].y) / 2

    huefte_x = (p[HUEFTE_L].x + p[HUEFTE_R].x) / 2
    huefte_y = (p[HUEFTE_L].y + p[HUEFTE_R].y) / 2

    dx = abs(schulter_x - huefte_x) * breite
    dy = abs(schulter_y - huefte_y) * hoehe

    neigung = math.degrees(math.atan2(dx, dy))

    neigung_ok = (
        regel["neigung_min"]
        <= neigung
        <= regel["neigung_max"]
    )

    # 6. Eine Hand oben, die andere unten
    knie_hoehe = min(p[KNIE_L].y, p[KNIE_R].y)

    def arm_oben(hand, schulter):
        return (
            p[hand].y
            < p[schulter].y - regel["hand_oben_abstand"]
        )

    def arm_unten(hand, schulter):
        return (
            p[hand].y
            > p[schulter].y + regel["hand_unten_abstand"]
            and p[hand].y
            >= knie_hoehe - regel["knie_naehe_toleranz"]
        )

    # Beide Ausrichtungen akzeptieren
    arme_position_ok = (
        arm_oben(HAND_L, SCHULTER_L)
        and arm_unten(HAND_R, SCHULTER_R)
    ) or (
        arm_oben(HAND_R, SCHULTER_R)
        and arm_unten(HAND_L, SCHULTER_L)
    )

    # 7. Alle Bedingungen muessen erfuellt sein
    return (
        arme_ok
        and beine_ok
        and fuesse_ok
        and neigung_ok
        and arme_position_ok
    )

def erkenne_pose(p, regel: dict, breite: int, hoehe: int) -> bool:
    """Prüft eine Pose gegen ihre konfigurierten 2D-Regeln.

    MediaPipe übernimmt bereits die ML-basierte Landmark-Erkennung.
    Dieser Klassifikator ist bewusst regelbasiert und erfordert kein Training.
    """
    typ = regel["typ"]
    if typ == "stuhl":
        return pruefe_stuhl(p, regel, breite, hoehe)

    if typ == "dreieck":
        return pruefe_dreieck(p, regel, breite, hoehe)

    if typ not in ("oben", "seitlich", "krieger_2", "baum"):
        return False
    if not punkte_sichtbar(p, ARM_PUNKTE, regel["sichtbarkeit"]):
        return False

    links = berechne_winkel(p[SCHULTER_L], p[ELLBOGEN_L], p[HAND_L], breite, hoehe)
    rechts = berechne_winkel(p[SCHULTER_R], p[ELLBOGEN_R], p[HAND_R], breite, hoehe)
    if links is None or rechts is None:
        return False
    if links < regel["ellbogen_min"] or rechts < regel["ellbogen_min"]:
        return False

    if typ in ("oben", "baum"):
        if not arme_oben(p, regel["hand_ueber_schulter"]):
            return False
    else:
        if not arme_seitlich(p, regel["hoehen_toleranz"], regel["seitlicher_abstand"]):
            return False

    if typ == "krieger_2":
        return pruefe_krieger_2(p, regel, breite, hoehe)
    if typ == "baum":
        return pruefe_baum(p, regel, breite, hoehe)
    return True


def zeichne_skelett(bild, punkte) -> None:
    """Verbindungen (grün) und sichtbare Landmarken (rot) einzeichnen."""
    hoehe, breite = bild.shape[:2]
    for verbindung in vision.PoseLandmarksConnections.POSE_LANDMARKS:
        a, b = punkte[verbindung.start], punkte[verbindung.end]
        if min(a.visibility, b.visibility) < 0.5:
            continue
        p1 = (int(a.x * breite), int(a.y * hoehe))
        p2 = (int(b.x * breite), int(b.y * hoehe))
        cv2.line(bild, p1, p2, (0, 255, 0), 2)

    for punkt in punkte:
        if punkt.visibility >= 0.5:
            pos = (int(punkt.x * breite), int(punkt.y * hoehe))
            cv2.circle(bild, pos, 4, (0, 0, 255), -1)


def zeichne_feedback(bild, status: str, punkte=None) -> None:
    """Status und optionale Ellbogenwinkel in das Kamerabild zeichnen."""
    cv2.rectangle(bild, (10, 10), (560, 70), (0, 0, 0), -1)
    cv2.putText(bild, status, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    if punkte is None or not punkte_sichtbar(punkte, ARM_PUNKTE, 0.6):
        return

    hoehe, breite = bild.shape[:2]
    links = berechne_winkel(punkte[SCHULTER_L], punkte[ELLBOGEN_L], punkte[HAND_L], breite, hoehe)
    rechts = berechne_winkel(punkte[SCHULTER_R], punkte[ELLBOGEN_R], punkte[HAND_R], breite, hoehe)
    if links is None or rechts is None:
        return

    text = f"Ellbogen: L {links:.0f} | R {rechts:.0f} Grad"
    cv2.rectangle(bild, (10, 80), (550, 130), (0, 0, 0), -1)
    cv2.putText(bild, text, (20, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)


def main() -> None:
    """Kamera lesen, Pose prüfen, Feedback anzeigen, Tastatur verarbeiten."""
    if not POSEN:
        raise ValueError("Keine Pose in pose_definitions.py definiert.")
    if not MODELLPFAD.is_file():
        raise FileNotFoundError(f"MediaPipe-Modell nicht gefunden: {MODELLPFAD}")

    zustand = CoachZustand(pose_namen=list(POSEN))
    tasten_zu_posen = {
        ord(str(index + 1)): index
        for index in range(min(len(zustand.pose_namen), 9))
    }
    optionen = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(MODELLPFAD)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
    )

    kamera = cv2.VideoCapture(0)  # MacBook-Webcam; Raspberry-Pi-Kamera später via Picamera2
    if not kamera.isOpened():
        raise RuntimeError("Kamera konnte nicht geöffnet werden.")

    beginn = time.monotonic()
    letzter_timestamp = -1
    try:
        with vision.PoseLandmarker.create_from_options(optionen) as detector:
            while True:
                success, bild = kamera.read()
                if not success:
                    print("Kein Kamerabild empfangen.")
                    break

                jetzt = time.monotonic()
                timestamp = max(int((jetzt - beginn) * 1000), letzter_timestamp + 1)
                letzter_timestamp = timestamp

                rgb = cv2.cvtColor(bild, cv2.COLOR_BGR2RGB)
                mp_bild = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ergebnis = detector.detect_for_video(mp_bild, timestamp)

                punkte = ergebnis.pose_landmarks[0] if ergebnis.pose_landmarks else None
                pose_ok = False
                if punkte is not None:
                    hoehe, breite = bild.shape[:2]
                    pose_ok = erkenne_pose(punkte, zustand.regel, breite, hoehe)
                    zeichne_skelett(bild, punkte)

                status = zustand.aktualisiere_status(pose_ok, jetzt)
                zeichne_feedback(bild, status, punkte)
                cv2.imshow("Yoga Coach - Pose Detection", bild)

                taste = cv2.waitKey(1) & 0xFF
                if taste == ord("q"):
                    break
                if taste in tasten_zu_posen:
                    zustand.waehle_pose(tasten_zu_posen[taste])
    finally:
        kamera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
