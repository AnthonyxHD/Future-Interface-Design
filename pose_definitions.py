# Globale Standardeinstellungen
STANDARD_HALTEZEIT = 3.0

# Globale Pose-Definitionen
POSEN = {
    "Arme oben": {
        "typ": "oben",
        "sichtbarkeit": 0.6,
        "hand_ueber_schulter": 0.10,
        "ellbogen_min": 160,
    },

    "Warrior II": {
        "typ": "krieger_2",
        "sichtbarkeit": 0.6,
        "hoehen_toleranz": 0.12,
        "seitlicher_abstand": 0.12,
        "ellbogen_min": 160,
        "knie_gebeugt_min": 85,
        "knie_gebeugt_max": 145,
        "knie_gestreckt_min": 155,
    },

    "Baum": {
        "typ": "baum",
        "sichtbarkeit": 0.6,
        "hand_ueber_schulter": 0.10,
        "ellbogen_min": 150,
        "knie_gebeugt_min": 35,
        "knie_gebeugt_max": 130,
        "knie_gestreckt_min": 155,
        "fuss_hoeher": 0.12,
        "fuss_nahe_bein": 0.16,
        "knie_seitlich_min": 0.06,
    },

    "Stuhl": {
        "typ": "stuhl",
        "sichtbarkeit": 0.6,
        "knie_min": 105,
        "knie_max": 160,
        "huefte_min": 90,
        "huefte_max": 155,
    },

    "Dreieck": {
        "typ": "dreieck",
        "sichtbarkeit": 0.6,
        "ellbogen_min": 150,
        "knie_min": 150,
        "fuss_abstand_min": 0.22,
        "neigung_min": 25,
        "neigung_max": 80,
        "hand_oben_abstand": 0.08,
        "hand_unten_abstand": 0.15,
        "knie_naehe_toleranz": 0.12
    },

    "T-Pose": {
        "typ": "seitlich",
        "sichtbarkeit": 0.6,
        "hoehen_toleranz": 0.10,
        "seitlicher_abstand": 0.12,
        "ellbogen_min": 160,
    }
}

# Reihenfolge für die Tastatursteuerung festlegen
REIHENFOLGE = (
    "Arme oben",
    "Warrior II",
    "Baum",
    "Stuhl",
    "Dreieck",
    "T-Pose"
)

POSEN = {name: POSEN[name] for name in REIHENFOLGE}

# Standard-Haltezeit für alle Posen übernehmen
for pose in POSEN.values():
    pose.setdefault("haltezeit", STANDARD_HALTEZEIT)