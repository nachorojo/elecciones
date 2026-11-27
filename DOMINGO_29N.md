# Domingo 29N: guía paso a paso para quien lleve la captura

Escrita el 27 de noviembre de 2026 para que pueda seguirla alguien que no conoce el proyecto.
Si algo no coincide con lo que ves, para y llama a Nacho antes de improvisar.

## Qué es esto, en cuatro líneas

Un programa (la «captura») corre en una ventana de PowerShell en el PC del trabajo de Nacho. Cada minuto pregunta al
Ministerio del Interior si hay datos nuevos. Cuando los hay, los guarda y los sube a la web interna
`https://elecciones2030.netlify.app`, de la que salen los gráficos de OBS y las imágenes para redes.
Tu trabajo es arrancarlo, comprobar que funciona y vigilar la ventana. No hay que programar nada.

**Regla de oro: una sola captura a la vez, en un solo PC.** Dos a la vez se pisan al publicar.

## Lo que necesitas antes de empezar (pídeselo a Nacho)

1. **El PC del trabajo de Nacho, con su sesión de Windows abierta.** La subida a la web usa permisos guardados en su
   usuario: desde otro usuario u otro PC no funciona sin preparación previa.
2. **El usuario y la contraseña de Interior** (vienen en un correo del Ministerio). Te los da Nacho en mano o por un canal
   privado. **No los escribas en ningún fichero, chat ni correo.** Solo se teclean en la ventana de PowerShell.
3. **El teléfono de Nacho** y, si lo tiene, el contacto de soporte de Interior para medios.
4. Que el PC **no se suspenda ni se apague** en todo el día (Configuración → Sistema → Energía → Suspender: «Nunca»).
   No cierres la sesión ni la tapa si es portátil.

## Horario del domingo

| Hora | Qué manda Interior | Qué haces tú |
|---|---|---|
| 9:00 | Abren los colegios | Nada |
| 13:00 | — | Estás en el PC. Pasos 1 a 5 (preparar y comprobar) |
| 13:45 | — | Paso 6: arrancar la captura |
| 14:00 | Primer avance de participación | Paso 7: comprobar que la web lo enseña |
| 14:00–18:00 | Poco movimiento | Mirar la ventana cada media hora |
| 18:00 | Segundo avance de participación | Comprobar otra vez la web |
| 19:30 | — | Repaso general antes del recuento (paso 8) |
| 20:00 | Cierran los colegios en la península; empieza el recuento | Mirar si empiezan a llegar votos (puede que no hasta las 21:00) |
| 21:00 | Cierra Canarias; Interior publica resultados | Datos nuevos cada 3 minutos, más o menos |
| 21:00–00:30 | Recuento | Vigilar la ventana (paso 9) |
| Cuando el recuento se pare cerca del 100 % | Fin del recuento provisional | Paso 10: parar y bajar los ficheros por mesa |

Si no se puede estar a las 13:00: lo más tarde que se debe arrancar es a las **17:30**. Se pierde solo enseñar el avance
de las 14:00 durante la tarde. Más tarde no deja margen para arreglar nada antes de las 20:00.

No sabemos a qué hora empieza Interior a mandar la constitución de mesas, ni si da recuento a los medios entre las
20:00 y las 21:00. Si a las 20:15 no hay votos, es normal.

---

## Paso 1. Abrir PowerShell dentro de la carpeta `repo`

1. Abre el Explorador de archivos y ve a esta carpeta (está en el OneDrive de Nacho):
   `1. MIS DOCUMENTOS\_____IA_____\Claude\Proyectos Claude\Elecciones 2026\repo`
2. Comprueba que estás **dentro de `repo`**: debes ver las carpetas `pipeline`, `web` y `tests`, y este fichero.
   Si ves una carpeta `repo` y otra `datos`, estás un nivel por encima: entra en `repo`.
3. Con la tecla Mayúsculas pulsada, clic derecho en un hueco vacío de la carpeta → «Abrir en Terminal» (o «Abrir la ventana
   de PowerShell aquí»).
4. Se abre una ventana oscura. La línea donde escribes debe terminar en `...\Elecciones 2026\repo>`.

**Todo lo que sigue se escribe en esa misma ventana**, una orden cada vez, pulsando Intro después de cada una.
Para pegar en PowerShell: clic derecho, o Ctrl+V.

## Paso 2. Traer la última versión y comprobar que el programa está sano

```powershell
git pull
```
Debe acabar con `Already up to date.` o con una lista de ficheros actualizados. Si pide usuario o contraseña, o da un
error en rojo, para y llama a Nacho.

```powershell
python -m pytest tests/test_captura_29n.py tests/test_escrutinio_29n.py -q
```
Tarda unos segundos y debe acabar con una línea verde que diga `passed` (por ejemplo `25 passed`; el número puede ser
mayor). Si dice `failed` o `error`, para y llama a Nacho.

Si en lugar de eso sale `No module named ...`, falta activar el entorno de Python. Prueba esto y repite la orden anterior:
```powershell
& "$env:LOCALAPPDATA\venvs\elecciones\Scripts\Activate.ps1"
```
(Si funciona, la línea empezará por `(elecciones)`. Tendrás que repetirlo cada vez que abras una ventana nueva.)

## Paso 3. Escribir las tres variables de Interior

Son tres órdenes. **Las comillas son simples** (`'`, la tecla a la derecha del cero), no dobles. Sustituye los puntos
suspensivos por el usuario y la contraseña que te dio Nacho, sin espacios delante ni detrás:

```powershell
$env:ELECCIONES_API_URL='https://prensa.29neleccionesgenerales.es'
```
```powershell
$env:ELECCIONES_API_USER='...'
```
```powershell
$env:ELECCIONES_API_PASS='...'
```

No responden nada: es normal. **Estas variables solo existen en esta ventana.** Si la cierras, o abres otra, hay que
volver a escribirlas.

## Paso 4. Comprobar que Interior te deja entrar

Copia esta orden tal cual, sin cambiar nada:

```powershell
curl.exe -s -o NUL -w "%{http_code}" -u "$($env:ELECCIONES_API_USER):$($env:ELECCIONES_API_PASS)" "$env:ELECCIONES_API_URL/descargas/csv/data/getEnvio/2"
```

- Si imprime **`200`**: correcto, sigue.
- Si imprime **`401`**: usuario o contraseña mal escritos. Repite el paso 3 con cuidado (mayúsculas, comillas simples) y
  vuelve a probar **una o dos veces, no más**. Si sigue, llama a Nacho.
- Si imprime **`403`** u otra cosa: no insistas (Interior puede bloquear al usuario si se reintenta sin parar).
  Apunta la hora y llama a Nacho.

## Paso 5. Comprobar que el PC puede subir a la web

```powershell
git push --dry-run
```
Debe responder `Everything up-to-date` o un par de líneas con el nombre de la rama, **sin pedir usuario ni contraseña**.
Si los pide o da error, llama a Nacho: sin esto la web no se actualiza.

## Paso 6. Arrancar la captura (a las 13:45)

```powershell
python -m pipeline.captura_29n --publicar --cada-previa 10
```

**Sin la palabra `--simulacro`.** Esa era para las pruebas; el domingo no se pone.

Qué debes ver:
- Primero, una línea parecida a `Capturando en ...\datos\29n_envios cada 60 s. Ctrl+C para parar.`
- Si aparece `La página tenía datos de un simulacro: se ha vaciado.`, es correcto.
- Después, **una línea nueva cada vez que Interior manda datos**, con la hora, el número de envío y el porcentaje
  escrutado. Entre envío y envío la ventana se queda quieta: es normal.
- Hasta las 20:00 a veces verás `confirmado en local; sube con el siguiente`. Es normal: antes del recuento solo se sube
  a la web cada diez minutos, para no gastar.

**No cierres esta ventana, no escribas en ella y no pulses Ctrl+C** hasta el paso 10. Si necesitas otra ventana de
PowerShell para algo, abre una nueva.

No abras con Excel el fichero `registro.csv` mientras la captura esté en marcha (lo bloquea). Si quieres mirarlo, usa el
Bloc de notas.

## Paso 7. Comprobar que la web enseña los datos

Abre en el navegador (Chrome o Edge):

- **Web general:** `https://elecciones2030.netlify.app` → en el desplegable de elecciones, «29 de noviembre de 2026».
- **Gráficos para OBS:** `https://elecciones2030.netlify.app/directo/galeria.html`
- **Imágenes para redes:** `https://elecciones2030.netlify.app/directo/redes.html`

Qué debe verse en cada momento:
- **Antes de las 14:00:** mesas constituidas (un porcentaje) y los avances como «pendiente».
- **Poco después de las 14:00:** el avance de las 14:00, comparado con 2023.
- **Poco después de las 18:00:** los dos avances.
- **Desde que empiece el recuento:** porcentaje escrutado, escaños y votos, que cambian cada pocos minutos.

La web tarda hasta un minuto en reflejar cada subida. **No debe aparecer el rótulo «SIMULACRO»**: si aparece, avisa a Nacho.

Al principio del recuento puede haber provincias sin datos y escaños «sin asignar» (en gris). Mientras no estén asignados
los 350, los gráficos no comparan con 2023 y el pactómetro no saca conclusiones. Es correcto, no es un fallo.

## Paso 8. Repaso de las 19:30

- La ventana de la captura sigue abierta y su última línea es reciente (de los últimos minutos).
- La web enseña los dos avances de participación.
- La galería de OBS y la página de redes cargan.
- Si tienes acceso al panel de Netlify, mira que queden créditos (cada subida gasta unos 15; el domingo se esperan unas
  125 subidas). Si no tienes acceso, pregúntale a Nacho.

## Paso 9. Durante el recuento (20:00 a medianoche)

Mira la ventana cada pocos minutos. Lo normal es una línea nueva cada tres minutos, con el porcentaje subiendo.

Para redes: en `redes.html` elige el contenido (resultado, mapa, pactómetro, provincia) y pulsa «Descargar PNG». La
imagen lleva los datos del momento en que la descargas. El tamaño por defecto (1080 × 1350) es el bueno.

## Paso 10. Al terminar

Cuando el porcentaje escrutado lleve un rato parado cerca del 100 % (pasada la medianoche, normalmente):

1. Haz clic en la ventana de la captura y pulsa **Ctrl+C** una vez. Debe decir `Captura detenida.`
   Si añade `OJO: no se pudo subir lo pendiente`, escribe `git push` y pulsa Intro.
2. En esa **misma ventana**:
   ```powershell
   python -m pipeline.captura_29n --mesas
   ```
   Baja los resultados mesa a mesa. Tarda varios minutos y no escribe nada hasta el final. Si dice que los ficheros aún
   no existen, no insistas: se repite el lunes.
3. No borres nada. Deja el PC encendido o apágalo normalmente; avisa a Nacho de que has terminado y de cualquier cosa rara
   que hayas visto (con la hora).

---

## Si algo va mal

| Lo que ves | Qué significa | Qué haces |
|---|---|---|
| La ventana se ha cerrado, o el PC se reinició | La captura se paró | Repite los pasos 1, 3, 4 y 6. Retoma sola desde el envío que haya en ese momento |
| `no se pudo publicar -> ...` | No ha podido subir a la web; sigue guardando los datos | Espera al siguiente envío. Si se repite tres veces, abre **otra** ventana en `repo`, escribe `git pull` y avisa a Nacho |
| `Interior rechaza la petición (401...)` | Usuario o contraseña | La captura espera sola 5, 10 y 15 minutos. No la reinicies una y otra vez. Avisa a Nacho |
| `Interior rechaza la petición (403...)` | Posible bloqueo de Interior | No reintentes. Apunta hora y mensaje y avisa a Nacho (hay que escribir a soporte de Interior con la IP pública, la hora y la dirección) |
| `el recuento retrocede` | Interior mandó un envío incompleto | Nada. No se publica y se espera al siguiente |
| Una línea con `error:` suelta y luego sigue | Fallo puntual de red | Nada, si la línea siguiente es normal |
| La ventana escribe líneas pero la web no cambia | Fallan las subidas en Netlify, o se acabaron los créditos | Avisa a Nacho: se mira en el panel de Netlify |
| Pasan más de 15 minutos sin línea nueva en pleno recuento (después de las 21:00) | Interior parado, o la captura colgada | Mira si otros medios siguen actualizando. Si ellos sí y tú no: Ctrl+C y repite el paso 6 |
| El PC muere del todo | — | Llama a Nacho. Arrancar en otro PC exige tenerlo preparado de antes |

Cosas que **no** hay que hacer nunca:
- Arrancar una segunda captura en otra ventana u otro PC «por si acaso».
- Lanzar la captura con `--simulacro`.
- Escribir el usuario o la contraseña de Interior en un fichero, un chat o un correo.
- Tocar, mover o borrar ficheros de las carpetas `repo` y `datos` mientras la captura corre.

## La víspera (viernes 27 o sábado 28, en el mismo PC)

Sirve para no descubrir un problema el domingo a las 13:30. Son los pasos 1 y 2 de esta guía y, además:

1. Comprobar que la página del 29N está vacía: en `https://elecciones2030.netlify.app`, «29 de noviembre de 2026» debe
   salir al 0 % y sin rótulo de simulacro. (Si no lo está, la captura la vacía sola al arrancar el domingo.)
2. Quitar la suspensión automática del PC.
3. Si se puede, hacer también los pasos 3, 4 y 5 para confirmar que la contraseña y la subida funcionan. Cierra la ventana
   al terminar.

## Dónde queda todo

- Los datos que manda Interior, tal cual: carpeta `datos\29n_envios\` (al lado de `repo`), una subcarpeta por envío.
- El resumen de la jornada: `datos\29n_envios\registro.csv`.
- El detalle técnico: `HANDOFF.md` (apartados 0 y 0b) y `CLAUDE.md`, en esta misma carpeta.
- El resultado de la noche no incluye el voto de los residentes en el extranjero, que se cuenta días después y puede
  mover algún escaño.
