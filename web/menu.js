/* Menú común de las páginas de uso interno. Se inserta debajo de la cabecera.
   En páginas de una subcarpeta: <script src="../menu.js" data-base="../"></script> */
(function () {
  const base = document.currentScript.dataset.base || "";
  const ENTRADAS = [
    ["Resultados y 29N en directo", "index.html"],
    ["Simulador de escaños", "index.html?simulador"],
    ["Proyección de la noche", "proyeccion.html"],
    ["Gráficos de directo (OBS)", "directo/galeria.html"],
    ["Piezas para redes", "directo/redes.html"],
    ["Pantallas exteriores", "pantallas.html"],
  ];
  const aqui = location.pathname.replace(/\/$/, "/index.html");
  const sim = new URLSearchParams(location.search).has("simulador");
  const nav = document.createElement("nav");
  nav.className = "menu";
  nav.setAttribute("aria-label", "Secciones");
  ENTRADAS.forEach(([texto, destino]) => {
    const a = document.createElement("a");
    a.href = base + destino;
    a.textContent = texto;
    const [ruta, consulta] = destino.split("?");
    if (aqui.endsWith("/" + ruta) && (ruta !== "index.html" || sim === Boolean(consulta))) a.setAttribute("aria-current", "page");
    nav.appendChild(a);
  });
  const cab = document.querySelector("header.cabecera");
  if (cab) cab.after(nav); else document.body.prepend(nav);
})();
