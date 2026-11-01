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

    "T-Pose": {
        "typ": "seitlich",
        "sichtbarkeit": 0.6,
        "hoehen_toleranz": 0.10,
        "seitlicher_abstand": 0.12,
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
}

# Standard-Haltezeit für alle Posen übernehmen
for pose in POSEN.values():
    pose.setdefault("haltezeit", STANDARD_HALTEZEIT)