// Capturas de los gráficos de directo (y de las piezas para redes) con un fichero de datos dado, sin tocar la web.
//
//   node herramientas/capturas_directo.js DATOS.json CARPETA_SALIDA [prefijo]
//
// DATOS.json tiene la forma de web/data/vivo_29n.json (por ejemplo, el de un envío ya publicado:
//   git show <commit>:web/data/vivo_29n.json > envio.json). Sirve para revisar cómo queda cada gráfico en cada
// momento de la jornada. Necesita Playwright (viene instalado en las sesiones de Claude en la nube).
const http = require("http"), fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const [datos, salida, prefijo = ""] = process.argv.slice(2);
if (!datos || !salida) { console.error("uso: node herramientas/capturas_directo.js DATOS.json CARPETA [prefijo]"); process.exit(1); }
const WEB = path.join(__dirname, "..", "web");
const TIPOS = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".png": "image/png" };
const servidor = http.createServer((req, res) => {
  const ruta = decodeURIComponent(req.url.split("?")[0]);
  const f = ruta.endsWith("/data/vivo_29n.json") ? datos : path.join(WEB, ruta.endsWith("/") ? ruta + "index.html" : ruta);
  fs.readFile(f, (e, b) => { res.writeHead(e ? 404 : 200, { "Content-Type": TIPOS[path.extname(f)] || "application/octet-stream" }); res.end(e ? "" : b); });
});
const DIRECTO = [["arco", "vista=arco"], ["faldon", "vista=faldon&fondo=oscuro"], ["columna", "vista=columna&fondo=oscuro"],
  ["participacion", "vista=participacion"], ["provincia28", "vista=provincia&provincia=28"], ["provincia08", "vista=provincia&provincia=08"],
  ["ticker", "vista=ticker&fondo=oscuro"]];
const REDES = [["redes_historia", "formato=historia&limpio", 1080, 1920], ["redes_reel", "formato=reel&limpio", 1080, 1920],
  ["redes_post", "formato=post&limpio", 1080, 1350], ["redes_historia_participacion", "formato=historia&tema=participacion&limpio", 1080, 1920],
  ["redes_post_madrid", "formato=post&tema=provincia&provincia=28&limpio", 1080, 1350], ["redes_reel_guias", "formato=reel&limpio&guias", 1080, 1920]];
(async () => {
  await new Promise((ok) => servidor.listen(0, "127.0.0.1", ok));
  const base = `http://127.0.0.1:${servidor.address().port}/directo/`;
  fs.mkdirSync(salida, { recursive: true });
  const nav = await chromium.launch();
  const foto = async (nombre, url, w, h) => {
    const pag = await nav.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    await pag.goto(url); await pag.waitForTimeout(900);
    await pag.screenshot({ path: path.join(salida, prefijo + nombre + ".png") });
    await pag.close();
  };
  for (const [n, q] of DIRECTO) await foto(n, base + "?" + q, 1920, 1080);
  if (fs.existsSync(path.join(WEB, "directo", "redes.html"))) for (const [n, q, w, h] of REDES) await foto(n, base + "redes.html?" + q, w, h);
  await nav.close(); servidor.close();
  console.log("capturas en", salida);
})();
