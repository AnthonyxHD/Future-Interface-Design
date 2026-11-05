
const auswahlScreen = document.querySelector("#auswahl-screen");
const kameraScreen = document.querySelector("#kamera-screen");
const erfolgScreen = document.querySelector("#erfolg-screen");

const poseTitel = document.querySelector("#aktuelle-pose");

const kameraVideo = document.querySelector("#kamera-video");

let aktivePose = null;

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

        console.log("Python bestätigt:", daten.pose);

        aktivePose = pose;
        poseTitel.textContent = pose;
        kameraVideo.src = "/video_feed";
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

document.querySelector("#test-erfolg-btn").addEventListener("click", () => {
    console.log("Erfolg-Button wurde geklickt!");
    zeigeScreen(erfolgScreen);
});

document.querySelector("#wiederholen-btn").addEventListener("click", () => {
    waehlePose(aktivePose);
});

document.querySelector("#neue-pose-btn").addEventListener("click", () => {
    zeigeScreen(auswahlScreen);
});
