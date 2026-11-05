
const auswahlScreen = document.querySelector("#auswahl-screen");
const kameraScreen = document.querySelector("#kamera-screen");
const erfolgScreen = document.querySelector("#erfolg-screen");

const poseTitel = document.querySelector("#aktuelle-pose");

const kameraVideo = document.querySelector("#kamera-video");

const feedbackStatus = document.querySelector("#feedback-status");
const feedbackZeit = document.querySelector("#feedback-zeit");
const progressFill = document.querySelector("#progress-fill");

let aktivePose = null;

let aktiverVersuch = null;

function zeigeScreen(screen) {
    auswahlScreen.classList.add("hidden");
    kameraScreen.classList.add("hidden");
    erfolgScreen.classList.add("hidden");

    screen.classList.remove("hidden");
}

if (screen !== kameraScreen) {
    kameraVideo.removeAttribute("src");
}

async function waehlePose(pose) {
    try {
        const antwort = await fetch("/api/pose", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ pose: pose })
        });

        if (!antwort.ok) {
            throw new Error("Pose konnte nicht gesendet werden");
        }

        const daten = await antwort.json();

        aktiverVersuch = daten.versuch_id;

        console.log("Python bestätigt:", daten.pose);

        
        aktivePose = pose;
        poseTitel.textContent = pose;

        // Fortschrittsanzeige zurücksetzen
        feedbackStatus.textContent = "Nimm deine Pose ein";
        feedbackZeit.textContent = "0.0 / 0.0 s";
        progressFill.style.width = "0%";

        document.querySelector("#pose-progress")
            .setAttribute("aria-valuenow", "0");

        // Kamerastream starten
        kameraVideo.src =
            "/video_feed?pose=" + encodeURIComponent(pose)
            + "&versuch_id=" + encodeURIComponent(aktiverVersuch);
        zeigeScreen(kameraScreen);


    } catch (fehler) {
        console.error(fehler);
        alert("Verbindung zu Python fehlgeschlagen.");
    }
}

document.querySelectorAll("[data-pose]").forEach(button => {
    button.addEventListener("click", () => {
        waehlePose(button.dataset.pose);
    });
});

document.querySelector("#beenden-btn").addEventListener("click", () => {
    zeigeScreen(auswahlScreen);
});

document.querySelector("#wiederholen-btn").addEventListener("click", () => {
    waehlePose(aktivePose);
});

document.querySelector("#neue-pose-btn").addEventListener("click", () => {
    zeigeScreen(auswahlScreen);
});


async function aktualisiereFortschritt() {
    // Nur während einer Übung Daten abfragen
    if (kameraScreen.classList.contains("hidden")) {
        return;
    }

    try {
        const antwort = await fetch("/api/status", {
            cache: "no-store"
        });

        if (!antwort.ok) {
            throw new Error("Status konnte nicht geladen werden");
        }

        const daten = await antwort.json();

        // Alte oder fremde Pose ignorieren
        if (
            daten.pose !== aktivePose ||
            daten.versuch_id !== aktiverVersuch
        ) {
            return;
        }

        // Falls wir den Kamerabildschirm inzwischen verlassen haben
        if (kameraScreen.classList.contains("hidden")) {
            return;
        }

        // Text und Fortschritt aktualisieren
        feedbackStatus.textContent = daten.erfolg
            ? "Pose geschafft!"
            : daten.dauer > 0
                ? "Sehr gut! Halte die Position!"
                : "Nimm deine Pose ein";

        feedbackZeit.textContent =
            `${daten.dauer.toFixed(1)} / ${daten.haltezeit.toFixed(1)} s`;

        progressFill.style.width = `${daten.prozent}%`;

        document.querySelector("#pose-progress")
            .setAttribute("aria-valuenow", daten.prozent);

        // Automatisch zum Erfolgsbildschirm wechseln
        if (daten.erfolg) {
            zeigeScreen(erfolgScreen);
        }

    } catch (fehler) {
        console.error("Fortschritt:", fehler);
    }
}

// Alle 200 Millisekunden den aktuellen Fortschritt abrufen
setInterval(aktualisiereFortschritt, 200);
