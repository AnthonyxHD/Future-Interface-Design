
import sys

from PySide6.QtCore import QPropertyAnimation
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QGridLayout, QHBoxLayout,
    QStackedWidget, QGraphicsOpacityEffect
)

POSEN = [
    "Arme oben",
    "Krieger II",
    "Baum",
    "Stuhl",
    "Dreieck",
]


class YogaUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Yoga Coach")
        self.resize(800, 480)

        self.aktive_pose = None
        self.animation = None

        self.seiten = QStackedWidget()

        self.auswahl = self.baue_auswahl()
        self.kamera = self.baue_kamera()
        self.erfolg = self.baue_erfolg()

        self.seiten.addWidget(self.auswahl)
        self.seiten.addWidget(self.kamera)
        self.seiten.addWidget(self.erfolg)

        layout = QVBoxLayout(self)
        layout.addWidget(self.seiten)

        self.zeige_auswahl()

    def button(self, text, funktion):
        btn = QPushButton(text)
        btn.setMinimumHeight(65)
        btn.clicked.connect(funktion)
        btn.setStyleSheet("""
            QPushButton {
                background: #394F5F;
                color: white;
                border-radius: 14px;
                font-size: 18px;
                padding: 10px;
            }
            QPushButton:pressed {
                background: #58768A;
            }
        """)
        return btn

    def baue_auswahl(self):
        seite = QWidget()
        layout = QVBoxLayout(seite)

        titel = QLabel("Wähle deine Yoga-Pose")
        titel.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
        )
        layout.addWidget(titel)

        raster = QGridLayout()

        for index, name in enumerate(POSEN):
            btn = self.button(
                name,
                lambda checked=False, n=name:
                    self.waehle_pose(n)
            )
            raster.addWidget(btn, index // 3, index % 3)

        layout.addLayout(raster)
        return seite

    def baue_kamera(self):
        seite = QWidget()
        layout = QVBoxLayout(seite)

        kopf = QHBoxLayout()
        self.pose_label = QLabel("")
        self.pose_label.setStyleSheet("font-size: 22px;")

        kopf.addWidget(self.pose_label)
        kopf.addStretch()
        kopf.addWidget(
            self.button("✕ Beenden", self.zeige_auswahl)
        )

        layout.addLayout(kopf)

        platzhalter = QLabel("Hier erscheint das Kamerabild")
        platzhalter.setStyleSheet("""
            background: #283A45;
            color: white;
            font-size: 22px;
            border-radius: 12px;
        """)
        platzhalter.setMinimumHeight(190)
        platzhalter.setAlignment(
            __import__("PySide6.QtCore", fromlist=["Qt"])
            .Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(platzhalter, 1)

        # Nur fuer unseren UI-Test
        layout.addWidget(
            self.button(
                "Erfolg simulieren",
                self.zeige_erfolg
            )
        )
        return seite

    def baue_erfolg(self):
        seite = QWidget()
        seite.setStyleSheet(
            "background: #DDF3E5; border-radius: 16px;"
        )

        layout = QVBoxLayout(seite)
        layout.addStretch()

        self.erfolg_label = QLabel("GUT GEMACHT!")
        self.erfolg_label.setStyleSheet("""
            color: #247D4C;
            font-size: 44px;
            font-weight: bold;
        """)
        self.erfolg_label.setAlignment(
            __import__("PySide6.QtCore", fromlist=["Qt"])
            .Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self.erfolg_label)

        layout.addStretch()

        layout.addWidget(
            self.button("Wiederholen", self.wiederholen)
        )
        layout.addWidget(
            self.button("Neue Pose", self.zeige_auswahl)
        )

        return seite

    def waehle_pose(self, name):
        self.aktive_pose = name
        self.pose_label.setText(name)
        self.seiten.setCurrentWidget(self.kamera)

    def zeige_auswahl(self):
        self.seiten.setCurrentWidget(self.auswahl)

    def wiederholen(self):
        self.waehle_pose(self.aktive_pose)

    def zeige_erfolg(self):
        self.seiten.setCurrentWidget(self.erfolg)

        effekt = QGraphicsOpacityEffect(
            self.erfolg_label
        )
        self.erfolg_label.setGraphicsEffect(effekt)

        self.animation = QPropertyAnimation(
            effekt, b"opacity"
        )
        self.animation.setDuration(650)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()


app = QApplication(sys.argv)

fenster = YogaUI()
fenster.show()

sys.exit(app.exec())