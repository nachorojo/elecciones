/* Configuración de la web. `vivo`: de dónde lee la página el recuento del 29N (la que escribe
   pipeline/captura_29n.py). Puede ser un fichero de la propia web o una dirección completa
   (por ejemplo, un almacén externo con permiso de lectura pública y CORS). */
window.CONFIG = {
  vivo: "data/vivo_29n.json",
  refresco: 30            // segundos entre consultas
};
