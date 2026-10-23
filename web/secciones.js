/* Vista de secciones censales (2019 abril/noviembre y 2023). Se carga bajo demanda y por provincia.
   Geometría: data/sec/g/AAAA/NN.geojson (INE, CC BY 4.0), propiedad `s` = CUSEC de 10 dígitos.
   Resultados: data/sec/NN.json = {sección: {elección: [censo, votantes, blancos, nulos, candidaturas,
   [[cód, votos] x3], cód_ganador_anterior|null, cambio 0/1|null]}}; data/partidos_sec.json traduce códigos. */
const Seccion = (() => {
  const LEAFLET = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet";
  const ELECCIONES = ["2019a", "2019b", "2023"];
  const ANTERIOR = { "2019b": "2019a", "2023": "2019b" };
  const NOMBRE_EL = { "2019a": "abril de 2019", "2019b": "noviembre de 2019", "2023": "julio de 2023" };
  let mapa = null, capa = null, INDICE = [], MUNI = {}, PARTIDOS = {}, promesa = null, seleccionada = null, provActual = null;
  const datos = {}, geoms = {}, capas = new Map();

  const norm = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
  const elec = () => $("#eleccion").value;
  const anioCapa = (e) => (e === "2023" ? 2023 : 2019);
  const pedir = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); };
  const cargarScript = (src) => new Promise((ok, ko) => {
    const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = () => ko(new Error("no se pudo cargar " + src));
    document.head.appendChild(s);
  });
  const cargarCss = (href) => new Promise((ok, ko) => {
    const l = document.createElement("link"); l.rel = "stylesheet"; l.href = href; l.onload = ok; l.onerror = () => ko(new Error("no se pudo cargar " + href));
    document.head.appendChild(l);
  });
  const provNombre = (cod) => { const p = DATOS.elecciones[DATOS.elecciones.length - 1].provincias[cod]; return p ? p.nombre : cod; };
  const muniNombre = (id5) => MUNI[id5] || id5;
  const info = (e, cod) => (PARTIDOS[e] && PARTIDOS[e][cod]) || [cod, "OTROS"];
  const disponible = () => ELECCIONES.includes(elec());

  function fila(s) { const d = datos[s.slice(0, 2)]; return d && d[s] ? d[s][elec()] : null; }
  function resumen(s) {
    const f = fila(s);
    if (!f) return null;
    const validos = f[4] + f[2];
    const top = f[5][0];
    const [siglas, fam] = top ? info(elec(), top[0]) : ["—", "OTROS"];
    return { f, validos, siglas, fam, cuota: top ? 100 * top[1] / validos : 0, part: f[0] ? 100 * f[1] / f[0] : 0 };
  }

  const GRIS = { fillColor: "#c9cfd8", fillOpacity: 0.3, weight: 0.3, color: "#8d98a6" };
  function estilo(ft) {
    const r = resumen(ft.properties.s);
    if (!r || !r.f[5].length) return GRIS;
    if ($("#modo-sec").value === "cambio") {
      if (r.f[7] === null || r.f[7] === undefined) return { ...GRIS, fillOpacity: 0.22, dashArray: "2 2" };
      return r.f[7] === 1
        ? { fillColor: color(r.fam), fillOpacity: 0.92, weight: 0.5, color: "#12171f" }
        : { fillColor: color(r.fam), fillOpacity: 0.16, weight: 0.3, color: "#5d6b7f" };
    }
    const t = Math.min(1, Math.max(0, (r.cuota - 25) / 35));
    return { fillColor: color(r.fam), fillOpacity: 0.3 + 0.65 * t, weight: 0.3, color: "#5d6b7f" };
  }

  function hover(s) {
    const r = resumen(s);
    const nombre = `${muniNombre(s.slice(0, 5))} · distrito ${s.slice(5, 7)} · sección ${s.slice(7)}`;
    if (!r) return `${nombre}: sin datos en esta elección.`;
    return `${nombre}: ${r.siglas} ${dec(r.cuota, 1)} % · participación ${dec(r.part, 1)} % · ${num(r.f[0])} electores`;
  }

  function leyenda() {
    const ley = $("#leyenda");
    ley.replaceChildren();
    const ant = ANTERIOR[elec()];
    if ($("#modo-sec").value === "cambio") {
      ley.appendChild(el("span", null, ant
        ? `Color vivo: el ganador cambió respecto a ${NOMBRE_EL[ant]}. Tenue: mismo ganador. Gris punteado: no comparable (el municipio cambió de distritos o la sección cambió de tamaño).`
        : "No hay elección anterior con la que comparar."));
    } else {
      ley.appendChild(el("span", null, "Color = candidatura más votada; más intenso = más cuota de voto. Gris = sin datos."));
    }
  }

  function ficha() {
    if (!seleccionada) { $("#titulo").textContent = "Secciones censales"; $("#volver").hidden = true; $("#fecha").textContent = "";
      ["#resumen", "#partidos", "#historia"].forEach((q) => $(q).replaceChildren());
      $("#otros").textContent = "Pulsa una sección del mapa para ver sus tres candidaturas más votadas y si cambió el ganador. Una sección censal agrupa de unos cientos a unas 2.000 personas y NO equivale a una calle."; return; }
    const s = seleccionada, r = resumen(s), e = elec();
    $("#titulo").textContent = `${muniNombre(s.slice(0, 5))} · distrito ${s.slice(5, 7)}, sección ${s.slice(7)}`;
    $("#volver").hidden = false;
    $("#fecha").textContent = `Elecciones generales de ${NOMBRE_EL[e]} · ${provNombre(s.slice(0, 2))}`;
    const res = $("#resumen"), lista = $("#partidos");
    res.replaceChildren(); lista.replaceChildren();
    if (!r) { $("#otros").textContent = "Esta sección no tiene datos en la elección elegida (no existía o tenía otro código)."; return; }
    [[dec(r.part, 2) + " %", "participación"], [num(r.f[0]), "electores"], [num(r.validos), "votos válidos"]]
      .forEach(([v, l]) => { const d = el("div", "dato"); d.append(el("b", null, v), el("span", null, l)); res.appendChild(d); });
    const tope = r.f[5][0] ? r.f[5][0][1] : 1;
    r.f[5].forEach(([cod, v], i) => {
      const [sig, fam] = info(e, cod);
      const f = el("div", "fila fila-mun");
      const barra = el("div", "barra"); const sp = el("span");
      sp.style.width = `${100 * v / tope}%`; sp.style.background = color(fam); barra.appendChild(sp);
      f.append(el("div", null, `${i + 1}.º ${sig}`), barra, el("div", "cifras", `${num(v)} · ${dec(100 * v / r.validos, 2)} %`));
      lista.appendChild(f);
    });
    const resto = r.f[4] - r.f[5].reduce((t, p) => t + p[1], 0);
    let nota = `Resto de candidaturas: ${num(resto)} votos · en blanco: ${num(r.f[2])} · nulos: ${num(r.f[3])}.`;
    const ant = ANTERIOR[e];
    if (ant && r.f[6]) {
      const [as] = info(ant, r.f[6]);
      nota += r.f[7] === 1 ? ` Cambió el ganador: en ${NOMBRE_EL[ant]} ganó ${as}.` : ` Mismo ganador que en ${NOMBRE_EL[ant]} (${as}).`;
    } else if (ant) {
      nota += ` No comparable con ${NOMBRE_EL[ant]}: el municipio cambió de distritos o la sección cambió de tamaño.`;
    }
    $("#otros").textContent = nota + " Una sección no equivale a una calle: las mesas se reparten por apellidos.";
    const hist = $("#historia");
    hist.replaceChildren();
    ELECCIONES.forEach((x) => {
      const d = datos[s.slice(0, 2)][s][x];
      const top = d && d[5][0];
      const [sg, fm] = top ? info(x, top[0]) : ["—", "OTROS"];
      const c = el("span", "chip" + (x === e ? " actual" : ""), `${x}: ${sg}`);
      c.style.background = top ? color(fm) : "#8d98a6";
      hist.appendChild(c);
    });
  }

  function seleccionar(s) {
    seleccionada = s;
    pintar();
    const l = capas.get(s);
    if (l) { l.setStyle({ weight: 2.5, color: "#12171f" }); l.bringToFront(); }
  }

  function pintar() {
    if (!mapa) return;
    const estado = $("#estado-sec");
    if (!disponible()) {
      estado.textContent = "El nivel de sección solo está disponible para las elecciones de abril de 2019, noviembre de 2019 y julio de 2023. Elige una de ellas.";
      if (capa) { mapa.removeLayer(capa); capa = null; capas.clear(); }
      ficha(); return;
    }
    if (provActual && !capa) { dibujar(provActual); return; }
    if (capa) {
      if (geoms.anio !== anioCapa(elec()) && provActual) { dibujar(provActual); return; }
      capa.setStyle(estilo);
      if (seleccionada && capas.get(seleccionada)) { capas.get(seleccionada).setStyle({ weight: 2.5, color: "#12171f" }); capas.get(seleccionada).bringToFront(); }
    }
    leyenda();
    ficha();
  }

  async function dibujar(prov, municipio) {
    const estado = $("#estado-sec");
    estado.textContent = `Cargando las secciones de ${provNombre(prov)}…`;
    const anio = anioCapa(elec());
    const clave = `${anio}/${prov}`;
    try {
      const [d, g] = await Promise.all([
        datos[prov] || pedir(`data/sec/${prov}.json`),
        geoms[clave] || pedir(`data/sec/g/${anio}/${prov}.geojson`)]);
      datos[prov] = d; geoms[clave] = g; geoms.anio = anio;
    } catch (err) {
      estado.textContent = anio === 2019 && String(err.message).includes("404")
        ? "Los límites de las secciones de 2019 todavía no están publicados en esta versión de la web (ver HANDOFF.md). Prueba con julio de 2023."
        : "No se pudieron cargar las secciones: " + err.message;
      return;
    }
    provActual = prov;
    if (capa) mapa.removeLayer(capa);
    capas.clear();
    capa = L.geoJSON(geoms[clave], {
      style: estilo,
      onEachFeature: (ft, l) => {
        const s = ft.properties.s; capas.set(s, l);
        l.on({ mouseover: () => { $("#hover-sec").textContent = hover(s); }, click: () => seleccionar(s) });
      },
    }).addTo(mapa);
    const cubiertas = [...capas.keys()].filter((s) => datos[prov][s] && datos[prov][s][elec()]).length;
    estado.textContent = `${provNombre(prov)}: ${num(capas.size)} secciones dibujadas (límites INE ${anio}); ${num(cubiertas)} con resultados en esta elección.`;
    let b = null;
    capas.forEach((l, s) => { if (!municipio || s.startsWith(municipio)) b = b ? b.extend(l.getBounds()) : L.latLngBounds(l.getBounds().getSouthWest(), l.getBounds().getNorthEast()); });
    if (b) mapa.fitBounds(b, { padding: [20, 20], maxZoom: municipio ? 14 : 11 });
    leyenda(); ficha();
  }

  function buscador() {
    const campo = $("#buscar-sec"), caja = $("#sugerencias-sec");
    campo.addEventListener("input", () => {
      const q = norm(campo.value.trim()); caja.replaceChildren();
      if (q.length < 2) { caja.hidden = true; return; }
      const lista = INDICE.filter((x) => x.k.includes(q)).sort((a, b) => (b.k.startsWith(q) - a.k.startsWith(q)) || a.k.length - b.k.length).slice(0, 8);
      lista.forEach((x) => {
        const b = el("button", "sugerencia", `${x.n} · ${provNombre(x.id.slice(0, 2))}`); b.type = "button";
        b.addEventListener("click", () => { campo.value = x.n; caja.hidden = true; seleccionada = null; dibujar(x.id.slice(0, 2), x.id); });
        caja.appendChild(b);
      });
      caja.hidden = lista.length === 0;
    });
    campo.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { const b = caja.querySelector("button"); if (b) b.click(); } });
    const sel = $("#ir-provincia-sec");
    Object.entries(DATOS.elecciones[DATOS.elecciones.length - 1].provincias).sort((a, b) => a[1].nombre.localeCompare(b[1].nombre, "es"))
      .forEach(([cod, p]) => sel.appendChild(Object.assign(el("option"), { value: cod, textContent: p.nombre })));
    sel.addEventListener("change", () => { if (sel.value) { seleccionada = null; dibujar(sel.value); } });
    $("#modo-sec").addEventListener("change", pintar);
  }

  async function cargar() {
    const estado = $("#estado-sec");
    if (location.protocol === "file:") { estado.textContent = "El mapa de secciones necesita servirse por HTTP (Netlify o `python -m http.server --directory web`)."; return; }
    try {
      if (!window.L) await Promise.all([cargarCss(`${LEAFLET}.min.css`), cargarScript(`${LEAFLET}.min.js`)]);
      const [ix, partidos] = await Promise.all([pedir("data/indice.json"), pedir("data/partidos_sec.json")]);
      PARTIDOS = partidos;
      ix.forEach(([id, n]) => { MUNI[id] = n; });
      INDICE = ix.map(([id, n]) => ({ id, n, k: norm(n) }));
      mapa = L.map("mapa-sec", { preferCanvas: true, zoomSnap: 0.25, minZoom: 4, maxZoom: 17 });
      mapa.attributionControl.setPrefix(false);
      mapa.attributionControl.addAttribution("Cartografía: INE (CC BY 4.0) · Resultados: Ministerio del Interior");
      mapa.fitBounds([[35.9, -9.6], [43.9, 4.6]]);
      buscador();
      if (disponible()) await dibujar("28", "28079"); else pintar();
    } catch (err) { estado.textContent = "No se pudo cargar el mapa de secciones: " + err.message; promesa = null; }
  }

  return {
    iniciar() { if (!promesa) promesa = cargar(); setTimeout(() => mapa && mapa.invalidateSize(), 50); return promesa; },
    pintar,
    limpiar() { seleccionada = null; pintar(); },
  };
})();
