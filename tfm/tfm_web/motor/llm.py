from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from .datos import ELECCIONES, PARTIDOS

SERVIDOR = "http://localhost:11434"
MODELOS_PREFERIDOS = ["qwen2.5:7b", "qwen2.5:3b", "llama3.1:8b", "llama3.2:3b", "gemma2:9b"]

ESQUEMA_INTENCION = """Devuelve SOLO un objeto JSON valido, sin texto alrededor, con estas claves:
{"tipo": "<uno de: resultado, evolucion, ranking, comparar, mesas, futuro, escenario, ayuda>",
 "metrica": "<opcional>", "orden": "<desc o asc>", "nivel": "<municipio, provincia o ccaa>"}

Significado de cada tipo:
- resultado: quien gano o que resultado hubo en un sitio y una eleccion concretos.
- evolucion: como ha cambiado algo a lo largo de varias elecciones.
- ranking: que sitios tienen el valor mas alto o mas bajo de algo.
- comparar: contraste explicito entre dos o mas territorios.
- mesas: detalle por mesa o seccion censal de un municipio.
- futuro: pregunta por elecciones que aun no se han celebrado.
- escenario: simulacion del tipo "que pasaria si un partido sacara X".
- ayuda: la pregunta no trata de datos electorales."""


def _peticion(ruta, cuerpo=None, tiempo=120):
    url = f"{SERVIDOR}{ruta}"
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(url, data=datos,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pet, timeout=tiempo) as resp:
        return json.loads(resp.read().decode())


class Ollama:

    def __init__(self, modelo=None):
        self.modelo = modelo
        self.error = None
        self.modelos = []
        self.comprobar()

    def comprobar(self):
        try:
            datos = _peticion("/api/tags", tiempo=4)
        except Exception as exc:
            self.error = f"Ollama no responde en {SERVIDOR} ({type(exc).__name__})"
            self.modelo = None
            return False
        self.modelos = [m["name"] for m in datos.get("models", [])]
        self.error = None
        if self.modelo and self.modelo in self.modelos:
            return True
        for preferido in MODELOS_PREFERIDOS:
            for disponible in self.modelos:
                if disponible.startswith(preferido.split(":")[0]) and preferido.split(":")[1] in disponible:
                    self.modelo = disponible
                    return True
        if self.modelos:
            self.modelo = self.modelos[0]
            return True
        self.error = "Ollama está levantado pero no tiene ningún modelo descargado"
        self.modelo = None
        return False

    @property
    def disponible(self):
        return self.modelo is not None

    def _generar(self, sistema, usuario, json_forzado=False, tokens=700, temperatura=0.2):
        cuerpo = {
            "model": self.modelo,
            "messages": [{"role": "system", "content": sistema},
                         {"role": "user", "content": usuario}],
            "stream": False,
            "options": {"temperature": temperatura, "num_predict": tokens},
        }
        if json_forzado:
            cuerpo["format"] = "json"
        datos = _peticion("/api/chat", cuerpo)
        return datos["message"]["content"].strip()

    def intencion(self, pregunta, pistas, historial=None):
        contexto = []
        if pistas.get("territorios"):
            contexto.append("Territorios detectados: " +
                            ", ".join(f"{t['nombre']} ({t['nivel']})"
                                      for t in pistas["territorios"]))
        if pistas.get("elecciones"):
            contexto.append("Convocatorias detectadas: " + ", ".join(pistas["elecciones"]))
        if pistas.get("partidos"):
            contexto.append("Partidos detectados: " + ", ".join(pistas["partidos"]))
        if historial:
            contexto.append("Preguntas anteriores: " + " | ".join(historial[-3:]))
        sistema = ("Eres un clasificador de preguntas sobre elecciones generales espanolas. "
                   "No respondes preguntas, solo las clasificas. " + ESQUEMA_INTENCION)
        usuario = f"Pregunta: {pregunta}\n" + "\n".join(contexto)
        try:
            bruto = self._generar(sistema, usuario, json_forzado=True, tokens=200)
            return json.loads(re.search(r"\{.*\}", bruto, re.S).group(0))
        except Exception:
            return None

    def redactar(self, pregunta, datos_texto, tabla_texto=""):
        sistema = (
            "Eres un analista electoral que responde en espanol de Espana, en tono claro y "
            "directo, sin florituras ni emojis.\n"
            "REGLA ABSOLUTA: solo puedes usar las cifras que aparecen en los DATOS. "
            "Nunca inventes, redondees a tu gusto ni estimes una cifra que no este ahi. "
            "Si falta un dato, di que no lo tienes.\n"
            "Escribe entre dos y cinco frases. Usa los separadores espanoles: punto para los "
            "miles y coma para los decimales, tal y como vienen en los datos. "
            "Puedes destacar nombres con **negrita**. No uses listas ni titulos.")
        usuario = (f"Pregunta del usuario: {pregunta}\n\nDATOS VERIFICADOS:\n{datos_texto}\n"
                   f"{tabla_texto}\n\nRedacta la respuesta usando solo esas cifras.")
        try:
            return self._generar(sistema, usuario, tokens=500, temperatura=0.3)
        except Exception as exc:
            self.error = str(exc)
            return None
