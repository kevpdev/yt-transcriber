(function () {
  const root = document.documentElement;
  const button = document.getElementById("theme");
  const sync = () => button.setAttribute("aria-pressed", String(root.classList.contains("dark")));
  const hasChoice = () => { try { return localStorage.getItem(THEME_KEY) !== null; } catch { return false; } };
  sync();
  button.addEventListener("click", () => {
    const dark = !root.classList.contains("dark");
    root.classList.toggle("dark", dark);
    try { localStorage.setItem(THEME_KEY, dark ? "dark" : "light"); } catch {}
    sync();
  });
  systemDark.addEventListener("change", (ev) => {
    if (hasChoice()) return;
    root.classList.toggle("dark", ev.matches);
    sync();
  });
})();

const $ = (id) => document.getElementById(id);
const STAGES = { queued: "En attente", downloading: "Téléchargement de l'audio", transcribing: "Transcription", extracting: "Extraction des images" };
let timer = null;
let finished = null;

function formatTime(seconds) {
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

function timedText(segments) {
  return segments.map((s) => `[${formatTime(s.start)}] ${s.text}`).join("\n");
}

function render() {
  if (!finished) return;
  const timed = $("timestamps").getAttribute("aria-pressed") === "true";
  $("out").value = timed ? timedText(finished.segments) : finished.text;
}

function setBusy(busy) { $("go").disabled = busy; $("frames").disabled = busy; }
function showError(msg) { $("error").textContent = msg || ""; }

async function readError(resp) {
  try { return (await resp.json()).detail || resp.statusText; } catch { return resp.statusText; }
}

const KEY = "yt-transcriber-job";
const MAX_RETRIES = 5;

function remember(id) { try { id ? localStorage.setItem(KEY, id) : localStorage.removeItem(KEY); } catch {} }
function remembered() { try { return localStorage.getItem(KEY); } catch { return null; } }

function stop(message) {
  remember(null);
  if (message) showError(message);
  setBusy(false);
}

async function poll(id, failures = 0) {
  let job;
  try {
    const resp = await fetch(`/jobs/${id}`);
    if (resp.status === 404) {
      $("status").textContent = "";
      return stop("Ce job n'existe plus, le serveur a sûrement redémarré. Relance la transcription.");
    }
    if (!resp.ok) throw new Error(await readError(resp));
    job = await resp.json();
  } catch (e) {
    if (failures + 1 >= MAX_RETRIES) {
      $("status").textContent = "";
      showError("Le serveur ne répond pas : " + e.message + ". Recharge la page pour reprendre le job.");
      return setBusy(false);
    }
    $("status").textContent = "Connexion perdue, nouvelle tentative…";
    timer = setTimeout(() => poll(id, failures + 1), 2000);
    return;
  }
  showError("");
  if (job.stage === "done") {
    finished = job;
    render();
    $("status").textContent = "Terminé.";
    return stop();
  }
  if (job.stage === "error") {
    $("status").textContent = "";
    return stop(job.error);
  }
  const pct = job.stage === "transcribing" ? ` · ${Math.round(job.progress * 100)} %` : "";
  $("status").textContent = (STAGES[job.stage] || job.stage) + pct;
  timer = setTimeout(() => poll(id), 2000);
}

$("form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  clearTimeout(timer);
  showError("");
  finished = null;
  $("out").value = "";
  setBusy(true);
  try {
    const resp = await fetch("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: $("url").value, level: $("frames").checked ? "frames" : "text" }),
    });
    if (!resp.ok) {
      showError(await readError(resp));
      setBusy(false);
      return;
    }
    $("status").textContent = "En attente";
    const { id } = await resp.json();
    remember(id);
    poll(id);
  } catch (e) {
    showError("Le serveur ne répond pas : " + e.message);
    setBusy(false);
  }
});

const resumed = remembered();
if (resumed) {
  setBusy(true);
  $("status").textContent = "Reprise du job en cours…";
  poll(resumed);
}

$("timestamps").addEventListener("click", () => {
  const pressed = $("timestamps").getAttribute("aria-pressed") === "true";
  $("timestamps").setAttribute("aria-pressed", String(!pressed));
  render();
});

$("copy").addEventListener("click", async () => {
  const text = $("out").value;
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    $("out").select();
    document.execCommand("copy");
  }
  $("copy").title = "Copié";
  $("status").textContent = "Texte copié dans le presse-papiers.";
  setTimeout(() => { $("copy").title = "Copier"; }, 1500);
});
