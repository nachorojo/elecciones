const NOMBRE = { PP: "PP", PSOE: "PSOE", VOX: "Vox", FA: "Frente Amplio", PODEMOS: "Podemos", SALF: "Se Acabó la Fiesta", ERC: "ERC",
  JUNTS: "Junts", EH_BILDU: "EH Bildu", PNV: "PNV", BNG: "BNG", CC: "Coalición Canaria", COMPROMIS: "Compromís",
  NC: "NC-Podemos-IU-Sumar", ADELANTE: "Adelante Andalucía", TERUEL_EXISTE: "Teruel Existe", GBAI: "Geroa Bai", PACMA: "PACMA", OTROS: "Otras" };
const COLOR = { PP: "#1D84CE", PSOE: "#E30713", VOX: "#5BA82B", FA: "#E51C55", PODEMOS: "#6B2E7A", SALF: "#7A5230", ERC: "#E0A020",
  JUNTS: "#00A99D", EH_BILDU: "#7BA21A", PNV: "#0F6B3C", BNG: "#5F93C0", CC: "#C9A400", COMPROMIS: "#D96A2B", NC: "#3C8D5A",
  ADELANTE: "#2AA198", TERUEL_EXISTE: "#4B6B4F", GBAI: "#B0333A", PACMA: "#9BB52B" };
const Q = new URLSearchParams(location.search);
const $ = (s) => document.querySelector(s);
const el = (t, c, x) => { const n = document.createElement(t); if (c) n.className = c; if (x !== undefined) n.textContent = x; return n; };
const dec = (x, d = 1) => Number(x).toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
const num = (x) => Math.round(x).toLocaleString("es-ES", { useGrouping: "always" });
const punto = (f) => { const i = el("i", "p"); i.style.background = COLOR[f] || "#8D98A6"; return i; };
const REFRESCO = 1000 * Math.max(30, Number(Q.get("refresco")) || 120);
function avisarAltura() {
  if (parent === window) return;
  parent.postMessage({ origen: "ondacero-29n", modulo: document.body.dataset.modulo, alto: document.documentElement.scrollHeight }, "*");
  if (location.hash.includes("amp=1")) parent.postMessage({ sentinel: "amp", type: "embed-size", height: document.documentElement.scrollHeight }, "*");
}
addEventListener("load", avisarAltura); addEventListener("resize", avisarAltura);
async function pedir(url) { const r = await fetch(url, { cache: "no-cache" }); if (!r.ok) throw new Error(r.status); return r.json(); }
