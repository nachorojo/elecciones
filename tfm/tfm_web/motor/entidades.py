from __future__ import annotations

import difflib
import re
import unicodedata
from collections import defaultdict

from .datos import BLOQUES, ELECCIONES, METRICAS, PARTIDOS, SOCIO, SOCIO_ETIQUETA

PALABRAS_VACIAS = {
    "el", "la", "los", "las", "de", "del", "en", "y", "a", "al", "un", "una", "que", "quien",
    "quienes", "como", "cual", "cuales", "cuanto", "cuantos", "cuanta", "cuantas", "donde",
    "cuando", "por", "para", "con", "sin", "sobre", "es", "fue", "son", "eran", "hay", "habia",
    "me", "te", "se", "lo", "le", "su", "sus", "mi", "tu", "dime", "dame", "quiero", "saber",
    "puedes", "decir", "muestrame", "ensename", "cuentame", "ano", "anos", "elecciones",
    "eleccion", "generales", "resultado", "resultados", "voto", "votos", "electoral",
    "paso", "pasa", "pasaron", "gano", "gana", "ganaron", "saco", "saca", "sacaron", "dice",
    "sale", "salio", "vale", "va", "van", "fueron", "tiene", "tienen", "habra", "sera",
    "mas", "menos", "mejor", "peor", "mucho", "poco", "todo", "toda", "todos", "todas",
    "campo", "puebla", "union", "villa", "real", "nuevo", "nueva", "alta", "baja", "medio",
    "mesa", "mesas", "seccion", "secciones", "distrito", "distritos", "colegio", "censo",
    "provincia", "provincias", "comunidad", "comunidades", "municipio", "municipios",
    "pueblo", "pueblos", "ciudad", "ciudades", "partido", "partidos", "ranking", "lista",
}

ALIAS_CCAA = {
    "andalucia": "01", "aragon": "02", "asturias": "03", "principado de asturias": "03",
    "baleares": "04", "islas baleares": "04", "illes balears": "04", "les illes balears": "04",
    "canarias": "05", "islas canarias": "05", "cantabria": "06",
    "castilla la mancha": "07", "castilla-la mancha": "07", "la mancha": "07",
    "castilla y leon": "08", "castilla leon": "08",
    "cataluna": "09", "catalunya": "09", "cat": "09",
    "extremadura": "10", "galicia": "11", "galiza": "11",
    "madrid comunidad": "12", "comunidad de madrid": "12",
    "navarra": "13", "comunidad foral de navarra": "13", "nafarroa": "13",
    "pais vasco": "14", "euskadi": "14", "euskal herria": "14", "vascongadas": "14",
    "murcia region": "15", "region de murcia": "15",
    "la rioja": "16", "rioja": "16",
    "comunidad valenciana": "17", "comunitat valenciana": "17", "valencia comunidad": "17",
    "pais valenciano": "17", "levante": "17",
    "ceuta": "18", "melilla": "19",
}

ALIAS_PROVINCIA = {
    "alava": "01", "araba": "01",
    "albacete": "02", "alicante": "03", "alacant": "03", "almeria": "04", "avila": "05",
    "badajoz": "06", "barcelona": "08", "burgos": "09", "caceres": "10", "cadiz": "11",
    "castellon": "12", "castello": "12", "ciudad real": "13", "cordoba": "14",
    "a coruna": "15", "la coruna": "15", "coruna": "15", "cuenca": "16", "girona": "17",
    "gerona": "17", "granada": "18", "guadalajara": "19", "guipuzcoa": "20", "gipuzkoa": "20",
    "huelva": "21", "huesca": "22", "jaen": "23", "leon": "24", "lleida": "25", "lerida": "25",
    "lugo": "27", "malaga": "29", "ourense": "32", "orense": "32", "palencia": "34",
    "las palmas": "35", "gran canaria": "35", "pontevedra": "36", "salamanca": "37",
    "santa cruz de tenerife": "38", "tenerife": "38", "segovia": "40", "sevilla": "41",
    "soria": "42", "tarragona": "43", "teruel": "44", "toledo": "45", "valladolid": "47",
    "vizcaya": "48", "bizkaia": "48", "bilbao provincia": "48", "zamora": "49", "zaragoza": "50",
}

ALIAS_PARTIDO = {
    "pp": "pp", "partido popular": "pp", "populares": "pp", "el pp": "pp", "pepe": "pp",
    "psoe": "psoe", "partido socialista": "psoe", "socialistas": "psoe", "psc": "psoe",
    "vox": "vox",
    "podemos": "podemos_sumar", "unidas podemos": "podemos_sumar",
    "unidos podemos": "podemos_sumar", "sumar": "podemos_sumar", "up": "podemos_sumar",
    "en comun podem": "podemos_sumar", "en marea": "podemos_sumar",
    "ciudadanos": "cs", "cs": "cs", "c s": "cs", "ciutadans": "cs", "naranjas": "cs",
    "iu": "iu", "izquierda unida": "iu",
    "upyd": "upyd", "union progreso y democracia": "upyd",
    "erc": "erc", "esquerra": "erc", "esquerra republicana": "erc",
    "ciu": "ciu_jxcat", "convergencia": "ciu_jxcat", "jxcat": "ciu_jxcat", "junts": "ciu_jxcat",
    "cdc": "ciu_jxcat", "pdecat": "ciu_jxcat",
    "pnv": "pnv", "eaj": "pnv", "partido nacionalista vasco": "pnv",
    "bildu": "eh_bildu", "eh bildu": "eh_bildu", "amaiur": "eh_bildu", "hb": "eh_bildu",
    "herri batasuna": "eh_bildu",
    "bng": "bng", "bloque nacionalista galego": "bng",
    "cc": "cc", "coalicion canaria": "cc",
    "compromis": "compromis",
}

ALIAS_METRICA = {
    "participacion": "participacion", "abstencion": "abstencion",
    "voto en blanco": "pct_blancos", "blancos": "pct_blancos", "votos en blanco": "pct_blancos",
    "voto nulo": "pct_nulos", "nulos": "pct_nulos", "votos nulos": "pct_nulos",
    "izquierda": "pct_izquierda_total", "izquierdas": "pct_izquierda_total",
    "derecha": "pct_derecha_total", "derechas": "pct_derecha_total",
    "nacionalismo": "pct_nacionalista", "nacionalista": "pct_nacionalista",
    "nacionalistas": "pct_nacionalista", "independentismo": "pct_nacionalista",
    "indice": "indice_izq_der", "indice ideologico": "indice_izq_der",
    "posicion ideologica": "posicion_ideologica", "ideologia": "posicion_ideologica",
    "censo": "censo_escrutinio", "electores": "censo_escrutinio",
    "votantes": "votantes",
    "paro": "tasa_paro", "desempleo": "tasa_paro", "tasa de paro": "tasa_paro",
    "pib": "pib_per_capita", "pib per capita": "pib_per_capita", "riqueza": "pib_per_capita",
    "edad media": "edad_media", "edad": "edad_media",
    "escolarizacion": "escolarizacion", "estudios": "escolarizacion",
    "esperanza de vida": "esperanza_vida",
    "inmigracion": "pct_inmigrantes", "extranjeros": "pct_inmigrantes",
    "inmigrantes": "pct_inmigrantes",
    "mujeres": "pct_mujeres",
    "criminalidad": "tasa_criminalidad_1000", "delincuencia": "tasa_criminalidad_1000",
}


def normalizar(texto):
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9\s/'-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def variantes_nombre(nombre):
    base = normalizar(nombre)
    salida = {base}
    for trozo in re.split(r"[/]", base):
        trozo = trozo.strip()
        if len(trozo) > 2:
            salida.add(trozo)
    m = re.match(r"^(.*),\s*(.+)$", base)
    if m:
        salida.add(f"{m.group(2)} {m.group(1)}".strip())
        salida.add(m.group(1).strip())
    salida.add(re.sub(r"^(el|la|los|las|les|o|a)\s+", "", base))
    return {s for s in salida if len(s) > 2}


class Catalogo:

    def __init__(self, almacen):
        self.almacen = almacen
        self.indice = defaultdict(list)
        self._construir()
        self.claves = list(self.indice)
        self.por_inicial = defaultdict(list)
        for k in self.claves:
            self.por_inicial[k[0]].append(k)

    def _añadir(self, texto, nivel, codigo, prioridad):
        clave = normalizar(texto)
        if len(clave) < 3:
            return
        entrada = (nivel, codigo, prioridad)
        if entrada not in self.indice[clave]:
            self.indice[clave].append(entrada)

    def _construir(self):
        a = self.almacen
        for alias, cod in ALIAS_CCAA.items():
            self._añadir(alias, "ccaa", cod, 3_000_000)
        for cod, nombre in a.nombres_ccaa.items():
            for v in variantes_nombre(nombre):
                self._añadir(v, "ccaa", cod, 3_000_000)
        for alias, cod in ALIAS_PROVINCIA.items():
            self._añadir(alias, "provincia", cod, 5_000_000)
        for cod, nombre in a.nombres_prov.items():
            for v in variantes_nombre(nombre):
                self._añadir(v, "provincia", cod, 5_000_000)
        for mid, nombre in a.nombres_mun.items():
            pob = a.poblacion_mun.get(mid, 0) or 0
            for v in variantes_nombre(nombre):
                self._añadir(v, "municipio", mid, int(pob))
        for _, fila in a.mun[["mun_id", "municipio"]].drop_duplicates().iterrows():
            pob = a.poblacion_mun.get(fila["mun_id"], 0) or 0
            for v in variantes_nombre(fila["municipio"]):
                self._añadir(v, "municipio", fila["mun_id"], int(pob))
        for clave in ("espana", "spain", "nacional", "todo el pais", "todo espana",
                      "conjunto de espana", "a nivel nacional"):
            self._añadir(clave, "nacional", None, 9_000_000)

    def buscar(self, texto, limite=6):
        clave = normalizar(texto)
        if clave in self.indice:
            opciones = sorted(self.indice[clave], key=lambda e: -e[2])
            return [self._describir(n, c) for n, c, _ in opciones[:limite]]
        candidatos = self.por_inicial.get(clave[0], []) if clave else []
        cercanos = difflib.get_close_matches(clave, candidatos or self.claves, n=4, cutoff=0.82)
        salida = []
        for c in cercanos:
            for n, cod, _ in sorted(self.indice[c], key=lambda e: -e[2])[:2]:
                d = self._describir(n, cod)
                if d not in salida:
                    salida.append(d)
        return salida[:limite]

    def _describir(self, nivel, codigo):
        return {"nivel": nivel, "codigo": codigo, "nombre": self.almacen.nombre(nivel, codigo),
                "contexto": self._contexto(nivel, codigo)}

    def _contexto(self, nivel, codigo):
        a = self.almacen
        if nivel == "municipio":
            prov = a.prov_de_mun.get(codigo)
            return f"municipio de {a.nombres_prov.get(prov, '')}"
        if nivel == "provincia":
            ccaa = a.ccaa_de_prov.get(codigo)
            return f"provincia de {a.nombres_ccaa.get(ccaa, '')}"
        if nivel == "ccaa":
            return "comunidad autónoma"
        return "conjunto del país"

    def extraer_territorios(self, frase, maximo=3):
        palabras = normalizar(frase).split()
        encontrados, usados = [], set()
        for largo in range(min(6, len(palabras)), 0, -1):
            for i in range(len(palabras) - largo + 1):
                if any(j in usados for j in range(i, i + largo)):
                    continue
                trozo = " ".join(palabras[i:i + largo])
                if largo == 1 and (trozo in PALABRAS_VACIAS or trozo.isdigit()):
                    continue
                if trozo in self.indice:
                    opciones = sorted(self.indice[trozo], key=lambda e: -e[2])
                    nivel, codigo, _ = opciones[0]
                    encontrados.append({
                        "nivel": nivel, "codigo": codigo,
                        "nombre": self.almacen.nombre(nivel, codigo), "texto": trozo,
                        "alternativas": [self._describir(n, c) for n, c, _ in opciones[1:4]],
                    })
                    usados.update(range(i, i + largo))
        return encontrados[:maximo]

    def extraer_partidos(self, frase):
        texto = normalizar(frase)
        salida = []
        for alias in sorted(ALIAS_PARTIDO, key=len, reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", texto):
                clave = ALIAS_PARTIDO[alias]
                if clave not in salida:
                    salida.append(clave)
        return salida

    def extraer_elecciones(self, frase):
        texto = normalizar(frase)
        salida, ambigua = [], False
        menciona_2019 = bool(re.search(r"\b2019\b", texto))
        if menciona_2019 and re.search(r"\babril\b|\b2019\s*a\b", texto):
            salida.append("2019a")
        if menciona_2019 and re.search(r"\bnoviembre\b|\b2019\s*b\b", texto):
            salida.append("2019b")
        for anio in re.findall(r"\b(19\d{2}|20\d{2})\b", texto):
            if anio == "2019":
                if not salida:
                    salida.extend(["2019a", "2019b"])
                    ambigua = True
            elif anio in ELECCIONES:
                salida.append(anio)
        if re.search(r"ultim[ao]s?|mas recientes?|actual", texto) and not salida:
            salida.append("2023")
        vistos, unicos = set(), []
        for e in salida:
            if e not in vistos:
                vistos.add(e)
                unicos.append(e)
        return unicos, ambigua

    def extraer_metrica(self, frase):
        texto = normalizar(frase)
        for alias in sorted(ALIAS_METRICA, key=len, reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", texto):
                return ALIAS_METRICA[alias]
        return None

    def etiqueta_metrica(self, metrica):
        if metrica in METRICAS:
            return METRICAS[metrica][0]
        if metrica in SOCIO_ETIQUETA:
            return SOCIO_ETIQUETA[metrica]
        if metrica == "abstencion":
            return "Abstención"
        if metrica and metrica.startswith("pct_"):
            clave = metrica[4:]
            if clave in PARTIDOS:
                return f"Voto a {PARTIDOS[clave][0]}"
            if clave in BLOQUES:
                return f"Voto {BLOQUES[clave][0].lower()}"
        return metrica or ""
