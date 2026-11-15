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

let META = null;
let CONTEXTO = {};
let HISTORIAL = [];
let ESCENARIO_BASE = null;

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const dec = (x, d = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? "—"
    : x.toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
const ent = (x) => x === null || x === undefined ? "—" : Math.round(x).toLocaleString("es-ES");

function negrita(t) {
  return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

async function pedir(ruta, opciones) {
  const r = await fetch(ruta, opciones);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

/* ---------- arranque ---------- */

async function inicio() {
  META = await pedir("/api/estado");
  $("#conteo").textContent =
    `${ent(META.n_mesas)} mesas · ${ent(META.n_municipios)} municipios · 10 convocatorias`;
  pintarEstadoLlm();
  const sel = $("#ex-eleccion");
  META.elecciones.forEach((e) => {
    const o = document.createElement("option");
    o.value = e.clave; o.textContent = e.etiqueta;
    sel.appendChild(o);
  });
  sel.value = "2023";
  sel.addEventListener("change", cargarMapa);
  $("#ex-metrica").addEventListener("change", cargarMapa);
  pintarSugerencias();
  cargarMapa();
  mostrarDetalle("nacional", null);
  saludo();
}

function pintarEstadoLlm() {
  const e = $("#estado-llm");
  if (META.llm_disponible) {
    e.className = "insignia activa";
    e.textContent = `modelo ${META.modelo}`;
  } else {
    e.className = "insignia inactiva";
    e.textContent = "sin modelo · intérprete de reglas";
    e.title = META.error || "";
  }
}

const SUGERENCIAS = [
  "¿Quién ganó en Sevilla en 2011?",
  "Participación en el País Vasco en 2023",
  "¿Dónde sacó más VOX en 2023?",
  "Evolución de Bilbao",
  "Compara Madrid y Barcelona en 2023",
  "Mesas de Segovia en 2023",
  "Provincias con menos participación en 2016",
  "¿Quién ganará en 2027?"
];

function pintarSugerencias() {
  const c = $("#sugerencias");
  c.innerHTML = "";
  SUGERENCIAS.forEach((s) => {
    const b = document.createElement("button");
    b.className = "sugerencia"; b.textContent = s; b.type = "button";
    b.onclick = () => { $("#pregunta").value = s; $("#formulario").requestSubmit(); };
    c.appendChild(b);
  });
}

function saludo() {
  burbuja("bot", `<div class="texto">Pregúntame por cualquier convocatoria entre
    <strong>1996 y 2023</strong>, a nivel de país, comunidad, provincia, municipio o incluso
    mesa electoral. Las cifras salen siempre de la base de datos, nunca del modelo.</div>`);
}

/* ---------- chat ---------- */

function burbuja(quien, html) {
  const d = document.createElement("div");
  d.className = `burbuja ${quien}`;
  d.innerHTML = html;
  $("#conversacion").appendChild(d);
  $("#conversacion").scrollTop = $("#conversacion").scrollHeight;
  return d;
}

$("#formulario").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const campo = $("#pregunta");
  const texto = campo.value.trim();
  if (!texto) return;
  campo.value = "";
  burbuja("usuario", negrita(texto));
  HISTORIAL.push(texto);
  const cargando = burbuja("bot", '<div class="cargador">Consultando la base de datos…</div>');
  $("#enviar").disabled = true;
  try {
    const r = await pedir("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta: texto, historial: HISTORIAL, contexto: CONTEXTO })
    });
    CONTEXTO = r.contexto;
    cargando.innerHTML = renderRespuesta(r);
    cargando.querySelectorAll("[data-ir]").forEach((b) => {
      b.onclick = () => cambiarPanel(b.dataset.ir);
    });
  } catch (e) {
    cargando.innerHTML = `<div class="texto">Ha fallado la consulta: ${e.message}</div>`;
  } finally {
    $("#enviar").disabled = false;
    campo.focus();
  }
});

function renderRespuesta(r) {
  let html = `<div class="texto">${negrita(r.texto)}</div>`;
  const d = r.datos || {};
  if (d.tipo === "resultado") html += vistaResultado(d);
  else if (d.tipo === "comparar") html += vistaComparar(d);
  else if (d.tipo === "evolucion") html += vistaEvolucion(d);
  else if (d.tipo === "ranking") html += vistaRanking(d);
  else if (d.tipo === "mesas") html += vistaMesas(d);
  else if (d.tipo === "futuro") {
    html += `<p class="nota">${d.detalle}</p>
      <button class="secundario" data-ir="escenarios">Abrir el simulador de escenarios</button>`;
  } else if (d.tipo === "escenario_redirigir") {
    html += `<button class="secundario" data-ir="escenarios">Abrir el simulador</button>`;
  } else if (d.tipo === "ayuda" && d.ejemplos) {
    html += `<p class="nota">Prueba con algo así:</p><ul class="nota">` +
      d.ejemplos.map((e) => `<li>${e}</li>`).join("") + `</ul>`;
  }
  html += `<div class="etiqueta-fuente"><span class="punto${r.llm ? "" : " reglas"}"></span>
    ${r.llm ? `redactado por ${META.modelo}` : "redactado con plantilla"} ·
    cifras leídas de la base de datos</div>`;
  return html;
}

function barras(filas, maximo) {
  const tope = maximo || Math.max(...filas.map((f) => f.pct), 1);
  return `<div class="barras">` + filas.map((f) => `
    <div class="barra-fila">
      <span class="barra-nombre">${f.nombre}</span>
      <span class="barra-pista"><span class="barra-relleno"
        style="width:${(100 * f.pct / tope).toFixed(1)}%;background:${f.color}"></span></span>
      <span class="barra-valor">${dec(f.pct)} % · ${ent(f.votos)}</span>
    </div>`).join("") + `</div>`;
}

function vistaResultado(d) {
  return d.resultados.map((r) => {
    const s = r.resumen;
    return `<h3>${r.territorio} · ${r.eleccion}</h3>${barras(r.partidos)}
      <div class="metricas">
        ${metrica(dec(s.participacion) + " %", "Participación", ent(s.votantes) + " votantes")}
        ${metrica(ent(s.censo_escrutinio), "Censo", r.nivel === "nacional" ? "España" : r.territorio)}
        ${metrica(dec(s.pct_izquierda_total) + " %", "Bloque de izquierdas", "")}
        ${metrica(dec(s.pct_derecha_total) + " %", "Bloque de derechas", "")}
        ${metrica(dec(s.pct_nacionalista) + " %", "Nacionalistas", "")}
        ${metrica(dec(s.posicion_ideologica, 2), "Posición ideológica", "escala 0 a 10")}
      </div>`;
  }).join("");
}

function metrica(valor, etiqueta, detalle) {
  return `<div class="metrica"><div class="valor">${valor}</div>
    <div class="etiqueta">${etiqueta}</div>
    ${detalle ? `<div class="detalle">${detalle}</div>` : ""}</div>`;
}

function vistaComparar(d) {
  const claves = new Set();
  d.resultados.forEach((r) => r.partidos.slice(0, 6).forEach((p) => claves.add(p.clave)));
  const lista = Array.from(claves);
  let h = `<div class="tabla-envoltura"><table><thead><tr><th>Partido</th>` +
    d.resultados.map((r) => `<th class="num">${r.territorio}</th>`).join("") +
    `</tr></thead><tbody>`;
  lista.forEach((c) => {
    const fila = d.resultados.map((r) => {
      const p = r.partidos.find((x) => x.clave === c);
      return `<td class="num">${p ? dec(p.pct) + " %" : "—"}</td>`;
    }).join("");
    const ref = d.resultados.map((r) => r.partidos.find((x) => x.clave === c)).find(Boolean);
    h += `<tr><td><span class="pastilla" style="background:${ref.color}">${ref.nombre}</span></td>${fila}</tr>`;
  });
  h += `<tr><td><b>Participación</b></td>` +
    d.resultados.map((r) => `<td class="num">${dec(r.resumen.participacion)} %</td>`).join("") +
    `</tr></tbody></table></div>`;
  return h;
}

function vistaEvolucion(d) {
  const claves = d.partidos_pedidos && d.partidos_pedidos.length ? d.partidos_pedidos
    : ["pp", "psoe", "vox", "podemos_sumar"];
  const series = claves.filter((c) => META.partidos[c]).map((c) => ({
    clave: c, nombre: META.partidos[c].nombre, color: META.partidos[c].color,
    puntos: d.serie.map((e) => e[`pct_${c}`] || 0)
  })).filter((s) => Math.max(...s.puntos) > 0.5);
  return grafico(d.serie.map((e) => e.eleccion), series, "%") + `
    <div class="tabla-envoltura"><table><thead><tr><th>Convocatoria</th><th>Ganador</th>
      <th class="num">Participación</th><th class="num">Índice izq-der</th></tr></thead><tbody>` +
    d.serie.map((e) => `<tr><td>${e.eleccion}</td><td>${e.ganador || "—"}</td>
      <td class="num">${dec(e.participacion)} %</td>
      <td class="num">${e.indice_izq_der > 0 ? "+" : ""}${dec(e.indice_izq_der)}</td></tr>`).join("") +
    `</tbody></table></div>`;
}

function grafico(etiquetas, series, unidad) {
  const W = 640, H = 230, ML = 42, MB = 26, MT = 12, MR = 12;
  const todos = series.flatMap((s) => s.puntos);
  const max = Math.max(...todos, 1) * 1.12, min = Math.min(...todos, 0);
  const x = (i) => ML + i * (W - ML - MR) / Math.max(etiquetas.length - 1, 1);
  const y = (v) => MT + (H - MT - MB) * (1 - (v - min) / (max - min || 1));
  let svg = `<svg viewBox="0 0 ${W} ${H}" class="mosaico" style="margin-top:14px">`;
  for (let k = 0; k <= 4; k++) {
    const v = min + (max - min) * k / 4;
    svg += `<line x1="${ML}" y1="${y(v)}" x2="${W - MR}" y2="${y(v)}"
      stroke="currentColor" stroke-opacity=".12"/>
      <text x="${ML - 6}" y="${y(v) + 3}" text-anchor="end" font-size="9"
      fill="currentColor" fill-opacity=".55">${dec(v, 0)}${unidad}</text>`;
  }
  etiquetas.forEach((e, i) => {
    svg += `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="9"
      fill="currentColor" fill-opacity=".55">${e}</text>`;
  });
  series.forEach((s) => {
    const d = s.puntos.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");
    svg += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.2"
      stroke-linejoin="round"/>`;
    s.puntos.forEach((v, i) => {
      svg += `<circle cx="${x(i)}" cy="${y(v)}" r="2.8" fill="${s.color}"><title>${s.nombre} ${etiquetas[i]}: ${dec(v)}${unidad}</title></circle>`;
    });
  });
  svg += `</svg><div class="leyenda">` + series.map((s) =>
    `<span><i class="punto-leyenda" style="background:${s.color}"></i>${s.nombre}</span>`).join("") + `</div>`;
  return svg;
}

function vistaRanking(d) {
  return `<div class="tabla-envoltura"><table><thead><tr><th>#</th><th>Territorio</th>
    <th>Ámbito</th><th class="num">${d.etiqueta}</th></tr></thead><tbody>` +
    d.filas.map((f, i) => `<tr><td>${i + 1}</td><td>${f.nombre}</td>
      <td class="nota">${f.contexto || ""}</td>
      <td class="num">${dec(f.valor)}${d.unidad === "%" ? " %" : ""}</td></tr>`).join("") +
    `</tbody></table></div>` +
    (d.poblacion_minima ? `<p class="nota">Solo municipios de más de
      ${ent(d.poblacion_minima)} habitantes.</p>` : "");
}

function vistaMesas(d) {
  return `<div class="tabla-envoltura"><table><thead><tr><th>Distrito</th><th>Sección</th>
    <th>Mesa</th><th class="num">Censo</th><th class="num">Participación</th>
    <th>Ganador</th></tr></thead><tbody>` +
    d.mesas.slice(0, 60).map((m) => `<tr><td>${m.distrito}</td><td>${m.seccion}</td>
      <td>${m.mesa}</td><td class="num">${ent(m.censo)}</td>
      <td class="num">${dec(m.participacion)} %</td><td>${m.ganador || "—"}</td></tr>`).join("") +
    `</tbody></table></div>` +
    (d.total_mesas > 60 ? `<p class="nota">Mostrando 60 de ${ent(d.total_mesas)} mesas.</p>` : "");
}

/* ---------- explorar ---------- */

function cambiarPanel(nombre) {
  $$(".pestana").forEach((b) => b.classList.toggle("activa", b.dataset.panel === nombre));
  $$(".panel").forEach((p) => p.classList.toggle("activo", p.id === `panel-${nombre}`));
  if (location.hash.slice(1) !== nombre) history.replaceState(null, "", `#${nombre}`);
  if (nombre === "escenarios" && !ESCENARIO_BASE) cargarEscenario();
  if (nombre === "backtest" && !$("#backtest-metricas").dataset.listo) cargarBacktest();
}
$$(".pestana").forEach((b) => b.onclick = () => cambiarPanel(b.dataset.panel));

function escalaIndice(v) {
  const t = Math.max(-40, Math.min(40, v || 0)) / 40;
  const c1 = [227, 69, 63], c2 = [59, 130, 214], base = [150, 158, 170];
  const m = t < 0 ? c1 : c2, f = Math.abs(t);
  return `rgb(${m.map((c, i) => Math.round(base[i] + (c - base[i]) * f)).join(",")})`;
}
function escalaParticipacion(v) {
  const t = Math.max(0, Math.min(1, ((v || 60) - 55) / 30));
  return `rgb(${Math.round(240 - 150 * t)},${Math.round(245 - 80 * t)},${Math.round(235 - 60 * t)})`;
}

async function cargarMapa() {
  const eleccion = $("#ex-eleccion").value;
  const modo = $("#ex-metrica").value;
  const metrica = modo === "ganador" ? "indice_izq_der" : modo;
  const d = await pedir(`/api/mapa?eleccion=${eleccion}&metrica=${metrica}`);
  const C = 34, G = 3;
  let svg = `<svg viewBox="0 0 ${11 * (C + G)} ${9 * (C + G)}" class="mosaico">`;
  const usados = new Map();
  d.zonas.forEach((z) => {
    const pos = MOSAICO[z.codigo];
    if (!pos) return;
    const color = modo === "ganador" ? z.color_ganador
      : modo === "participacion" ? escalaParticipacion(z.participacion)
      : escalaIndice(z.valor);
    if (modo === "ganador") usados.set(z.ganador, z.color_ganador);
    const oscuro = modo === "participacion";
    svg += `<g class="celda" data-cod="${z.codigo}">
      <rect x="${pos[0] * (C + G)}" y="${pos[1] * (C + G)}" width="${C}" height="${C}"
        rx="5" fill="${color}"><title>${z.nombre} · ${z.ganador} · participación ${dec(z.participacion)} %</title></rect>
      <text x="${pos[0] * (C + G) + C / 2}" y="${pos[1] * (C + G) + C / 2 + 3}"
        text-anchor="middle" fill="${oscuro ? "#1a1f28" : "#fff"}">${SIGLAS[z.codigo]}</text></g>`;
  });
  svg += `</svg>`;
  $("#mapa").innerHTML = svg;
  $$("#mapa .celda").forEach((g) => g.onclick = () => mostrarDetalle("provincia", g.dataset.cod));
  if (modo === "ganador") {
    $("#leyenda").innerHTML = Array.from(usados).map(([n, c]) =>
      `<span><i class="punto-leyenda" style="background:${c}"></i>${n}</span>`).join("");
  } else if (modo === "participacion") {
    $("#leyenda").innerHTML = `<span>Más clara = menos participación · más oscura = más participación</span>`;
  } else {
    $("#leyenda").innerHTML = `<span><i class="punto-leyenda" style="background:${escalaIndice(-35)}"></i>Izquierda</span>
      <span><i class="punto-leyenda" style="background:${escalaIndice(0)}"></i>Equilibrio</span>
      <span><i class="punto-leyenda" style="background:${escalaIndice(35)}"></i>Derecha</span>`;
  }
}

async function mostrarDetalle(nivel, codigo) {
  const eleccion = $("#ex-eleccion").value || "2023";
  const r = await pedir(`/api/resultado?nivel=${nivel}&codigo=${codigo || ""}&eleccion=${eleccion}`);
  if (!r || !r.partidos) { $("#detalle").innerHTML = `<p class="nota">Sin datos.</p>`; return; }
  $("#detalle-titulo").textContent = `${r.territorio} · ${r.eleccion}`;
  const s = r.resumen;
  const socio = Object.entries(r.socio).filter(([, v]) => v !== null)
    .map(([k, v]) => `<tr><td>${k.replace(/_/g, " ")}</td><td class="num">${dec(v)}</td></tr>`).join("");
  const ev = await pedir(`/api/evolucion?nivel=${nivel}&codigo=${codigo || ""}`);
  $("#detalle").innerHTML = barras(r.partidos) + `
    <div class="metricas">
      ${metrica(dec(s.participacion) + " %", "Participación", ent(s.votantes) + " votantes")}
      ${metrica(ent(s.censo_escrutinio), "Censo", "")}
      ${metrica(dec(s.pct_izquierda_total) + " %", "Izquierdas", "")}
      ${metrica(dec(s.pct_derecha_total) + " %", "Derechas", "")}
    </div>
    <h3>Evolución 1996-2023</h3>` +
    grafico(ev.serie.map((e) => e.eleccion),
      ["pp", "psoe", "vox", "podemos_sumar"].map((c) => ({
        nombre: META.partidos[c].nombre, color: META.partidos[c].color,
        puntos: ev.serie.map((e) => e[`pct_${c}`] || 0)
      })).filter((s) => Math.max(...s.puntos) > 0.5), "%") +
    (socio ? `<h3>Contexto socioeconómico</h3><div class="tabla-envoltura"><table><tbody>${socio}</tbody></table></div>` : "");
}

const campoBuscar = $("#ex-buscar");
let temporizador = null;
campoBuscar.addEventListener("input", () => {
  clearTimeout(temporizador);
  temporizador = setTimeout(async () => {
    const q = campoBuscar.value.trim();
    if (q.length < 2) { $("#ex-resultados").classList.remove("visible"); return; }
    const r = await pedir(`/api/buscar?q=${encodeURIComponent(q)}`);
    const caja = $("#ex-resultados");
    caja.innerHTML = r.map((x) =>
      `<div class="opcion" data-nivel="${x.nivel}" data-cod="${x.codigo || ""}">${x.nombre}
        <small>${x.contexto}</small></div>`).join("") ||
      `<div class="opcion">Sin coincidencias</div>`;
    caja.classList.add("visible");
    caja.querySelectorAll(".opcion[data-nivel]").forEach((o) => o.onclick = () => {
      mostrarDetalle(o.dataset.nivel, o.dataset.cod);
      caja.classList.remove("visible");
      campoBuscar.value = "";
    });
  }, 220);
});
document.addEventListener("click", (e) => {
  if (!e.target.closest(".buscador")) $("#ex-resultados").classList.remove("visible");
});

/* ---------- escenarios ---------- */

async function cargarEscenario() {
  $("#deslizadores").innerHTML = `<div class="cargador">Entrenando el modelo, unos 20 segundos…</div>`;
  const d = await pedir("/api/escenario/partida");
  ESCENARIO_BASE = d;
  pintarDeslizadores(d.partidos);
  simular();
}

function pintarDeslizadores(partidos) {
  $("#deslizadores").innerHTML = partidos.map((p) => `
    <div class="deslizador">
      <div class="deslizador-cabecera"><span>
        <i class="punto-leyenda" style="background:${p.color};display:inline-block"></i>
        ${p.nombre}</span><b><span id="v-${p.clave}">${dec(p.valor, 1)}</span> %</b></div>
      <input type="range" min="0" max="${Math.max(50, Math.ceil(p.valor * 2))}" step="0.1"
        value="${p.valor.toFixed(1)}" data-clave="${p.clave}">
    </div>`).join("");
  $$("#deslizadores input").forEach((i) => i.addEventListener("input", () => {
    $(`#v-${i.dataset.clave}`).textContent = dec(parseFloat(i.value), 1);
    actualizarSuma();
  }));
  actualizarSuma();
}

function valoresEscenario() {
  const v = {};
  $$("#deslizadores input").forEach((i) => v[i.dataset.clave] = parseFloat(i.value));
  return v;
}

function actualizarSuma() {
  const v = valoresEscenario();
  const total = Object.values(v).reduce((a, b) => a + b, 0);
  $("#suma-total").innerHTML = `Suma de los partidos mostrados: <b>${dec(total, 1)} %</b>.
    El resto hasta el 100 % corresponde a otras candidaturas.`;
}

$("#simular").onclick = simular;
$("#reiniciar").onclick = () => { pintarDeslizadores(ESCENARIO_BASE.partidos); simular(); };

async function simular() {
  const caja = $("#mapa-escenario");
  caja.innerHTML = `<div class="cargador">Repartiendo el voto por el territorio…</div>`;
  const r = await pedir("/api/escenario", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nacional: valoresEscenario() })
  });
  const res = r.resultado;
  const C = 34, G = 3;
  let svg = `<svg viewBox="0 0 ${11 * (C + G)} ${9 * (C + G)}" class="mosaico">`;
  res.provincias.forEach((p) => {
    const pos = MOSAICO[p.codigo];
    if (!pos) return;
    svg += `<g class="celda"><rect x="${pos[0] * (C + G)}" y="${pos[1] * (C + G)}"
      width="${C}" height="${C}" rx="5" fill="${p.color}">
      <title>${p.nombre} · ganaría ${p.ganador} · participación ${dec(p.participacion)} %</title></rect>
      <text x="${pos[0] * (C + G) + C / 2}" y="${pos[1] * (C + G) + C / 2 + 3}"
        text-anchor="middle" fill="#fff">${SIGLAS[p.codigo]}</text></g>`;
  });
  svg += `</svg>`;
  caja.innerHTML = svg;
  const orden = Object.entries(res.provincias_ganadas).sort((a, b) => b[1] - a[1]);
  $("#resumen-escenario").innerHTML = `<div class="metricas">` +
    orden.map(([n, c]) => metrica(c, `provincias para ${n}`, "")).join("") + `</div>
    <div class="tabla-envoltura"><table><thead><tr><th>Provincia</th><th>Ganaría</th>
    <th class="num">PP</th><th class="num">PSOE</th><th class="num">VOX</th>
    <th class="num">Participación</th></tr></thead><tbody>` +
    res.provincias.map((p) => `<tr><td>${p.nombre}</td>
      <td><span class="pastilla" style="background:${p.color}">${p.ganador}</span></td>
      <td class="num">${dec(p.pp)}</td><td class="num">${dec(p.psoe)}</td>
      <td class="num">${dec(p.vox)}</td>
      <td class="num">${dec(p.participacion)} %</td></tr>`).join("") +
    `</tbody></table></div>`;
}

/* ---------- backtest ---------- */

async function cargarBacktest() {
  $("#backtest-metricas").innerHTML = `<div class="cargador">Entrenando y evaluando…</div>`;
  const d = await pedir("/api/backtest");
  $("#backtest-metricas").dataset.listo = "1";
  $("#backtest-intro").innerHTML = `El modelo se entrena <b>solo con datos hasta
    ${d.entrenado_hasta}</b> y se le pide repartir el resultado nacional de 2023 entre los
    ${ent(d.n_municipios)} municipios. Nunca ve el resultado municipal de 2023.
    Acierta el partido más votado en el <b>${dec(100 * d.acierto_ganador, 1)} %</b> de los municipios.`;
  $("#backtest-metricas").innerHTML = `<div class="metricas">` +
    d.resumen.map((r) => metrica(dec(r.mae) + " pts",
      `${r.nombre} · error medio`, `R² ${dec(r.r2, 3)} · real ${dec(r.media_real)} % / predicho ${dec(r.media_pred)} %`)).join("") +
    `</div>`;
  $("#backtest-dispersión").innerHTML = dispersion(d.detalle);
  $("#backtest-tabla").innerHTML = `<div class="tabla-envoltura"><table><thead><tr>
    <th>Municipio</th><th>Provincia</th><th class="num">PP real</th><th class="num">PP pred.</th>
    <th class="num">PSOE real</th><th class="num">PSOE pred.</th></tr></thead><tbody>` +
    d.detalle.slice(0, 40).map((f) => `<tr><td>${f.municipio}</td><td>${f.provincia}</td>
      <td class="num">${dec(f.pp_real)}</td><td class="num">${dec(f.pp_pred)}</td>
      <td class="num">${dec(f.psoe_real)}</td><td class="num">${dec(f.psoe_pred)}</td></tr>`).join("") +
    `</tbody></table></div>`;
}

function dispersion(detalle) {
  const W = 640, H = 300, M = 40, max = 70;
  const x = (v) => M + (W - 2 * M) * v / max;
  const y = (v) => H - M - (H - 2 * M) * v / max;
  let svg = `<svg viewBox="0 0 ${W} ${H}" class="mosaico" style="margin-top:12px">
    <line x1="${x(0)}" y1="${y(0)}" x2="${x(max)}" y2="${y(max)}"
      stroke="currentColor" stroke-opacity=".3" stroke-dasharray="4 4"/>`;
  for (let v = 0; v <= max; v += 10) {
    svg += `<text x="${x(v)}" y="${H - M + 16}" text-anchor="middle" font-size="9"
      fill="currentColor" fill-opacity=".55">${v}</text>
      <text x="${M - 8}" y="${y(v) + 3}" text-anchor="end" font-size="9"
      fill="currentColor" fill-opacity=".55">${v}</text>`;
  }
  [["pp", "#1D84CE"], ["psoe", "#E30713"], ["vox", "#5BA82B"]].forEach(([k, c]) => {
    detalle.forEach((f) => {
      svg += `<circle cx="${x(f[k + "_real"])}" cy="${y(f[k + "_pred"])}" r="2.6"
        fill="${c}" fill-opacity=".65"><title>${f.municipio}: real ${dec(f[k + "_real"])} %, predicho ${dec(f[k + "_pred"])} %</title></circle>`;
    });
  });
  svg += `<text x="${W / 2}" y="${H - 6}" text-anchor="middle" font-size="10"
    fill="currentColor" fill-opacity=".6">% real en 2023</text>
    <text x="12" y="${H / 2}" text-anchor="middle" font-size="10" fill="currentColor"
    fill-opacity=".6" transform="rotate(-90 12 ${H / 2})">% predicho</text></svg>
    <div class="leyenda"><span><i class="punto-leyenda" style="background:#1D84CE"></i>PP</span>
    <span><i class="punto-leyenda" style="background:#E30713"></i>PSOE</span>
    <span><i class="punto-leyenda" style="background:#5BA82B"></i>VOX</span>
    <span>Cuanto más cerca de la diagonal, mejor la predicción</span></div>`;
  return svg;
}

window.addEventListener("hashchange", () => {
  const n = location.hash.slice(1);
  if (n && $(`#panel-${n}`)) cambiarPanel(n);
});

inicio().then(() => {
  const n = location.hash.slice(1);
  if (n && $(`#panel-${n}`)) cambiarPanel(n);
  const q = new URLSearchParams(location.search).get("q");
  if (q) { $("#pregunta").value = q; $("#formulario").requestSubmit(); }
});
