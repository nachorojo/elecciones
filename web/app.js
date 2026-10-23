/* Atlas Electoral — versión estática. Lee data/resultados.json (pipeline/export_web.py).
   Mosaico de provincias y siglas: adaptados de la web local de Mikel Ibáñez (tfm_web). */
const MOSAICO = {
  "15":[1,0],"27":[2,0],"33":[3,0],"39":[4,0],"48":[5,0],"20":[6,0],
  "36":[1,1],"32":[2,1],"24":[3,1],"34":[4,1],"09":[5,1],"01":[6,1],"31":[7,1],"22":[8,1],"25":[9,1],"17":[10,1],
  "49":[2,2],"47":[3,2],"42":[4,2],"26":[5,2],"50":[6,2],"44":[7,2],"08":[9,2],"43":[10,2],
  "37":[2,3],"05":[3,3],"40":[4,3],"19":[5,3],"28":[6,3],"12":[8,3],
  "10":[2,4],"45":[3,4],"16":[4,4],"13":[5,4],"46":[7,4],"07":[9,4],
  "06":[2,5],"41":[3,5],"14":[4,5],"23":[5,5],"02":[6,5],"03":[7,5],
  "21":[2,6],"11":[3,6],"29":[4,6],"18":[5,6],"30":[6,6],"04":[7,6],
  "38":[0,7],"35":[1,7],"51":[3,8],"52":[4,8]
};
const SIGLAS = {
  "01":"VI","02":"AB","03":"A","04":"AL","05":"AV","06":"BA","07":"IB","08":"B","09":"BU",
  "10":"CC","11":"CA","12":"CS","13":"CR","14":"CO","15":"C","16":"CU","17":"GI","18":"GR",
  "19":"GU","20":"SS","21":"H","22":"HU","23":"J","24":"LE","25":"L","26":"LO","27":"LU",
  "28":"M","29":"MA","30":"MU","31":"NA","32":"OU","33":"O","34":"P","35":"GC","36":"PO",
  "37":"SA","38":"TF","39":"S","40":"SG","41":"SE","42":"SO","43":"T","44":"TE","45":"TO",
  "46":"V","47":"VA","48":"BI","49":"ZA","50":"Z","51":"CE","52":"ML"
};
const COLOR = {
  PP: "#1D84CE", PSOE: "#E30713", VOX: "#5BA82B", PODEMOS_SUMAR: "#6B2E7A", CS: "#EB6109",
  IU: "#A61B29", UPYD: "#E4007C", ERC: "#E0A020", CIU_JXCAT: "#00A99D", PNV: "#0F6B3C",
  EH_BILDU: "#7BA21A", BNG: "#5F93C0", CC: "#C9A400", COMPROMIS: "#D96A2B", OTROS: "#8D98A6"
};
const ETIQUETA = {
  PP: "PP", PSOE: "PSOE", VOX: "Vox", PODEMOS_SUMAR: "Podemos / Sumar", CS: "Cs", IU: "IU", UPYD: "UPyD",
  ERC: "ERC", CIU_JXCAT: "CiU / Junts", PNV: "PNV", EH_BILDU: "EH Bildu", BNG: "BNG", CC: "CC",
  COMPROMIS: "Compromís", OTROS: "Otras"
};

const $ = (s) => document.querySelector(s);
const num = (x) => Math.round(x).toLocaleString("es-ES");
const dec = (x, d = 2) => x.toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
const color = (f) => COLOR[f] || COLOR.OTROS;
const el = (tag, cls, texto) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (texto !== undefined) n.textContent = texto;
  return n;
};

let DATOS = null;
let seleccion = null; // código de provincia, o null para España

const actual = () => DATOS.elecciones.find((e) => e.id === $("#eleccion").value);
const ganador = (ambito) => ambito.partidos.reduce((a, b) => (b.v > a.v ? b : a));

function pintarMapa() {
  const e = actual();
  const mapa = $("#mapa");
  mapa.replaceChildren();
  const metrica = $("#metrica").value;
  const parts = Object.values(e.provincias).map((p) => p.participacion_residentes);
  const [min, max] = [Math.min(...parts), Math.max(...parts)];
  for (const [cod, [x, y]] of Object.entries(MOSAICO)) {
    const prov = e.provincias[cod];
    if (!prov) continue;
    const b = el("button", "casilla" + (cod === seleccion ? " activa" : ""), SIGLAS[cod]);
    b.type = "button";
    b.style.gridColumn = x + 1;
    b.style.gridRow = y + 1;
    const g = ganador(prov);
    if (metrica === "ganador") {
      b.style.background = color(g.f);
    } else {
      const t = (prov.participacion_residentes - min) / (max - min || 1);
      b.style.background = `hsl(215 70% ${88 - 52 * t}%)`;
      b.style.color = t > 0.45 ? "#fff" : "#12171f";
      b.style.textShadow = "none";
    }
    b.title = `${prov.nombre}: ${g.s} (${dec(100 * g.v / prov.validos, 1)} %) · participación ${dec(prov.participacion_residentes, 1)} %`;
    b.setAttribute("aria-label", b.title);
    b.addEventListener("click", () => { seleccion = cod; pintar(); });
    mapa.appendChild(b);
  }
  const ley = $("#leyenda");
  ley.replaceChildren();
  if (metrica === "ganador") {
    const usados = [...new Set(Object.values(e.provincias).map((p) => ganador(p).f))];
    usados.forEach((f) => {
      const s = el("span");
      const i = el("i"); i.style.background = color(f);
      s.append(i, ETIQUETA[f] || f);
      ley.appendChild(s);
    });
  } else {
    ley.textContent = `Participación de residentes: de ${dec(min, 1)} % (claro) a ${dec(max, 1)} % (oscuro).`;
  }
}

function pintarDetalle() {
  const e = actual();
  const a = seleccion ? e.provincias[seleccion] : e.nacional;
  $("#titulo").textContent = a.nombre;
  $("#volver").hidden = !seleccion;
  $("#fecha").textContent = `Elecciones generales del ${e.fecha} · ${a.escanos_total} escaños en juego`;
  const r = $("#resumen");
  r.replaceChildren();
  [[dec(a.participacion_residentes, 2) + " %", "participación (residentes)"],
   [num(a.censo - a.cera.censo), "electores residentes"],
   [num(a.validos), "votos válidos"],
   [num(a.cera.votos), "votos CERA (exterior)"]].forEach(([v, l]) => {
    const d = el("div", "dato");
    d.append(el("b", null, v), el("span", null, l));
    r.appendChild(d);
  });
  const lista = $("#partidos");
  lista.replaceChildren();
  const tope = Math.max(...a.partidos.map((p) => p.v));
  a.partidos.slice(0, 12).forEach((p) => {
    const f = el("div", "fila");
    const barra = el("div", "barra");
    const s = el("span"); s.style.width = `${100 * p.v / tope}%`; s.style.background = color(p.f);
    barra.appendChild(s);
    const esc = el("div", "esc", String(p.e));
    esc.append(" ", el("small", null, "esc."));
    f.append(el("div", null, p.s), barra,
             el("div", "cifras", `${num(p.v)} · ${dec(100 * p.v / a.validos, 2)} %`), esc);
    lista.appendChild(f);
  });
  const mostrados = a.partidos.slice(0, 12);
  const resto = a.validos - mostrados.reduce((t, p) => t + p.v, 0) - a.blancos;
  $("#otros").textContent =
    `Resto de candidaturas: ${num(resto)} votos · en blanco: ${num(a.blancos)} (${dec(100 * a.blancos / a.validos, 2)} % de los válidos) · nulos: ${num(a.nulos)}.`;
  const h = $("#historia");
  h.replaceChildren();
  DATOS.elecciones.forEach((x) => {
    const ambito = seleccion ? x.provincias[seleccion] : x.nacional;
    const g = ganador(ambito);
    const c = el("span", "chip" + (x.id === e.id ? " actual" : ""), `${x.id}: ${g.s}`);
    c.style.background = color(g.f);
    h.appendChild(c);
  });
}

function pintar() { pintarMapa(); pintarDetalle(); }

async function inicio() {
  DATOS = await (await fetch("data/resultados.json")).json();
  const sel = $("#eleccion");
  DATOS.elecciones.forEach((e) => sel.appendChild(Object.assign(el("option"), { value: e.id, textContent: e.fecha })));
  sel.value = "2023";
  sel.addEventListener("change", pintar);
  $("#metrica").addEventListener("change", pintarMapa);
  $("#volver").addEventListener("click", () => { seleccion = null; pintar(); });
  pintar();
}
inicio().catch((err) => { document.querySelector("main").prepend(el("p", "aviso", "No se pudieron cargar los datos: " + err.message)); });
