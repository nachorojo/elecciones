/* Simulador de escaños del 29N. NO es un pronóstico: reparte por provincias el resultado nacional
   que el usuario elige, suponiendo que cada espacio conserva su perfil territorial de 2023, y aplica
   d'Hondt con barrera del 3 % en cada circunscripción.
   Datos: data/simulador.json (pipeline/simulador.py). El cálculo es el mismo que `simular` en Python
   (tests/test_simulador.py comprueba que ambos dan idéntico reparto). */
const MotorSim = (() => {
  const RESTO = "_RESTO";

  /* Ajuste proporcional iterativo: columnas (espacios) a su total nacional, filas (provincias) a sus votos válidos. */
  function ajustar(base, objetivo, filas, iteraciones = 200, tol = 1e-9) {
    const x = {};
    const presentes = new Set();
    for (const [p, fila] of Object.entries(base)) {
      x[p] = {};
      for (const [e, v] of Object.entries(fila)) {
        if (v > 0 && objetivo[e] > 0) { x[p][e] = v; presentes.add(e); }
      }
    }
    const total = Object.values(filas).reduce((a, b) => a + b, 0);
    let sumaObj = 0;
    presentes.forEach((e) => { sumaObj += objetivo[e]; });
    const obj = {};
    presentes.forEach((e) => { obj[e] = objetivo[e] * total / sumaObj; });
    for (let it = 0; it < iteraciones; it++) {
      const col = {};
      presentes.forEach((e) => { col[e] = 0; });
      for (const fila of Object.values(x)) for (const e in fila) col[e] += fila[e];
      for (const fila of Object.values(x)) for (const e in fila) fila[e] *= obj[e] / col[e];
      let error = 0;
      for (const [p, fila] of Object.entries(x)) {
        let s = 0;
        for (const e in fila) s += fila[e];
        if (s > 0) {
          const k = filas[p] / s;
          error = Math.max(error, Math.abs(k - 1));
          for (const e in fila) fila[e] *= k;
        }
      }
      if (error < tol) break;
    }
    return x;
  }

  /* d'Hondt con barrera del 3 % de los votos válidos (candidaturas + blancos). */
  function dhondt(votos, n, blancos = 0, umbral = 0.03) {
    let validos = blancos;
    for (const e in votos) validos += votos[e];
    const cocientes = [];
    for (const [e, v] of Object.entries(votos)) {
      if (v > 0 && v >= umbral * validos) for (let k = 1; k <= n; k++) cocientes.push([v / k, v, e]);
    }
    cocientes.sort((a, b) => b[0] - a[0] || b[1] - a[1] || (a[2] < b[2] ? 1 : -1));
    const out = {};
    cocientes.slice(0, n).forEach(([, , e]) => { out[e] = (out[e] || 0) + 1; });
    return out;
  }

  /* pct: {espacio: % nacional de votos válidos}. Devuelve votos y escaños por provincia y el total. */
  function simular(datos, pct, campoEscanos = "escanos") {
    const objetivo = {};
    let suma = 0;
    for (const [e, v] of Object.entries(pct)) {
      if (v > 0) objetivo[e] = datos.validos * v / 100;
      suma += v;
    }
    if (100 - suma > 0) objetivo[RESTO] = datos.validos * (100 - suma) / 100;
    const base = {}, filas = {};
    for (const [p, d] of Object.entries(datos.provincias)) {
      base[p] = { ...d.base, [RESTO]: d.resto };
      filas[p] = d.validos;
    }
    const votos = ajustar(base, objetivo, filas);
    const escanos = {}, total = {};
    for (const [p, fila] of Object.entries(votos)) {
      const cand = {};
      for (const e in fila) if (e !== RESTO) cand[e] = Math.round(fila[e]);
      escanos[p] = dhondt(cand, datos.provincias[p][campoEscanos], Math.round(fila[RESTO] || 0));
      for (const e in escanos[p]) total[e] = (total[e] || 0) + escanos[p][e];
    }
    return { votos, escanos, total };
  }

  return { ajustar, dhondt, simular, RESTO };
})();

if (typeof module !== "undefined") module.exports = MotorSim;

const Simulador = (() => {
  const COLOR_SIM = {
    PP: "#1D84CE", PSOE: "#E30713", VOX: "#5BA82B", FA: "#E51C55", PODEMOS: "#6B2E7A", SALF: "#7A5230",
    ERC: "#E0A020", JUNTS: "#00A99D", EH_BILDU: "#7BA21A", PNV: "#0F6B3C", BNG: "#5F93C0", CC: "#C9A400",
    COMPROMIS: "#D96A2B", NC: "#3C8D5A", ADELANTE: "#2AA198", TERUEL_EXISTE: "#4B6B4F", GBAI: "#B0333A"
  };
  const NACIONALES = ["PP", "PSOE", "VOX", "FA", "PODEMOS", "SALF"];
  const MAYORIA = 176;
  let D = null, pct = {}, res = null, provincia = null, promesa = null;
  const col = (e) => COLOR_SIM[e] || "#8D98A6";
  const nombre = (e) => (D.espacios.find((x) => x.id === e) || { nombre: e }).nombre;
  const suma = () => Object.values(pct).reduce((a, b) => a + b, 0);

  function iniciar() {
    if (!promesa) {
      promesa = fetch("data/simulador.json").then((r) => {
        if (!r.ok) throw new Error("data/simulador.json: " + r.status);
        return r.json();
      }).then((d) => {
        D = d;
        reiniciar();
        montar();
      }).catch((err) => { $("#estado-sim").textContent = "No se pudo cargar el simulador (" + err.message + "). Solo funciona por HTTP."; });
    }
    return promesa;
  }

  function reiniciar() {
    pct = {};
    D.espacios.forEach((e) => { pct[e.id] = e.inicio; });
  }

  function control(e, conBarra) {
    const fila = el("div", "sim-fila");
    const etq = el("label", null, e.nombre);
    etq.htmlFor = "sim-" + e.id;
    const punto = el("i"); punto.style.background = col(e.id);
    etq.prepend(punto);
    const n = el("input");
    n.type = "number"; n.id = "sim-" + e.id; n.min = 0; n.max = 60; n.step = conBarra ? 0.1 : 0.05; n.value = pct[e.id];
    n.setAttribute("inputmode", "decimal");
    const poner = (v, origen) => {
      v = Math.max(0, Math.min(60, Number(v) || 0));
      pct[e.id] = v;
      if (origen !== n) n.value = v;
      if (barra && origen !== barra) barra.value = v;
      calcular();
    };
    let barra = null;
    if (conBarra) {
      barra = el("input");
      barra.type = "range"; barra.min = 0; barra.max = 45; barra.step = 0.1; barra.value = pct[e.id];
      barra.setAttribute("aria-label", e.nombre + ": porcentaje nacional");
      barra.style.accentColor = col(e.id);
      barra.addEventListener("input", () => poner(barra.value, barra));
    }
    n.addEventListener("input", () => poner(n.value, n));
    fila.append(etq);
    if (barra) fila.append(barra);
    const caja = el("span", "sim-num");
    caja.append(n, " %");
    fila.append(caja);
    if (e.provincias < 52) fila.append(el("small", null, e.provincias + (e.provincias === 1 ? " circunscripción" : " circunscripciones")));
    return fila;
  }

  function montar() {
    const c = $("#sim-controles");
    c.replaceChildren();
    D.espacios.filter((e) => NACIONALES.includes(e.id)).forEach((e) => c.appendChild(control(e, true)));
    const det = el("details", "sim-detalle");
    det.appendChild(el("summary", null, "Candidaturas de ámbito autonómico (porcentaje sobre el total nacional)"));
    D.espacios.filter((e) => !NACIONALES.includes(e.id)).forEach((e) => det.appendChild(control(e, false)));
    c.appendChild(det);
    const bt = D.backtest.filter((b) => b.a !== "1996");
    const errs = bt.map((b) => b.escanos_mal_nacional).sort((a, b) => a - b);
    const maxP = Math.max(...bt.map((b) => b.max_error_partido));
    $("#sim-error").textContent =
      `Error medido del método: repartiendo el resultado nacional REAL de cada elección (2000–2023) con el perfil ` +
      `territorial de la anterior, entre ${errs[0]} y ${errs[errs.length - 1]} de los 350 escaños acaban en un partido ` +
      `distinto del real (mediana ${errs[Math.floor(errs.length / 2)]}), y un partido concreto se desvía hasta ${maxP} escaños. ` +
      `El error es mayor cuando irrumpen candidaturas nuevas (2015, abril de 2019), como ocurre el 29N.`;
    $("#estado-sim").hidden = true;
  }

  function calcular() {
    res = MotorSim.simular(D, pct);
    pintar();
  }

  function pintarMosaico() {
    const mapa = $("#mapa-sim");
    mapa.replaceChildren();
    for (const [cod, [x, y]] of Object.entries(MOSAICO)) {
      const d = D.provincias[cod];
      const fila = res.votos[cod];
      let g = null;
      for (const e in fila) if (e !== MotorSim.RESTO && (!g || fila[e] > fila[g])) g = e;
      const b = el("button", "casilla" + (cod === provincia ? " activa" : ""), SIGLAS[cod]);
      b.type = "button";
      b.style.gridColumn = x + 1;
      b.style.gridRow = y + 1;
      const t = Math.min(1, Math.max(0, (100 * fila[g] / d.validos - 25) / 30));
      b.style.background = `color-mix(in srgb, ${col(g)} ${Math.round(40 + 60 * t)}%, var(--superficie-alta))`;
      const rep = Object.entries(res.escanos[cod]).sort((a, c) => c[1] - a[1]).map(([e, n]) => `${nombre(e)} ${n}`).join(", ");
      b.title = `${d.nombre} (${d.escanos} escaños): ${rep}`;
      b.setAttribute("aria-label", b.title);
      b.addEventListener("click", () => { provincia = cod; pintar(); });
      mapa.appendChild(b);
    }
  }

  function pintarDetalle() {
    const d = provincia ? D.provincias[provincia] : null;
    $("#titulo").textContent = d ? `Escenario · ${d.nombre}` : "Escenario · España";
    $("#volver").hidden = !provincia;
    const cambio = d && d.escanos !== d.escanos_2023 ? ` (en 2023 eran ${d.escanos_2023})` : "";
    $("#fecha").textContent = d
      ? `${d.escanos} escaños el 29 de noviembre de 2026${cambio}. Reparto que saldría con tu escenario nacional; no es un pronóstico.`
      : "350 escaños el 29 de noviembre de 2026. Reparto que saldría con tu escenario nacional; no es un pronóstico.";
    const esc = provincia ? res.escanos[provincia] : res.total;
    const votos = {};
    let validos = 0;
    const filas = provincia ? { [provincia]: res.votos[provincia] } : res.votos;
    for (const fila of Object.values(filas)) for (const e in fila) { votos[e] = (votos[e] || 0) + fila[e]; validos += fila[e]; }
    const orden = Object.keys(votos).filter((e) => e !== MotorSim.RESTO)
      .sort((a, b) => (esc[b] || 0) - (esc[a] || 0) || votos[b] - votos[a]);
    const r = $("#resumen");
    r.replaceChildren();
    const primero = orden[0];
    const datos = provincia
      ? [[String(d.escanos), "escaños en juego"], [nombre(primero), "candidatura más votada"]]
      : [[String(MAYORIA), "mayoría absoluta"], [`${nombre(primero)} · ${esc[primero] || 0}`, "primera fuerza en escaños"],
         [dec(Math.max(0, 100 - suma()), 1) + " %", "resto de candidaturas y blanco"]];
    datos.forEach(([v, l]) => {
      const c = el("div", "dato");
      c.append(el("b", null, v), el("span", null, l));
      r.appendChild(c);
    });
    const lista = $("#partidos");
    lista.replaceChildren();
    const tope = Math.max(1, ...orden.map((e) => esc[e] || 0));
    orden.filter((e) => (esc[e] || 0) > 0 || 100 * votos[e] / validos >= 1).forEach((e) => {
      const f = el("div", "fila");
      const barra = el("div", "barra");
      const s = el("span"); s.style.width = `${100 * (esc[e] || 0) / tope}%`; s.style.background = col(e);
      barra.appendChild(s);
      const antes = !provincia && D.escanos_2023[e] !== undefined ? ` · 2023: ${D.escanos_2023[e]}` : "";
      const n = el("div", "esc", String(esc[e] || 0));
      n.append(" ", el("small", null, "esc."));
      f.append(el("div", null, nombre(e)), barra, el("div", "cifras", `${dec(100 * votos[e] / validos, 1)} %${antes}`), n);
      lista.appendChild(f);
    });
    const exceso = suma() > 100.0001;
    $("#otros").textContent = (exceso
      ? `Los porcentajes suman ${dec(suma(), 1)} %: se han reescalado proporcionalmente para que sumen 100. `
      : "") + (provincia
      ? "Porcentajes estimados sobre votos válidos de la provincia. Con pocos escaños en juego, un cambio pequeño de voto mueve el último escaño."
      : `En 2023, Sumar obtuvo ${D.escanos_2023.IZQ} escaños; el 29N ese espacio concurre dividido (Frente Amplio, Podemos y listas conjuntas en la Comunidad Valenciana, Canarias y Andalucía). PP de 2023 incluye el escaño de UPN, que ahora va en coalición.`);
  }

  function pintar() {
    if (!D) return;
    if (!res) res = MotorSim.simular(D, pct);
    const s = suma();
    const linea = $("#sim-suma");
    linea.textContent = `Suma de las candidaturas: ${dec(s, 1)} % · resto y voto en blanco: ${dec(Math.max(0, 100 - s), 1)} %`;
    linea.classList.toggle("sim-exceso", s > 100.0001);
    pintarMosaico();
    pintarDetalle();
  }

  function limpiar() { provincia = null; }

  if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", () => {
    const b = $("#sim-reiniciar");
    if (b) b.addEventListener("click", () => { reiniciar(); res = null; montar(); pintar(); });
  });

  return { iniciar, pintar, limpiar };
})();
