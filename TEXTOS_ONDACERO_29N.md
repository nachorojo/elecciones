# Textos para las páginas públicas del 29N (ondacero.es)

Escritos el 28 de noviembre de 2026. Dos páginas con un módulo incrustado cada una. El código del `<iframe>` de cada módulo
está en `https://elecciones2030.netlify.app/embeds.html` (botón «Copiar código»). Los textos son propuestas: Redacción manda.

---

## Página 1. Proyección

**Módulo:** `https://elecciones2030.netlify.app/embed/proyeccion.html`

**Título (opciones)**
- PROYECCIÓN | Hacia dónde apunta el recuento: el reparto de escaños que dibujan los votos ya contados
- PROYECCIÓN | Quién ganará las elecciones según el recuento actual *(más directo; el módulo dice «primera fuerza», no «ganador»)*

**Entradilla (encima del módulo)**

> A medida que avanza el escrutinio, Onda Cero calcula cómo quedaría el Congreso si el voto que falta por contar se comporta como
> el que ya se ha contado en cada municipio. El gráfico compara los escaños que cada candidatura tiene con el recuento actual
> (la marca vertical) con los que tendría al final (la barra). Se actualiza con cada envío de datos del Ministerio del Interior.

**Explicación (debajo del módulo)**

> **Cómo se calcula.** El recuento oficial no avanza igual en toda España: llegan antes unas mesas que otras, y los primeros datos
> rara vez se parecen al resultado final. Esta proyección corrige ese efecto municipio a municipio. En cada localidad compara los
> votos ya contados con lo que ese mismo municipio votó en las generales de julio de 2023, mide cuánto ha subido o bajado cada
> candidatura y aplica ese cambio a los votos que aún faltan por contar allí. Donde todavía hay pocos datos, se apoya en lo que
> está ocurriendo en los municipios de tamaño parecido de su provincia y, si hace falta, en el conjunto de la provincia. Con esos
> votos estimados se reparten los escaños de cada circunscripción con la misma fórmula que usa la ley electoral.
>
> **Qué tiene en cuenta y qué no.** Al trabajar pueblo a pueblo y ciudad a ciudad, la proyección sabe de dónde llegan los votos:
> no confunde un recuento avanzado en el medio rural con uno avanzado en las grandes capitales, ni una provincia con otra. Lo que
> no puede saber es qué mesas de un mismo municipio se han contado primero, porque ese dato no se publica durante la noche, y
> el orden de llegada de los votos dentro de cada localidad influye en el resultado. Tampoco hay referencia de 2023 para las
> candidaturas que se presentan por primera vez o que antes concurrían juntas: en esos casos se proyecta el porcentaje que
> llevan en lo ya contado, con menos precisión.
>
> **Cuánto puede fallar.** El margen de error que acompaña al gráfico procede de un ensayo: se han reconstruido las noches
> electorales de abril de 2019, noviembre de 2019 y julio de 2023 haciendo llegar los votos en distintos órdenes, y se ha medido
> a cuántos escaños del resultado final se quedaba la proyección en cada momento. Con la mitad del voto contado, la desviación
> media fue de entre uno y dos escaños sobre 350, y de cuatro en el caso más desfavorable. Con menos recuento, o si los votos
> llegan en un orden poco habitual, puede ser mayor. La proyección no incluye el voto de los residentes en el extranjero, que
> se cuenta días después, y no es un dato oficial: el único resultado oficial es el que publica el Ministerio del Interior.

**Crédito sugerido (al pie):** Datos: Ministerio del Interior. Proyección: Onda Cero, a partir de la base histórica de resultados
electorales elaborada por Miguel Ibáñez González (Universidad Autónoma de Madrid).
*(Nacho: la proyección de la noche es un cálculo propio que usa su tabla municipal como referencia de 2023; decide tú la fórmula del crédito.)*

### Cuándo publicar la página

- **Recomendación: a partir del 50 % escrutado y con las 52 provincias ya con datos.** El propio módulo avisa mientras falten
  provincias («Muy provisional») y rotula el nivel: muy provisional (< 30 %), provisional (30–50 %), orientativa (50–80 %) y
  muy próxima al recuento (> 80 %).
- **Si se quiere arriesgar antes:** el mínimo razonable es el 30 %. Por debajo, en la prueba del 25-N la proyección infraestimó
  mucho a las candidaturas sin referencia de 2023 (dio 9 escaños al Frente Amplio con el 10 % contado; acabó en 27).
- Antes de que haya recuento, el módulo muestra solo un mensaje de espera: se puede dejar la página preparada sin publicar.

### Respuestas a las dudas de Nacho

- **«El margen sale de reconstruir las noches de abril de 2019, noviembre de 2019 y 2023…»: ¿qué margen?** El margen de error
  de la proyección: cuántos escaños de los 350 acabaron en un partido distinto del que decía la proyección. No hay registro de
  en qué orden llegaron las mesas en noches anteriores, así que se simularon varios órdenes posibles (al azar, primero los
  municipios pequeños, primero las mesas pequeñas) con los resultados reales por sección de esas tres elecciones. Eso da el
  margen «normal». También se probaron dos órdenes adversos (primero las secciones más de derechas, o más de izquierdas): ahí
  el error es bastante mayor (unos 6 escaños de media con el 50 %, hasta 10).
- **«Compara lo ya contado en cada municipio con su resultado de 2023 y aplica ese cambio a lo que falta».** Ejemplo: si en un
  municipio el PP sacó 1.000 votos en 2023 y con la mitad del censo contado lleva 600, va a un ritmo de 1.200: un 20 % más.
  Ese +20 % se aplica a la mitad que falta. En la práctica el cambio de cada municipio se mezcla con el de su entorno
  (municipios de su tamaño en la provincia, y la provincia), con más peso para el propio municipio cuanto más voto lleva contado.
- **¿Qué elecciones anteriores se usan?** Para proyectar, **solo la última, julio de 2023**. Las de 2019 y 2023 se usaron para
  ensayar y medir el error, no entran en el cálculo de mañana.
- **¿Por qué no todas las que tenemos (desde 1996)?** Porque lo que mejor anticipa el voto de un municipio es su voto más
  reciente; al revisar el modelo del TFM se vio que los resultados más antiguos apenas añadían información sobre el último. Y
  porque el mapa de partidos cambia: cuanto más atrás, menos comparable. Dicho esto, no se ha probado una versión con varias
  elecciones de referencia: es una decisión razonada, no un resultado medido.
- **¿Solo mira el orden de llegada de elecciones pasadas? ¿No tiene más parámetros?** No usa ningún patrón de llegada del
  pasado: no existe ese dato. Usa lo que llega mañana. Sus «parámetros» son la provincia, el tamaño del municipio (cuatro
  tramos: hasta 1.000, 10.000 y 100.000 electores, y más) y el propio municipio, más un ajuste de cuánto fiarse de cada nivel.
- **¿Se puede ponderar rural/urbano y por provincia?** Ya lo hace, y es lo esencial del método: cada municipio se compara
  consigo mismo, así que da igual que primero lleguen pueblos o capitales. El punto ciego está dentro de cada municipio (qué
  barrios o mesas llegan antes); solo se podría afinar en las siete ciudades de las que Interior da el dato por distrito. No
  está hecho.

---

## Página 2. Escaños en el aire

**Módulo:** `https://elecciones2030.netlify.app/embed/disputados.html` (por defecto, 12 filas; `?n=10` para diez)

**Título:** Los escaños en el aire: ¿dónde se está jugando el resultado final?

**Entradilla (encima del módulo)**

> El reparto del Congreso se decide a menudo por un puñado de votos en unas pocas provincias. Esta lista recoge, con el recuento
> en marcha, las circunscripciones donde el último escaño está más ajustado: qué candidatura lo tiene ahora, cuál se lo disputa
> y cuántos votos le faltan para arrebatárselo.

**Explicación (debajo del módulo)**

> **Cómo se calcula.** En cada provincia los escaños se asignan con la fórmula D'Hondt: los votos de cada candidatura se dividen
> entre uno, dos, tres… y los escaños van a los cocientes más altos. El último escaño es el que entra con el cociente más bajo,
> y la candidatura que se queda a las puertas es la que tiene el siguiente. El Ministerio del Interior publica con cada
> actualización, para cada provincia, quién ocupa ese último escaño, quién va detrás y cuántos votos más necesitaría para
> quedárselo. Aquí se ordenan las provincias de menos a más votos de diferencia.
>
> **Cómo leerlo.** La cifra corresponde a lo contado en ese momento, no al final del recuento: una provincia con el 60 %
> escrutado puede cambiar de manos varias veces. Por eso solo entran en la lista las que han superado la mitad del escrutinio,
> y cada una indica su porcentaje. Cuando el recuento termina, la lista muestra los escaños que se han decidido por menos votos.
> No incluye el voto de los residentes en el extranjero, que se suma días después y que en provincias muy ajustadas puede
> cambiar el último escaño.

**Cuándo publicarla:** desde que haya varias provincias por encima del 50 % (antes, el módulo dice que la lista aparecerá en
cuanto las haya). Es dato de Interior tal cual: no tiene el riesgo de la proyección.

---

## Página 3. Temas para artículos

Los datos salen de `https://elecciones2030.netlify.app/curiosidades.html` (con `?datos=ejemplo` se ve el formato). Se generan
al acabar el recuento en el PC que captura, con la captura ya parada:

    python -m pipeline.curiosidades_29n --publicar

Cada tabla lleva su regla y se puede copiar o descargar en CSV. Temas que salen (unos 45 con datos completos):

1. El municipio donde más se ha votado a Vox / al PP / al PSOE / al Frente Amplio / a Se Acabó la Fiesta / a Podemos.
2. Cuántos municipios gana cada partido, y los municipios donde gana Vox, el Frente Amplio o SALF.
3. El municipio con mayor abstención y el que más vota; lo mismo entre ciudades de más de 50.000 electores.
4. Dónde se hunde y dónde sube la participación frente a 2023.
5. Así han votado los 10 municipios con menos electores; los pueblos donde ha votado todo el censo.
6. Los pueblos del voto casi unánime (más del 80 % a una candidatura).
7. Empate exacto; ganar por un solo voto; las ciudades más reñidas.
8. El mapa cambia de color: cuántos municipios cambian de ganador y las mayores ciudades que lo hacen.
9. Cae el feudo: municipios donde siempre ganó la misma fuerza desde 1996 y ahora gana otra.
10. Dónde más se hunde y dónde más crece el PP, el PSOE, Vox y el espacio de Sumar (suma de sus herederos).
11. Donde un partido baja y otro sube a la vez (PP/Vox, PP/PSOE, PSOE/espacio de Sumar, en los dos sentidos).
12. Dónde hay más voto en blanco y más voto nulo.
13. El pueblo que vota como España.
14. El escaño más barato y el más caro (votos por escaño); los votos que se quedan sin escaño.
15. Ganar con poco: los municipios más repartidos; donde gana una candidatura sin presencia nacional.
16. Donde Podemos supera al Frente Amplio.
17. La España de los pueblos y la de las ciudades: resultado por tamaño de municipio.
18. Quién gana en la mayor ciudad de cada provincia.
19. Distritos de las siete grandes ciudades: el más fiel a cada partido, el que más vota y el que menos.
20. Usansolo vota por primera vez como municipio.

**Sobre los «trasvases».** El ejemplo de Nacho (PP 1.000 → 800 y Vox 200 → 400, PSOE igual) es justo lo que recoge el tema 11,
con los votos de 2023 y 2026 de los dos partidos a la vista. Se puede titular «donde el PP pierde lo que gana Vox», pero no
afirmar que esos 200 votantes sean los mismos: entre una elección y otra cambian el censo y la participación, y hay más
partidos en juego. En municipios pequeños y con el resto estable la lectura es razonable; cuanto mayor el municipio, menos.
