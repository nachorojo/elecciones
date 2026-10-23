/* Vista de municipios: mapa (Leaflet, sin mapa base), buscador y ficha. Se carga bajo demanda.
   Datos: data/municipios.geojson (INE, CC BY 4.0), data/mun/NN.json y data/partidos.json (Interior).
   Formato de un municipio: {n, h: {elección: [censo, votantes, blancos, nulos, candidaturas, [[cód, votos], ...]]}} */
const Municipal = (() => {
  const LEAFLET = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet";
  let mapa = null, capa = null, MUN = {}, PARTIDOS = {}, INDICE = [], seleccionado = null, promesa = null;
  const capas = new Map();
  let rangoPart = [60, 85];

  const norm = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
  const elec = () => $("#eleccion").value;
  const pedir = async (u) => {
    const r = await fetch(u);
    if (!r.ok) throw new Error(`${u}: ${r.status}`);
    return r.json();
  };
  const cargarScript = (src) => new Promise((ok, ko) => {
    const s = document.createElement("script");
    s.src = src; s.onload = ok; s.onerror = () => ko(new Error("no se pudo cargar " + src));
    document.head.appendChild(s);
  });
  const cargarCss = (href) => new Promise((ok, ko) => {
    const l = document.createElement("link");
    l.rel = "stylesheet"; l.href = href; l.onload = ok; l.onerror = () => ko(new Error("no se pudo cargar " + href));
    document.head.appendChild(l);
  });
  const provNombre = (id) => {
    const p = DATOS.elecciones[DATOS.elecciones.length - 1].provincias[id.slice(0, 2)];
    return p ? p.nombre : id.slice(0, 2);
  };

  function resultado(id) {
    const m = MUN[id];
    const h = m && m.h[elec()];
    if (!h) return null;
    const validos = h[4] + h[2];
    const top = h[5][0];
    const info = top && PARTIDOS[elec()][top[0]];
    return { m, h, validos, top, siglas: info ? info[0] : "—", fam: info ? info[1] : "OTROS",
             cuota: top ? 100 * top[1] / validos : 0, part: 100 * h[1] / h[0] };
  }

  const SIN_DATOS = { fillColor: "#c9cfd8", fillOpacity: 0.3, weight: 0.3, color: "#8d98a6" };
  function estilo(ft) {
    const r = resultado(ft.properties.id);
    if (!r || !r.top) return SIN_DATOS;
    let relleno;
    if ($("#metrica").value === "ganador") {
      const t = Math.min(1, Math.max(0, (r.cuota - 25) / 35));
      relleno = { fillColor: color(r.fam), fillOpacity: 0.3 + 0.65 * t };
    } else {
      const t = Math.min(1, Math.max(0, (r.part - rangoPart[0]) / (rangoPart[1] - rangoPart[0] || 1)));
      relleno = { fillColor: `hsl(215 75% ${88 - 56 * t}%)`, fillOpacity: 0.95 };
    }
    return { ...relleno, weight: 0.3, color: "#5d6b7f" };
  }

  function textoHover(id) {
    const m = MUN[id];
    const r = resultado(id);
    const nombre = m ? `${m.n} (${provNombre(id)})` : id;
    if (!r) return `${nombre}: sin datos en esta elección (el municipio no existía o cambió de código).`;
    return `${nombre}: ${r.siglas} ${dec(r.cuota, 1)} % · participación ${dec(r.part, 1)} % · ${num(r.h[0])} electores`;
  }

  function seleccionar(id, centrar) {
    seleccionado = id;
    capas.forEach((l, k) => { if (k !== id) capa.resetStyle(l); });
    const l = capas.get(id);
    if (l) {
      l.setStyle({ weight: 2.5, color: "#12171f" });
      l.bringToFront();
      if (centrar) mapa.fitBounds(l.getBounds(), { maxZoom: 11, padding: [30, 30] });
    }
    pintar();
  }

  function leyenda() {
    const ley = $("#leyenda");
    ley.replaceChildren();
    const e = elec();
    if ($("#metrica").value === "ganador") {
      ley.appendChild(el("span", null, "Color = candidatura más votada; más intenso = más cuota de voto. Gris = sin datos."));
      const usados = new Set();
      capas.forEach((_, id) => { const r = resultado(id); if (r && r.top) usados.add(COLOR[r.fam] ? r.fam : "OTROS"); });
      [...usados].forEach((f) => {
        const s = el("span"); const i = el("i"); i.style.background = color(f);
        s.append(i, ETIQUETA[f] || f); ley.appendChild(s);
      });
    } else {
      ley.append(`Participación de residentes: ${dec(rangoPart[0], 0)} %`, el("span", "gradiente"), `${dec(rangoPart[1], 0)} % o más (gris = sin datos)`);
    }
  }

  function calcularRango() {
    const v = [];
    capas.forEach((_, id) => { const r = resultado(id); if (r) v.push(r.part); });
    v.sort((a, b) => a - b);
    if (v.length) rangoPart = [v[Math.floor(v.length * 0.02)], v[Math.floor(v.length * 0.98)]];
  }

  function detalle() {
    if (!seleccionado) { pintarDetalle(); return; }
    const id = seleccionado, m = MUN[id], r = resultado(id), e = actual();
    $("#titulo").textContent = `${m.n} (${provNombre(id)})`;
    $("#volver").hidden = false;
    $("#fecha").textContent = `Elecciones generales del ${e.fecha}`;
    const res = $("#resumen"), lista = $("#partidos");
    res.replaceChildren(); lista.replaceChildren();
    if (!r) {
      $("#otros").textContent = "No hay datos de este municipio en esta elección: no existía o tenía otro código (fusión o segregación).";
    } else {
      [[dec(r.part, 2) + " %", "participación"], [num(r.h[0]), "electores"], [num(r.validos), "votos válidos"]]
        .forEach(([v, l]) => { const d = el("div", "dato"); d.append(el("b", null, v), el("span", null, l)); res.appendChild(d); });
      const tope = r.h[5][0] ? r.h[5][0][1] : 1;
      r.h[5].forEach(([cod, v]) => {
        const info = PARTIDOS[elec()][cod] || [cod, "OTROS"];
        const f = el("div", "fila fila-mun");
        const barra = el("div", "barra"); const s = el("span");
        s.style.width = `${100 * v / tope}%`; s.style.background = color(info[1]); barra.appendChild(s);
        f.append(el("div", null, info[0]), barra, el("div", "cifras", `${num(v)} · ${dec(100 * v / r.validos, 2)} %`));
        lista.appendChild(f);
      });
      const resto = r.h[4] - r.h[5].reduce((t, p) => t + p[1], 0);
      $("#otros").textContent = `Resto de candidaturas: ${num(resto)} votos · en blanco: ${num(r.h[2])} (${dec(100 * r.h[2] / r.validos, 2)} % de los válidos) · nulos: ${num(r.h[3])}. Solo se listan las candidaturas con al menos el 1,5 % de los votos válidos.`;
    }
    const hist = $("#historia");
    hist.replaceChildren();
    DATOS.elecciones.forEach((x) => {
      const h = m.h[x.id];
      const top = h && h[5][0];
      const info = top && PARTIDOS[x.id][top[0]];
      const c = el("span", "chip" + (x.id === e.id ? " actual" : ""), `${x.id}: ${info ? info[0] : "—"}`);
      c.style.background = info ? color(info[1]) : "#8d98a6";
      hist.appendChild(c);
    });
  }

  function pintar() {
    if (!capa) return;
    calcularRango();
    capa.setStyle(estilo);
    if (seleccionado && capas.get(seleccionado)) {
      capas.get(seleccionado).setStyle({ weight: 2.5, color: "#12171f" });
      capas.get(seleccionado).bringToFront();
    }
    leyenda();
    detalle();
  }

  function buscador() {
    const campo = $("#buscar"), caja = $("#sugerencias");
    campo.addEventListener("input", () => {
      const q = norm(campo.value.trim());
      caja.replaceChildren();
      if (q.length < 2) { caja.hidden = true; return; }
      const lista = INDICE.filter((x) => x.k.includes(q))
        .sort((a, b) => (b.k.startsWith(q) - a.k.startsWith(q)) || a.k.length - b.k.length).slice(0, 8);
      lista.forEach((x) => {
        const b = el("button", "sugerencia", `${x.n} · ${provNombre(x.id)}`);
        b.type = "button";
        b.addEventListener("click", () => { campo.value = x.n; caja.hidden = true; seleccionar(x.id, true); });
        caja.appendChild(b);
      });
      caja.hidden = lista.length === 0;
    });
    campo.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") { const b = caja.querySelector("button"); if (b) b.click(); }
    });
    const sel = $("#ir-provincia");
    const provs = DATOS.elecciones[DATOS.elecciones.length - 1].provincias;
    Object.entries(provs).sort((a, b) => a[1].nombre.localeCompare(b[1].nombre, "es"))
      .forEach(([cod, p]) => sel.appendChild(Object.assign(el("option"), { value: cod, textContent: p.nombre })));
    sel.addEventListener("change", () => {
      if (!sel.value) return;
      let b = null;
      capas.forEach((l, id) => { if (id.startsWith(sel.value)) b = b ? b.extend(l.getBounds()) : L.latLngBounds(l.getBounds().getSouthWest(), l.getBounds().getNorthEast()); });
      if (b) mapa.fitBounds(b, { padding: [20, 20] });
    });
  }

  async function cargar() {
    const estado = $("#estado-mun");
    if (location.protocol === "file:") {
      estado.textContent = "El mapa municipal necesita servirse por HTTP (Netlify o `python -m http.server --directory web`); no funciona abriendo el fichero directamente.";
      return;
    }
    try {
      await Promise.all([cargarCss(`${LEAFLET}.min.css`), cargarScript(`${LEAFLET}.min.js`)]);
      const cods = Object.keys(DATOS.elecciones[DATOS.elecciones.length - 1].provincias);
      const [geo, partidos, provincias] = await Promise.all([
        pedir("data/municipios.geojson"), pedir("data/partidos.json"), Promise.all(cods.map((c) => pedir(`data/mun/${c}.json`)))]);
      PARTIDOS = partidos;
      provincias.forEach((p) => Object.assign(MUN, p));
      INDICE = Object.entries(MUN).map(([id, m]) => ({ id, n: m.n, k: norm(m.n) }));
      mapa = L.map("mapa-mun", { preferCanvas: true, zoomSnap: 0.25, minZoom: 4, maxZoom: 13, zoomControl: true });
      mapa.attributionControl.setPrefix(false);
      mapa.attributionControl.addAttribution("Cartografía: INE (CC BY 4.0) · Resultados: Ministerio del Interior");
      capa = L.geoJSON(geo, {
        style: estilo,
        onEachFeature: (ft, l) => {
          const id = ft.properties.id;
          capas.set(id, l);
          l.on({ mouseover: () => { $("#hover").textContent = textoHover(id); }, click: () => seleccionar(id, false) });
        },
      }).addTo(mapa);
      mapa.fitBounds([[35.9, -9.6], [43.9, 4.6]]);
      buscador();
      const sinMapa = Object.keys(MUN).filter((id) => !capas.has(id)).length;
      const nuevos = [...capas.keys()].filter((id) => !MUN[id]).length;
      estado.textContent = `${num(capas.size)} municipios en el mapa (límites actuales del INE). ${num(sinMapa)} municipios históricos ya no existen por fusión y solo salen en la búsqueda; ${num(nuevos)} municipio${nuevos === 1 ? " es nuevo" : "s son nuevos"} (sin historia electoral propia).`;
      pintar();
    } catch (err) {
      estado.textContent = "No se pudo cargar el mapa municipal: " + err.message;
      promesa = null;
    }
  }

  return {
    iniciar() { if (!promesa) promesa = cargar(); setTimeout(() => mapa && mapa.invalidateSize(), 50); return promesa; },
    pintar,
    limpiar() { seleccionado = null; if (capa) { capas.forEach((l) => capa.resetStyle(l)); } },
  };
})();
