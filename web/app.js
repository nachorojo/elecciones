/* Atlas Electoral — versión estática. Lee data/resultados.json (pipeline/export_web.py).
   Siglas de provincia: adaptadas de la web local de Mikel Ibáñez (tfm_web). */
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
  EH_BILDU: "#7BA21A", BNG: "#5F93C0", CC: "#C9A400", COMPROMIS: "#D96A2B", OTROS: "#8D98A6",
  // Espacios del 29N (pipeline/convocatoria_29n.py)
  FA: "#E51C55", PODEMOS: "#6B2E7A", SALF: "#7A5230", JUNTS: "#00A99D", NC: "#3C8D5A", ADELANTE: "#2AA198",
  TERUEL_EXISTE: "#4B6B4F", GBAI: "#B0333A", UPN: "#2A5C9A", PACMA: "#9BB52B", CUP: "#D8C400"
};
const ETIQUETA = {
  PP: "PP", PSOE: "PSOE", VOX: "Vox", PODEMOS_SUMAR: "Podemos / Sumar", CS: "Cs", IU: "IU", UPYD: "UPyD",
  ERC: "ERC", CIU_JXCAT: "CiU / Junts", PNV: "PNV", EH_BILDU: "EH Bildu", BNG: "BNG", CC: "CC",
  COMPROMIS: "Compromís", OTROS: "Otras"
};
// Familia de 2023 -> espacio de 2026 con el que se compara (solo donde hay continuidad clara).
const ESPACIO_2023 = { PP: "PP", UPN: "PP", PSOE: "PSOE", VOX: "VOX", ERC: "ERC", CIU_JXCAT: "JUNTS",
  EH_BILDU: "EH_BILDU", PNV: "PNV", BNG: "BNG", CC: "CC" };
const DEMO = new URLSearchParams(location.search).has("demo");
// ?simulacro: último envío del simulacro de Interior del 18-N-2026 (datos ficticios, rotulados), para ver la página con recuento.
const SIMU = new URLSearchParams(location.search).has("simulacro");
const CFG = Object.assign({ vivo: "data/vivo_29n.json", refresco: 30 }, window.CONFIG || {});

const $ = (s) => document.querySelector(s);
const num = (x) => Math.round(x).toLocaleString("es-ES", { useGrouping: "always" });
const dec = (x, d = 2) => x.toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
const color = (f) => COLOR[f] || COLOR.OTROS;
const el = (tag, cls, texto) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (texto !== undefined) n.textContent = texto;
  return n;
};

/* Mapa de provincias (data/provincias.js, generado por pipeline/export_provincias.py). `estilo(cod)` devuelve
   {fill, title, activa} o null si la provincia no tiene datos; `alPulsar(cod)` recibe el clic. Canarias va en un recuadro. */
function mapaProvincias(cont, estilo, alPulsar) {
  const M = window.MAPA_PROV, NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${M.ancho} ${M.alto}`);
  svg.setAttribute("class", "mapa-prov");
  const marco = document.createElementNS(NS, "rect");
  [["x", M.canarias[0]], ["y", M.canarias[1]], ["width", M.canarias[2]], ["height", M.canarias[3]], ["class", "marco-canarias"]]
    .forEach(([k, v]) => marco.setAttribute(k, v));
  svg.appendChild(marco);
  let activa = null;
  const pieza = (cod, forma) => {
    const e = estilo(cod) || { fill: "var(--superficie-alta)", title: SIGLAS[cod] };
    forma.setAttribute("fill", e.fill);
    forma.setAttribute("class", "prov" + (e.activa ? " activa" : ""));
    forma.setAttribute("tabindex", "0");
    forma.setAttribute("role", "button");
    forma.setAttribute("aria-label", e.title);
    const t = document.createElementNS(NS, "title");
    t.textContent = e.title;
    forma.appendChild(t);
    forma.addEventListener("click", () => alPulsar(cod));
    forma.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); alPulsar(cod); } });
    if (e.activa) activa = forma; else svg.appendChild(forma);
  };
  for (const [cod, d] of Object.entries(M.p)) {
    if (M.puntos[cod]) continue;          // Ceuta y Melilla: solo el punto (su contorno no se ve a esta escala)
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", d);
    pieza(cod, path);
  }
  for (const [cod, [x, y]] of Object.entries(M.puntos)) {
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", x); c.setAttribute("cy", y); c.setAttribute("r", 6);
    pieza(cod, c);
  }
  if (activa) svg.appendChild(activa);   // la seleccionada, encima, para que se vea su borde
  cont.replaceChildren(svg);
}

let DATOS = null;
let seleccion = null; // código de provincia, o null para España

const actual = () => DATOS.elecciones.find((e) => e.id === $("#eleccion").value);
const ganador = (ambito) => ambito.partidos.reduce((a, b) => (!a || b.v > a.v ? b : a), null);
const enVivo = (e) => e.id === "2026";

/* Escaños por partido en dos anillos: fuera la convocatoria elegida, dentro la anterior. */
function hemiciclo(e, previa) {
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 320 172");
  svg.setAttribute("role", "img");
  const arco = (r1, r2, a0, a1) => {
    const pt = (r, a) => `${160 - r * Math.cos(a)},${160 - r * Math.sin(a)}`;
    const g = a1 - a0 > Math.PI ? 1 : 0;
    return `M${pt(r2, a0)}A${r2},${r2} 0 ${g} 1 ${pt(r2, a1)}L${pt(r1, a1)}A${r1},${r1} 0 ${g} 0 ${pt(r1, a0)}Z`;
  };
  const texto = (x, y, t, cls) => {
    const n = document.createElementNS(NS, "text");
    n.setAttribute("x", x); n.setAttribute("y", y); n.setAttribute("text-anchor", "middle");
    if (cls) n.setAttribute("class", cls);
    n.textContent = t;
    svg.appendChild(n);
  };
  const anillo = (ambito, r1, r2) => {
    const con = ambito.partidos.filter((p) => p.e > 0).sort((a, b) => b.e - a.e);
    const total = ambito.escanos_total;
    let acum = 0;
    con.forEach((p) => {
      const a0 = Math.PI * acum / total, a1 = Math.PI * (acum + p.e) / total;
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", arco(r1, r2, a0, a1));
      path.setAttribute("fill", color(p.f));
      path.setAttribute("stroke", "var(--superficie)");
      path.setAttribute("stroke-width", ".6");
      const t = document.createElementNS(NS, "title");
      t.textContent = `${p.s}: ${p.e}`;
      path.appendChild(t);
      svg.appendChild(path);
      if (p.e >= total * 0.06) {
        const m = (a0 + a1) / 2, r = (r1 + r2) / 2;
        texto(160 - r * Math.cos(m), 160 - r * Math.sin(m) + 4, String(p.e), "hemi-num");
      }
      acum += p.e;
    });
    if (!con.length) {
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", arco(r1, r2, 0, Math.PI));
      path.setAttribute("fill", "var(--superficie-alta)");
      svg.appendChild(path);
    }
  };
  anillo(e.nacional, 108, 152);
  if (previa) anillo(previa.nacional, 62, 100);
  const l = document.createElementNS(NS, "line");
  l.setAttribute("x1", 160); l.setAttribute("x2", 160); l.setAttribute("y1", 4); l.setAttribute("y2", 104);
  l.setAttribute("class", "hemi-mayoria");
  svg.appendChild(l);
  texto(160, 132, "Mayoría absoluta", "hemi-etq");
  texto(160, 147, String(Math.floor(e.nacional.escanos_total / 2) + 1), "hemi-may");
  texto(160, 168, `${e.nacional.escanos_total} escaños`, "hemi-etq");
  texto(22, 170, e.id.slice(0, 4), "hemi-etq");
  if (previa) texto(70, 170, previa.id.slice(0, 4), "hemi-etq");
  svg.setAttribute("aria-label", `Reparto de escaños de ${e.id}` + (previa ? ` (anillo interior: ${previa.id})` : ""));
  return svg;
}

function pintarMapa() {
  const e = actual();
  const metrica = $("#metrica").value;
  const parts = Object.values(e.provincias).map((p) => p.participacion_residentes);
  const [min, max] = [Math.min(...parts), Math.max(...parts)];
  mapaProvincias($("#mapa"), (cod) => {
    const prov = e.provincias[cod];
    if (!prov) return null;
    const g = ganador(prov);
    if (!g) return { fill: "var(--superficie-alta)", activa: cod === seleccion, title: `${prov.nombre}: sin datos todavía · ${prov.escanos_total} escaños` };
    let fill;
    if (metrica === "ganador") {
      // Color del partido; cuanto más pálido, más ajustada la ventaja de su cuota de voto.
      const t = Math.min(1, Math.max(0, (100 * g.v / prov.validos - 25) / 30));
      fill = `color-mix(in srgb, ${color(g.f)} ${Math.round(40 + 60 * t)}%, var(--superficie-alta))`;
    } else {
      fill = `hsl(215 75% ${90 - 58 * (prov.participacion_residentes - min) / (max - min || 1)}%)`;
    }
    return { fill, activa: cod === seleccion,
             title: `${prov.nombre}: ${g.s} (${dec(100 * g.v / prov.validos, 1)} %) · participación ${dec(prov.participacion_residentes, 1)} %` };
  }, (cod) => { seleccion = cod; pintar(); });
  const ley = $("#leyenda");
  ley.replaceChildren();
  if (metrica === "ganador") {
    const usados = [...new Set(Object.values(e.provincias).map((p) => ganador(p)).filter(Boolean).map((g) => g.f))];
    ley.appendChild(el("span", null, "Color = candidatura más votada; más pálido = ventaja más ajustada."));
    usados.forEach((f) => {
      const s = el("span");
      const i = el("i"); i.style.background = color(f);
      s.append(i, ETIQUETA[f] || f);
      ley.appendChild(s);
    });
  } else {
    const barra = el("span", "gradiente");
    ley.append(`Participación de residentes: ${dec(min, 1)} %`, barra, `${dec(max, 1)} %`);
  }
}

function pintarDetalle() {
  const e = actual();
  const a = seleccion ? e.provincias[seleccion] : e.nacional;
  $("#titulo").textContent = a.nombre;
  $("#volver").hidden = !seleccion;
  const vivo = enVivo(e);
  $("#fecha").textContent = `Elecciones generales del ${e.fecha} · ${a.escanos_total} escaños en juego` +
    (vivo ? (a.escrutado > 0 ? ` · recuento provisional${e.hora ? ", actualizado a las " + e.hora : ""}`
                             : " · el escrutinio empieza a las 20:00") : "");
  $("#aviso-prueba").hidden = !(vivo && e.prueba);
  $("#aviso-simulacro").hidden = !(vivo && e.simulacro);
  const hemi = $("#hemiciclo");
  hemi.replaceChildren();
  hemi.hidden = !!seleccion;
  if (!seleccion) hemi.appendChild(hemiciclo(e, DATOS.elecciones[DATOS.elecciones.indexOf(e) - 1]));
  const r = $("#resumen");
  r.replaceChildren();
  // 29N antes del escrutinio: constitución de mesas y avances de participación (14:00 y 18:00), si ya han llegado.
  const av = vivo && !(a.escrutado > 0) && a.avances ? a.avances : null;
  const horas = e.simulacro ? ["1.er avance", "2.º avance"] : ["a las 14:00", "a las 18:00"];
  (av
    ? [[a.mesas && a.mesas.total ? dec(100 * a.mesas.constituidas / a.mesas.total, 1) + " %" : "—", "mesas constituidas"],
       [av[0] > 0 ? dec(av[0], 2) + " %" : "—", "participación " + horas[0]],
       [av[1] > 0 ? dec(av[1], 2) + " %" : "—", "participación " + horas[1]],
       [num(a.censo), "electores"]]
    : vivo
    ? [[dec(a.escrutado, 2) + " %", "escrutado (censo)"],
       [a.escrutado > 0 ? dec(a.participacion_residentes, 2) + " %" : "—", "participación"],
       [num(a.validos), "votos válidos contados"],
       [num(a.censo), "electores"]]
    : [[dec(a.participacion_residentes, 2) + " %", "participación (residentes)"],
       [num(a.censo - a.cera.censo), "electores residentes"],
       [num(a.validos), "votos válidos"],
       [num(a.cera.votos), "votos CERA (exterior)"]]).forEach(([v, l]) => {
    const d = el("div", "dato");
    d.append(el("b", null, v), el("span", null, l));
    r.appendChild(d);
  });
  const lista = $("#partidos");
  lista.replaceChildren();
  const tope = Math.max(1, ...a.partidos.map((p) => p.v));
  // 29N: diferencia de escaños con 2023, solo para espacios con continuidad (PP incluye a UPN, ahora en coalición).
  const antes = {};
  if (vivo) {
    const e23 = DATOS.elecciones.find((x) => x.id === "2023");
    (seleccion ? e23.provincias[seleccion] : e23.nacional).partidos.forEach((p) => {
      const esp = ESPACIO_2023[p.f];
      if (esp) antes[esp] = (antes[esp] || 0) + p.e;
    });
  }
  // Mientras queden escaños sin asignar (provincias sin recuento) no se compara con 2023: la diferencia engañaría.
  const completo = a.partidos.reduce((t, p) => t + p.e, 0) >= a.escanos_total;
  const comparables = new Set(completo ? Object.values(ESPACIO_2023) : []);
  const filas = vivo ? [...a.partidos].sort((x, y) => y.e - x.e || y.v - x.v) : a.partidos;
  if (!filas.length) lista.appendChild(el("p", "nota", "Todavía no hay votos contados. " + (seleccion ? "" : "Mientras tanto, el anillo interior muestra el reparto de 2023.")));
  filas.slice(0, vivo ? 16 : 12).forEach((p) => {
    const f = el("div", "fila");
    const barra = el("div", "barra");
    const s = el("span"); s.style.width = `${100 * p.v / tope}%`; s.style.background = color(p.f);
    barra.appendChild(s);
    const esc = el("div", "esc", String(p.e));
    esc.append(" ", el("small", null, "esc."));
    if (vivo && comparables.has(p.f)) {
      const d = p.e - (antes[p.f] || 0);
      esc.append(" ", el("small", d > 0 ? "sube" : d < 0 ? "baja" : null, d > 0 ? `▲${d}` : d < 0 ? `▼${-d}` : "="));
    }
    const nombre = el("div", null, p.s);
    if (p.incluye) nombre.title = "Incluye: " + p.incluye.join(", ");
    f.append(nombre, barra,
             el("div", "cifras", `${num(p.v)} · ${dec(100 * p.v / a.validos, 2)} %`), esc);
    lista.appendChild(f);
  });
  const mostrados = filas.slice(0, vivo ? 16 : 12);
  const resto = a.validos - mostrados.reduce((t, p) => t + p.v, 0) - a.blancos;
  $("#otros").textContent = !a.validos ? "" :
    `Resto de candidaturas: ${num(resto)} votos · en blanco: ${num(a.blancos)} (${dec(100 * a.blancos / a.validos, 2)} % de los válidos) · nulos: ${num(a.nulos)}.` +
    (vivo ? " ▲▼: diferencia de escaños con 2023 (PP se compara con PP + UPN; el espacio de Sumar concurre dividido y no se compara)." : "");
  // Último escaño de la provincia: quién lo tiene, quién va detrás y cuántos votos le faltan (dato de Interior).
  const ult = $("#ultimo");
  ult.hidden = true;
  if (vivo && seleccion && a.escrutado > 0 && a.ultimo && Number(a.ultimo.ultima) > 0) {
    const sig = (c) => (a.partidos.find((p) => Number(p.c) === Number(c)) || { s: "otra candidatura" }).s;
    ult.replaceChildren(el("strong", null, "Último escaño: "), `lo tiene ${sig(a.ultimo.ultima)}.` +
      (Number(a.ultimo.proxima) > 0 ? ` El siguiente sería para ${sig(a.ultimo.proxima)}, que necesita ${num(a.ultimo.faltan)} votos más.` : ""));
    ult.hidden = false;
  }
  const h = $("#historia");
  h.replaceChildren();
  DATOS.elecciones.forEach((x) => {
    const ambito = seleccion ? x.provincias[seleccion] : x.nacional;
    const g = ganador(ambito);
    if (!g) return;
    const c = el("span", "chip" + (x.id === e.id ? " actual" : ""), `${x.id}: ${g.s}`);
    c.style.background = color(g.f);
    h.appendChild(c);
  });
}

let vista = "prov"; // "prov" (mosaico de provincias), "mun" (municipios), "sec" (secciones) o "sim" (simulador 29N)

function pintar() {
  if (vista === "sim") { Simulador.pintar(); return; }
  if (vista === "mun") { Municipal.pintar(); return; }
  if (vista === "sec") { Seccion.pintar(); return; }
  pintarMapa();
  pintarDetalle();
}

function cambiarVista(v) {
  vista = v;
  $("#vista-prov").classList.toggle("activa", v === "prov");
  $("#vista-mun").classList.toggle("activa", v === "mun");
  $("#vista-sec").classList.toggle("activa", v === "sec");
  $("#vista-sim").classList.toggle("activa", v === "sim");
  document.querySelector(".rejilla").classList.toggle("vista-mun", v === "mun" || v === "sec");
  document.querySelector(".rejilla").classList.toggle("vista-sim", v === "sim");
  $("#bloque-sim").hidden = v !== "sim";
  if (v !== "prov") { $("#hemiciclo").hidden = true; $("#aviso-prueba").hidden = true; $("#aviso-simulacro").hidden = true; $("#ultimo").hidden = true; }
  $("#aviso-sim").hidden = v !== "sim";
  $("#aviso-datos").hidden = v === "sim";
  $("#etq-eleccion").hidden = v === "sim";
  $("#leyenda").hidden = v === "sim";
  $("#titulo-historia").hidden = v === "sim";
  $("#historia").hidden = v === "sim";
  $("#bloque-prov").hidden = v !== "prov";
  $("#bloque-mun").hidden = v !== "mun";
  $("#bloque-sec").hidden = v !== "sec";
  if (v === "sec" && !["2019a", "2019b", "2023"].includes($("#eleccion").value)) $("#eleccion").value = "2023";
  if (v === "mun" && $("#eleccion").value === "2026") $("#eleccion").value = "2023";
  if (v === "sim") Simulador.iniciar().then(pintar);
  else if (v === "mun") Municipal.iniciar().then(pintar);
  else if (v === "sec") Seccion.iniciar().then(pintar);
  else pintar();
}

/* 29N: data/vivo_29n.json (pipeline/escrutinio_29n.py); con ?demo, el fichero de PRUEBA; con ?simulacro, el del
   simulacro de Interior. Se vuelve a pedir cada 30 s. */
async function cargarVivo(primera) {
  try {
    const r = await fetch(DEMO ? "data/demo_29n.json" : SIMU ? "data/simulacro_29n.json" : CFG.vivo, { cache: "no-store" });
    if (!r.ok) return;
    const e = await r.json();
    const i = DATOS.elecciones.findIndex((x) => x.id === "2026");
    if (i >= 0) DATOS.elecciones[i] = e; else DATOS.elecciones.push(e);
    const sel = $("#eleccion");
    if (primera) {
      sel.appendChild(Object.assign(el("option"), { value: e.id, textContent: e.fecha }));
      if (e.nacional.escrutado > 0) sel.value = e.id;
    }
    if (sel.value === "2026") pintar();
  } catch (err) { /* sin HTTP (file://) o sin fichero: no hay 29N en el desplegable */ }
}

async function inicio() {
  DATOS = window.RESULTADOS || await (await fetch("data/resultados.json")).json();
  const sel = $("#eleccion");
  DATOS.elecciones.forEach((e) => sel.appendChild(Object.assign(el("option"), { value: e.id, textContent: e.fecha })));
  sel.value = "2023";
  sel.addEventListener("change", () => {
    // El 29N solo existe, de momento, a nivel de España y provincias.
    if (sel.value === "2026" && vista !== "prov" && vista !== "sim") cambiarVista("prov"); else pintar();
  });
  await cargarVivo(true);
  setInterval(() => { if (sel.value === "2026" && !document.hidden) cargarVivo(false); }, 1000 * Math.max(10, CFG.refresco));
  $("#metrica").addEventListener("change", pintar);
  $("#volver").addEventListener("click", () => { seleccion = null; Municipal.limpiar(); Seccion.limpiar(); Simulador.limpiar(); pintar(); });
  $("#vista-sim").addEventListener("click", () => cambiarVista("sim"));
  $("#vista-sec").addEventListener("click", () => cambiarVista("sec"));
  $("#vista-prov").addEventListener("click", () => cambiarVista("prov"));
  $("#vista-mun").addEventListener("click", () => cambiarVista("mun"));
  // La entrada «Simulador» del menú abre la página con ?simulador: se entra directamente en esa vista.
  if (new URLSearchParams(location.search).has("simulador")) cambiarVista("sim"); else pintar();
}
inicio().catch((err) => { document.querySelector("main").prepend(el("p", "aviso", "No se pudieron cargar los datos (" + err.message + "). Comprueba que existe web/data/resultados.js.")); });
