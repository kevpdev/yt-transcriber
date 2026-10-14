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
let current = null;
let cancelling = false;
let jobUrl = "";

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

function setBusy(busy) {
  $("go").disabled = busy;
  $("go-frames").disabled = busy;
  $("cancel").hidden = !busy;
  $("cancel").disabled = false;
}
function showVideo(job) {
  if (!job || !job.title) {
    $("video").textContent = "";
    return;
  }
  const parts = [job.title, job.channel, job.duration != null ? formatTime(job.duration) : null];
  $("video").textContent = parts.filter(Boolean).join(" · ");
}
function showError(msg) { $("error").textContent = msg || ""; }

async function readError(resp) {
  try { return (await resp.json()).detail || resp.statusText; } catch { return resp.statusText; }
}

const KEY = "yt-transcriber-job";
const MAX_RETRIES = 5;

function remember(id) { try { id ? localStorage.setItem(KEY, id) : localStorage.removeItem(KEY); } catch {} }
function remembered() { try { return localStorage.getItem(KEY); } catch { return null; } }

function stop(message) {
  const mine = current;
  current = null;
  cancelling = false;
  // Another tab may have queued its own job under the same key: only clear our own id.
  if (remembered() === mine) remember(null);
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
  showVideo(job);
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
  $("status").textContent = cancelling ? "Annulation…" : (STAGES[job.stage] || job.stage) + pct;
  timer = setTimeout(() => poll(id), 2000);
}

$("form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  // Enter in the URL field submits with the first button, so it stays text only.
  const level = ev.submitter?.id === "go-frames" ? "frames" : "text";
  clearTimeout(timer);
  showError("");
  finished = null;
  cancelling = false;
  $("out").value = "";
  showVideo(null);
  jobUrl = $("url").value;
  setBusy(true);
  try {
    const resp = await fetch("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: jobUrl, level }),
    });
    if (!resp.ok) {
      showError(await readError(resp));
      setBusy(false);
      return;
    }
    $("status").textContent = "En attente";
    const { id } = await resp.json();
    current = id;
    remember(id);
    poll(id);
  } catch (e) {
    showError("Le serveur ne répond pas : " + e.message);
    setBusy(false);
  }
});

const resumed = remembered();
if (resumed) {
  current = resumed;
  setBusy(true);
  $("status").textContent = "Reprise du job en cours…";
  poll(resumed);
}

$("cancel").addEventListener("click", async () => {
  if (!current) return;
  $("cancel").disabled = true;
  try {
    const resp = await fetch(`/jobs/${current}/cancel`, { method: "POST" });
    // A 404 or 409 means the job is gone or finished: the polling shows the final state.
    // The job may have ended while the request was in flight: keep its final status.
    if (resp.ok && current) {
      cancelling = true;
      $("status").textContent = "Annulation…";
    }
  } catch {
    $("cancel").disabled = false;
  }
});

$("timestamps").addEventListener("click", () => {
  const pressed = $("timestamps").getAttribute("aria-pressed") === "true";
  $("timestamps").setAttribute("aria-pressed", String(!pressed));
  render();
});

function fileName(title) {
  const clean = (title || "").replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_").trim();
  return (clean || "transcription") + ".txt";
}

$("download").addEventListener("click", () => {
  const text = $("out").value;
  if (!text) return;
  const title = finished?.title || jobUrl;
  const blob = new Blob([title ? `${title}\n${text}` : text], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = fileName(finished?.title);
  link.click();
  // Revoked on the next tick: some browsers read the blob after click() returns.
  setTimeout(() => URL.revokeObjectURL(link.href), 0);
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
