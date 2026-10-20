# Bitácora de SICOP CONNECT

Una entrada por jornada (la escribe Ivania). Copia la plantilla y complétala.

<!-- Plantilla
## Día N — fecha

Horas realizadas:
Objetivo acordado en la reunión:
Trabajo y archivos cambiados:
Evidencia y comando de comprobación:
Datos: reales / sintéticos / simulados
Claude: interacciones usadas · % ventana A · % ventana B · % semanal
Estimado vs. real (horas humanas por tarea):
Concepto aprendido, con mis palabras:
Error encontrado y cómo se resolvió:
Bloqueo, responsable y próximo paso:
Commit:
Demo para mañana:
-->

## Día 1 — 2026-10-06

Horas realizadas: 6
Objetivo acordado en la reunión: completar los pasos del día 1 de la guía.
Trabajo y archivos cambiados:
- Base del proyecto: estructura de carpetas (15.3), configuración, `GET /health`, `python -m app.cli doctor`.
- Plantillas `docs/ACCESO_SICOP.md` y `docs/MAPEO_DATOS.md` (pasos 8–9).
- Primera visita al portal SICOP (Ivania, Google Chrome): 4 descargas de Ofertas, Solicitud de
  contratación y Detalle pliego de condiciones, en JSON y CSV.
Evidencia y comando de comprobación:
- `python -m pytest -v` → 2 passed · `python -m app.cli doctor` → 3 pendientes de correo/sesión · `/health` → HTTP 200.
Datos: sintéticos para la base; reales las descargas del portal (aún sin registrar ese día).
Claude: interacciones usadas no registrado · % ventana A no registrado · % ventana B no registrado · % semanal 1 %
Estimado vs. real (horas humanas por tarea): pasos del día 1 · estimado 2 h · real 6 h.
Concepto aprendido (redactado por Claude a pedido de Ivania):
- Entorno virtual: una carpeta (`.venv`) con un Python y unas librerías propias del proyecto, para que
  instalar algo aquí no rompa otros proyectos.
- Ruta web y código 200: `/health` es una dirección de la app; cuando responde, devuelve el código 200,
  que significa «todo bien» (404 sería «no existe»).
Error encontrado y cómo se resolvió: PowerShell no reconocía `claude` como un programa instalado. Había
dos causas: PowerShell no sabía en qué carpeta buscar el ejecutable y su política de seguridad bloqueaba
los scripts. Se resolvió así:
- Habilitar los scripts locales: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.
- Agregar Node.js y los módulos globales de npm al `Path` del usuario:
  `[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:AppData\npm;C:\Program Files\nodejs", "User")`.
Bloqueo, responsable y próximo paso: ninguno registrado; próximo paso: repetir la descarga con Oscar.
Commit: ninguno (repositorio sin commits).
Demo para mañana: no registrado.

## Día 2 — 2026-10-07

Horas realizadas: 6
Objetivo acordado en la reunión: terminar los pasos del día 1 y hacer los del día 2.
Trabajo y archivos cambiados:
- Segunda visita al portal (Oscar, Anabelle e Ivania): 5 descargas de Solicitud de contratación y
  Detalle pliego de condiciones. Comportamiento observado: código por correo en cada solicitud (≈ 1 min),
  enlace (≈ 1 min), el enlace dura entre 3 h y ≈ 16,5 h.
- Archivos reales revisados (sin abrir en Excel) y registrados con hash; movidos a `data/raw/` (fuera de Git);
  copia de carteles en `data/incoming/`.
- `docs/ACCESO_SICOP.md`: procedimiento, comportamiento por día, registro de 9 archivos.
- `docs/MAPEO_DATOS.md`: reportes 2, 2.1 y 1 con encabezados reales; contraste con diccionario y ERD oficiales.
- `docs/referencias/`: diccionario y ERD oficiales de SICOP.
- `docs/ESTADO_PROYECTO.md`: pendientes actualizados.
- Familias comerciales: Oscar aprobó en reunión el Diccionario de palabras clave v2 sin cambios
  (BodyCams como 9.ª familia, palabras «C» y casos adyacentes tal como están). Guardado como
  `docs/Diccionario_palabras_clave_v2_aprobado.pdf`.
Evidencia y comando de comprobación:
- `pytest` → 2 passed · `doctor` funciona · `/health` → HTTP 200 · `git status` → working tree clean.
- Hash SHA-256 de cada archivo en `ACCESO_SICOP.md`; `git check-ignore` confirma que `data/` no entra a Git.
Datos: reales (SICOP, datos abiertos).
Claude: interacciones usadas no registrado · % ventana A no registrado · % ventana B 37 % (según /usage) · % semanal 16 %
Estimado vs. real (horas humanas por tarea): pasos de los días 1 y 2 · estimado 7 h · real 6 h.
Concepto aprendido, con mis palabras: por qué se rechaza una fila. Como el archivo real no tuvo
rechazos, tomé el sintético: cuando un CSV se abre en Excel, los códigos largos se convierten a
notación científica y ciertos dígitos se pierden (p. ej. `3.00704E+09`); el importador rechaza la fila
por «código dañado por Excel», porque los dígitos perdidos no se pueden recuperar y es mejor rechazarla
con su motivo que guardar un dato falso.
Error encontrado y cómo se resolvió:
- Los CSV reales estaban en `docs/referencias/` y habrían entrado a Git → se movieron a `data/raw/`.
- Los primeros PDF de `docs/referencias/` no eran los oficiales de SICOP → se reemplazaron por los oficiales.
- `INST_CARTEL_NO` se había supuesto como `Número de solicitud` → el diccionario oficial dice que es el
  número de procedimiento; corregido en el mapeo.
Bloqueo, responsable y próximo paso:
- Reporte de Ofertas llega vacío sin filtros · Ivania · repetir otro día.
- Reportes 10.2 e 11 sin descargar · Ivania · cuando se necesiten.
- Dudas sin resolver: zona horaria de las fechas, códigos `LD`/`PX`/…, ausencia de `NRO_SEQ_SICOP`.
Commit: `b5a7902` Base del proyecto y acceso a SICOP documentado · `fc33c9a` Mapeo contrastado con diccionario y ERD oficiales de SICOP.
Demo para mañana: no registrado.

## Día 3 — 2026-10-08

Horas realizadas: 6
Objetivo acordado en la reunión: hacer los pasos de los días 3 y 4 de la guía.
Trabajo y archivos cambiados:
- Descarga del reporte 11 (instituciones compradoras, 691 filas) a `data/raw/`.
- Reporte 10.2 (catálogo): el portal solo acepta códigos de clasificación completos de 8 dígitos, no parciales.
  Las líneas usan 5 361 códigos distintos, así que se descargan solo los de las familias comerciales.
- Exploración (Claude): carteles reales con señal ALTA y sin exclusión → códigos de sus líneas:
  `83111602` (GPS/flotas, 4 carteles), `41112301` (IoT/frío, 2), `45121515` (BodyCams, 2).
  Las otras 6 familias no tuvieron carteles en el periodo.
- Descarga de esos 3 códigos del catálogo (3 ZIP en `data/raw/`).
- Importador de líneas, catálogo e instituciones y sus relaciones (migración `0002`, `app/importers/`,
  `app/dinero.py`, `app/compras.py`, comando `compra`). Hallazgo: el código de 16 dígitos del catálogo es
  clasificación (8) + identificación (8).
- Advertencia «inicio de recepción antes de la publicación» solo si pasa de 1 hora (108 → 1 caso; decisión de Ivania).
- Revisión en el portal: solo muestra carteles con la recepción abierta (confirmado con el del TEC). `ACCESO_SICOP.md`.
- Golden set: 31 carteles reales etiquetados por Oscar en `tests/golden/golden_set.csv` (5 provisionales).
- Inicio de los pasos del día 4 (lección 4): revisión de la guía (5 pasos, meta ≥ 80 % de acierto en el golden set)
  y acuerdo para el YAML: nombres de las 9 familias iguales al golden set, estructura con `senales_alta`,
  `senales_media`, `contexto` y `exclusiones`, y empezar por `gps_flotas`, `iot_frio`, `camaras_corporales` y
  `rastreo_activos`. Pendiente: que Ivania escriba `config/hermatix_rules.yaml` (todavía no existe).
- `docs/MAPEO_DATOS.md`, `docs/ESTADO_PROYECTO.md` y `docs/BITACORA.md` actualizados.
Evidencia y comando de comprobación:
- SHA-256 y filas de los 4 archivos nuevos en `ACCESO_SICOP.md`; cada ZIP del catálogo contiene el código pedido.
- `python -m pytest -q` → 45 passed (cada uno de los 3 commits probado por separado: 41, 42 y 45).
- Importación real: 691 instituciones, 100 códigos de catálogo, 73 991 líneas (0 rechazadas, 0 huérfanas);
  reimportar → «ya se importó». `python -m app.cli compra 20260701611` muestra cartel, comprador y 3 líneas.
Datos: reales (SICOP, datos abiertos).
Claude: interacciones usadas no registrado · % de la sesión de hoy 19 % · % semanal 13 % (según /usage)
Estimado vs. real (horas humanas por tarea): pasos de los días 3 y 4 · estimado 6 h · real 6 h (día 3 completo; día 4 iniciado, sin código todavía).
Concepto aprendido (redactado por Claude a pedido de Ivania): golden set. Es una «hoja de respuestas»: una lista
de carteles reales que Oscar etiquetó a mano (interesa, no interesa o falso positivo conocido, y su familia). Sirve
para medir con un porcentaje si las reglas aciertan. Incluye casos engañosos (p. ej. «equipo de topografía GNSS»)
porque sin ellos cualquier regla parecería buena. Los dudosos se guardan como provisionales y no cuentan al medir.
Error encontrado y cómo se resolvió: al revisar en el portal los 31 carteles del golden set, 30 no aparecían.
Parecía un error de datos. Hipótesis: la búsqueda del portal solo muestra carteles con la recepción abierta.
Prueba: 2 carteles abiertos sí aparecieron, y el del TEC apareció a las 10:54 y dejó de aparecer tras su cierre
de las 13:00. Quedó confirmado; los carteles cerrados solo se consultan en los datos abiertos.
Bloqueo, responsable y próximo paso: catálogo de 6 familias sin código · Ivania · buscarlos por nombre en el catálogo del portal.
Commit: `ab72df8` Bitácora días 1-3 y registro de reportes 11 y 10.2 · `ed681c7` Importador de líneas, catálogo e
instituciones y sus relaciones · `be84294` Advertencia de inicio de recepción solo si supera 1 hora; evidencia del
portal · `927ec38` Golden set: 31 carteles etiquetados por Oscar.
Demo para mañana: `python -m app.cli compra 20260800233`. El título solo dice «Insumos varios II» (CCSS), pero
sus 6 líneas muestran 2 termohigrómetros, uno «para control temperatura cadena de frío». Enseña por qué la app
une carteles con sus líneas y el catálogo: el título no siempre dice lo que se compra.

## Día 4 — 2026-10-09

Horas realizadas: 4 (en la mañana, primera ventana de uso; los días 4 y 5 se hicieron el mismo día, 2026-10-09: 7,5 h en total)
Objetivo acordado en la reunión: lección 4 de la guía, enseñarle al programa qué le interesa a Hermatix
(motor de reglas, YAML, prueba del golden set, `REGLAS.md`).
Trabajo y archivos cambiados:
- `config/hermatix_rules.yaml`: Ivania escribió a mano las 9 familias a partir del diccionario v2. Claude lo revisó
  y lo corrigió: formato YAML (sangría, comillas rectas), errores de tipeo, términos en minúsculas y sin tildes,
  variantes con «/» separadas y conflictos (p. ej. la exclusión «combustible» anulaba «control de combustible»).
- Motor de reglas (`app/matching/reglas.py`, `app/matching/evaluar.py`) y comando `python -m app.cli evaluate`:
  busca en el título y en el catálogo de las líneas, guarda familia, producto, encaje, regla, evidencia exacta,
  plazo y calidad de datos. Migración `0003`. Nueva dependencia: `pyyaml`.
- Prueba del golden set (`tests/test_golden_medicion.py`) que informa el % de acierto y los casos fallidos.
- Revisión de los candidatos reales y ajustes del YAML, cada uno con predicción previa (decisiones de Ivania):
  `mantenimiento_flotas` (contexto solo de software), `rastreo_activos` (contenedores y carga solo con rastreo;
  «impresora termica» como exclusión), `gps_flotas` (exclusión de talleres «mantenimiento preventivo y
  correctivo») e `iot_frio` (termohigrómetro y humedad relativa pasan a contexto).
- Segunda revisión de los primeros 20 candidatos (14 correctos, 1 error, 5 dudosos) y ajuste de `gps_flotas`
  (decisión de Ivania): exclusión «reparacion», «flotilla vehicular» pasa a contexto y señal alta «rastreo gps».
  Predicción simulada antes de aplicar: salen 2 talleres de Media y `20260802605` sube a Alta. Se cumplió.
- `docs/REGLAS.md`: cómo decide el motor, cómo cambiar y medir una regla, trampas conocidas, registro de
  decisiones y propuesta de Ivania (corregida) para sugerir términos a partir de las revisiones (lección 13).
Evidencia y comando de comprobación:
- `python -m pytest -q` → 79 passed.
- `python -m pytest tests/test_golden_medicion.py -s` → 25/26 = 96,2 % (meta O3: al menos 80 %). Único fallo:
  `20260902620` («Monitoreo y Localización Satelital mediante el Sistema GPS»), por las palabras intermedias.
- `python -m app.cli evaluate` sobre 10 339 carteles reales: la segunda corrida da «sin cambios» (idempotente).
  Revisión de los primeros 20 candidatos: 11 correctos, 6 errores, 3 dudosos. Tras los ajustes salieron los 6
  errores sin aparecer candidatos nuevos. Versiones de reglas guardadas para comparar: de `92299b2db230` a `2de4846a5a7e`.
  Resultado final: 14 Alta, 7 Media; solo 1 candidato no está vencido.
Datos: reales (SICOP, datos abiertos) en `data/sicop.db`; pruebas del motor con textos sintéticos.
Claude: interacciones usadas no registrado · % de la sesión de hoy 27 % · % semanal 17 % (según /usage)
Estimado vs. real (horas humanas por tarea): lección 4 · estimado 7,75 h (agenda de la guía) · real 4 h.
Concepto aprendido (redactado por Claude a pedido de Ivania): señal, contexto y exclusión. Una señal alta basta
sola («monitoreo gps» → Alta). Una señal media necesita compañía: «gps» con «flotilla» da Media; «gps» solo, Baja.
El contexto nunca crea una coincidencia, solo la refuerza. Una exclusión anula la familia aunque haya señales
(«topográfico» anula GPS). Y «Alta» habla del encaje con el portafolio, no de que Hermatix pueda ganar.
Error encontrado y cómo se resolvió: los termohigrómetros portátiles salían como Media aunque Oscar dijo que no
interesan. Predicción: al pasar «termohigrometro» a contexto bajarían a Baja. Al medir, siguieron en Media: la
ficha de catálogo de todo higrómetro dice «humedad relativa», que seguía siendo señal media y, sumada al
contexto, daba Media. Se movió también «humedad relativa» a contexto y salieron los 4. Lección: dos señales que
salen de la misma ficha no son dos pistas distintas.
Bloqueo, responsable y próximo paso: casos dudosos (data loggers de laboratorio, cámara de refrigeración, «cadena
de frío» en termómetros de mano) y términos «revisar» · Oscar · decidirlos. Casi todos los candidatos están
vencidos (datos de julio a octubre): hace falta descargar datos recientes.
Decisión de Oscar (confirmada a Ivania): los data loggers comprados como equipo de laboratorio (`20260903830`,
`20260901813`) interesan. Ya salían Alta; se agregaron al golden set (33 carteles). La medición bajó a 25/28 = 89,3 %
porque su señal está en las líneas y el golden set solo mide títulos: es un límite de la medición, no del motor.
Autoevaluación de la lección 4 (respuestas de Ivania, con ajustes de Claude):
1. ¿Por qué las reglas viven en un YAML y no en el código? YAML es un formato conocido para guardar configuración de
   forma estructurada y legible. La razón principal es separar las reglas del programa: Hermatix puede agregar o
   quitar una palabra sin programar ni tocar el motor, y cada cambio genera una versión de reglas que se puede medir
   antes y después. Ejemplo: agregar «reparacion» fue editar una línea del YAML; `app/matching/` no cambió.
2. Un falso positivo real y cómo se corrigió: «Servicio de reparación de 9 vehículos de la flotilla vehicular»
   (`20260803580`) salía Media en GPS porque «flotilla vehicular» (señal media) y «vehículos» (contexto) sumaban,
   aunque era un taller. Analicé las palabras del cartel y elegí cuáles debían anular: «reparacion» pasó a exclusión y
   «flotilla vehicular» a contexto. Predicción: salen 2 talleres de la lista; se cumplió. No siempre la solución es
   excluir: con los termohigrómetros se bajaron términos a contexto.
3. «Alta coincidencia» frente a «Hermatix puede participar»: Alta significa que el texto tiene señales fuertes de una
   familia del portafolio. Si aun así no es lo que Hermatix busca, es un falso positivo y se corrige en el YAML. Pero
   aunque la regla acierte, Hermatix puede no participar por el plazo, los requisitos o el presupuesto; eso lo decide
   una persona, y por eso plazo y requisitos son dimensiones aparte. Ejemplo: `20260900967` (monitoreo GPS para la
   flota municipal) es Alta y es justo lo que vende Hermatix, pero está Vencido.
Commit: `a30aaa4` Motor de reglas y comando evaluate; reglas de 9 familias y REGLAS.md · `214f5f4` Bitácora día 4 ·
`2a86ac3` Reglas gps_flotas: exclusión reparación, flotilla vehicular como contexto, rastreo gps.
Demo para mañana: `python -m app.cli evaluate --nro 20260800233`. El título solo dice «Insumos varios II», pero
el motor lo marca Alta en IoT/frío con la evidencia «CADENA DE FRÍO» (línea 2). Muestra cómo cada resultado
explica de dónde salió, y también por qué hay que revisarlo: es un termómetro de mano, un caso dudoso para Oscar.

## Día 5 — 2026-10-09

Horas realizadas: 3,5 (en la tarde, segunda ventana de uso; los días 4 y 5 se hicieron el mismo día, 2026-10-09: 7,5 h en total)
Objetivo acordado en la reunión: cerrar los pendientes de la lección 4 y hacer la lección 5 (Hito 1): un panel web
donde el encargado ve las oportunidades, abre el detalle con la evidencia y guarda su decisión, que se conserva
aunque se vuelvan a importar datos.
Trabajo y archivos cambiados:
- Cierre de la lección 4 (decisiones de Ivania y Oscar): la medición del golden set usa título y líneas
  (`tests/golden/golden_lineas.csv`); data loggers de laboratorio y `20260800233` (termómetro con pantalla) pasan
  a «interesa»; reglas nuevas: «compra de vacunas» (exclusión), «navegacion» (contexto), «didactico» y «de mano»
  (exclusiones; «de mano» excluye siempre, aunque tenga pantalla), «camara de refrigeracion» (contexto) y
  «localizacion satelital» (señal alta). Golden set: **29/29 = 100 %**. `docs/REGLAS.md` revisado.
- Dudas de datos cerradas en `docs/MAPEO_DATOS.md`: zona horaria de Costa Rica (confirmada), significado de los
  códigos de procedimiento (PDF de SICOP en `docs/referencias/`), `NRO_SEQ_SICOP` y `Codigos Productos.csv`.
  Corrección: `XE` = «Procedimientos Especiales», comprobado con la columna «Tipo de procedimiento» de los datos.
- Panel web (modo plan, aprobado por Ivania): `app/panel.py`, `app/web/rutas.py`, plantillas Jinja2 y CSS.
  Lista paginada con chips por estado de la revisión, buscador y filtros (prioridad, familia, institución, plazo,
  tipo de procedimiento); detalle con evidencia resaltada, líneas, comprador, cobertura de la fuente y formulario
  de revisión (Interesa / No interesa con motivo obligatorio / Revisar requisitos, comentario, responsable,
  historial). Migración `0004`: tipo de procedimiento en `tenders` y `reviews` con responsable y motivo; una
  revisión no se borra ni se modifica. Dependencias nuevas: `jinja2`, `python-multipart`.
- Diseño: primero una portada con contadores; después, a pedido de Ivania, el diseño del prototipo de Hermatix
  (`index-comentado.html`): tarjetas con monto, cierre y modalidad, «Ver toda la información», paleta verde,
  sin botones «Me interesa». Ajustes: márgenes y títulos dentro de la tarjeta, mismo color para todas las
  tarjetas, títulos en MAYÚSCULAS con mayúscula inicial (solo al mostrar).
- Descarga nueva de SICOP (ZIP del 2026-10-09, 13:49) registrada en `docs/ACCESO_SICOP.md` e importada.
Evidencia y comando de comprobación:
- `python -m pytest -q` → 144 passed.
- `python -m pytest tests/test_golden_medicion.py -s` → 29/29 = 100 %.
- Importaciones reales #7 (10 587 carteles: 460 nuevos, 119 actualizados) y #8 (74 824 líneas), 0 rechazos.
  `evaluate` → 18 Alta y 6 Media; **3 oportunidades abiertas**: Turrialba (`20261000870`, GPS, cierra 12/10 10:00),
  Cervantes (`20261000990`, telemetría IoT, 15/10) y CCDR Santa Cruz (`20261000674`, GPS, 16/10).
- Revisión real #1 de Ivania (`20260802051`, «Interesa») guardada en el panel; **sigue tras la importación #7**,
  que volvió a pasar por ese cartel. Criterio de la guía comprobado con datos reales.
- `python -m uvicorn app.main:app --reload` → http://127.0.0.1:8000; lista, filtros, buscador y detalle responden
  con los datos reales.
Datos: reales (SICOP, datos abiertos) en `data/sicop.db`; pruebas del panel con datos sintéticos en base temporal.
Claude: interacciones usadas no registrado · % de la sesión de hoy 52 % · % semanal 24 % (según /usage)
Estimado vs. real (horas humanas por tarea): lección 5 · estimado 7,5 h (agenda de la guía) · real 3,5 h (lección cerrada con la demo y el reto de comprensión).
Concepto aprendido (redactado por Claude a pedido de Ivania): Post/Redirect/Get. Al guardar una revisión, el
servidor no muestra la página directamente: responde «ve a esta dirección» y el navegador pide el detalle de nuevo.
Así, si se recarga con F5, se vuelve a pedir la página en vez de reenviar el formulario, y no se guarda una
revisión duplicada. Y la revisión va ligada al Número SICOP, que no cambia al reimportar: por eso no se pierde.
Error encontrado y cómo se resolvió: los títulos se salían de las tarjetas y aparecía una barra horizontal.
Parecía un problema de márgenes, pero la causa estaba en los datos: SICOP separa muchas palabras con espacios
duros (NBSP), que el navegador no puede cortar, así que un título entero se comportaba como una sola palabra.
Se resolvió cambiándolos por espacios normales solo al mostrar (el texto guardado no cambia) y dejando que las
cuadrículas del CSS se encojan. Una prueba lo fija. Otro aprendizaje: en Windows, la recarga automática del
servidor a veces no toma los cambios de varios archivos seguidos; reiniciarlo lo resuelve.
Bloqueo, responsable y próximo paso: ninguno. Ivania ensayó la demo del viaje del dato y superó el reto de
comprensión de la semana 1; Oscar vio el panel. Turrialba (cierra el lunes 12/10 10:00) no se trabaja: no da tiempo
de preparar una propuesta y los fines de semana no se trabaja. **Hito 1 cerrado.** Próximo paso: lección 6.
Autoevaluación de la lección 5 (respuestas de Ivania, con ajustes de Claude):
1. ¿Qué ocurre, paso a paso, cuando el encargado guarda una decisión? El navegador envía la decisión al servidor
   con un POST. El servidor la valida (que sea una de las tres decisiones, que «No interesa» traiga motivo y que
   haya responsable; si falta algo, responde con un error 400, no guarda nada y conserva lo escrito) y la guarda
   como una fila nueva en `reviews`. Después redirige al detalle, que se vuelve a dibujar desde la base
   (Post/Redirect/Get: recargar con F5 no reenvía el formulario ni duplica la revisión). Como las decisiones están
   separadas de los datos de SICOP y ligadas al Número SICOP, reimportar no las borra; además, la base impide
   borrar o modificar una revisión: cambiar de opinión es agregar una fila nueva al historial.
2. ¿Por qué el HTML debe escaparse? Para que el texto de afuera (de SICOP o de los usuarios) se muestre y nunca se
   ejecute. Así se protege al encargado de ataques XSS y la página no se rompe. Ejemplo: un título con
   `<script>alert(1)</script>` se muestra como texto. Jinja2 escapa todo por defecto, y el resaltado de la evidencia
   escapa primero el texto y después agrega las marcas `<mark>`; una prueba lo comprueba.
Commit: `7b5ae52` Medición del golden set con título y líneas · `4cd27d5` Dudas de datos resueltas · `bfad53e`,
`1450f0f`, `ece4991`, `811173d` Reglas y golden set · `503380e` PDF de SICOP · `16f3ae6` XE = Procedimientos
Especiales · `c328e86` Panel web · `8254781` Descarga del 2026-10-09 · `4c56097`, `094ccad`, `456db0a`, `38989ee`,
`bf75bc3` Diseño del panel.
Demo para mañana: abrir http://127.0.0.1:8000 y mostrar la tarjeta de Turrialba («Nuevo», «Cierra en 2 días»),
abrir su detalle con la evidencia resaltada («administración de combustible», «localización vehicular»), guardar
una revisión y contar que sigue ahí después de reimportar. Es el viaje completo del dato con una oportunidad real.

## Día 6 — 2026-10-12

Horas realizadas: 7 h
Objetivo acordado en la reunión: lección 6 de la guía, proteger el panel (usuarios, sesión y CSRF), confirmar
con Oscar los datos del servidor y del correo, y subir archivos de SICOP desde el panel.
Trabajo y archivos cambiados:
- Pendientes previos: golden set cerrado, los 4 provisionales se confirman sin pliego porque los concursos ya
  cerraron (decisión de Ivania); queda 33/33 = 100 %. El pendiente de la bitácora del día 4 ya estaba hecho y se quitó.
  En las pruebas, `httpx` se cambia por `httpx2`, lo que quita el aviso de deprecación de Starlette.
- Encargo A, panel protegido: `app/usuarios.py` (hash Argon2id con `argon2-cffi` sobre la tabla `users` de la
  migración 0001), `app/web/seguridad.py` (sesión obligatoria, token CSRF, `Cache-Control: no-store`), login y cierre
  de sesión en `app/web/rutas.py` y `login.html`, comando `python -m app.cli create-user` (contraseña con
  `getpass`), configuración `SESSION_SECRET` y `SESSION_MAX_AGE_HOURS`. `/docs` y `/openapi.json` desactivados.
- Paso 3 con Oscar: `docs/DESPLIEGUE.md` (borrador) con servidor Ubuntu 24.04 en Hostinger, IP, dirección
  https://sicop.hermatix.com, usuario `sicop` y las 3 rutas de la guía, correo con la API de Google desde
  licitaciones@hermatix.com y un GitHub que crea Oscar. 5 bloqueos registrados.
- Encargo B, carga de archivos: `app/web/carga.py` y `cargar.html`. Se elige reporte y origen; el archivo se
  guarda en `INCOMING_DIR` con nombre seguro y se importa con el mismo importador de la CLI. Límite
  `UPLOAD_MAX_MB` (25 MB), extensión `.csv` (`.zip` solo para el catálogo) y resumen de aceptadas y rechazadas.
  Mejora pedida por Ivania: si el archivo ya se importó, el aviso dice cuál fue la importación anterior.
- `requirements.lock.txt`: versiones exactas para el servidor, generadas desde un entorno limpio; el `.venv` se
  igualó a ese archivo (FastAPI 0.143.0).
- Lo que la lección 6 dejó fuera a propósito, hecho hoy (opción A en los 3 casos, decidida por Ivania):
  - La revisión queda a nombre del usuario de la sesión (`reviews.user_id`); el formulario ya no pide
    «Responsable». Las revisiones de antes del login se muestran «(escrito a mano)».
  - Límite de intentos de login (`app/web/intentos.py`): 5 fallos en 15 min por correo + IP bloquean 15 min (429).
  - Gestión de usuarios por terminal: `set-password`, `deactivate-user`, `activate-user` y `list-users`. Si un
    usuario se desactiva o cambia de contraseña, su sesión abierta se cierra en el siguiente clic.
- Propuesta de niveles de acceso para Oscar (2 niveles: Encargado y Administrador, con 6 preguntas); no se
  construye hasta que él lo defina.
Evidencia y comando de comprobación:
- `python -m pytest -q` → 233 passed (eran 144; al cierre de los encargos, 217; después, 16 más por la revisión
  ligada al usuario, el límite de intentos y los comandos de usuarios).
- Prueba manual como atacante (Ivania): ventana privada → login; URL directa de un detalle → login y vuelta al
  detalle; contraseña o correo incorrectos → el mismo mensaje; cerrar sesión y «atrás» → sin datos; `/health`
  responde sin sesión; `/docs` → login (comprobado con `curl`).
- Usuario real creado con `create-user`; `SESSION_SECRET` puesto en `.env` (`doctor`: «configurado (oculto)»).
- Carga de un CSV real de carteles desde el panel: lo reconoció como la importación #7 y no cambió nada (8 importaciones).
- Pruebas a mano de las 3 mejoras (Ivania): revisión nueva a su nombre y la #1 «(escrito a mano)»; bloqueo al quinto
  fallo aunque después acierte; `list-users` y `set-password` cerraron la sesión abierta y entró con la nueva.
Datos: reales (SICOP, datos abiertos) en `data/sicop.db`; las pruebas de acceso y carga usan datos sintéticos en una
base temporal.
Claude: interacciones usadas no registrado · % de la sesión de hoy 29 % · % semanal 29 % (según /usage)
Estimado vs. real (horas humanas por tarea): lección 6 · estimado 7,5 h (agenda de la guía: 2,75 + 1 + 1,75 + 2) ·
real 7 h (lección completa en el día, más las 3 mejoras que había dejado fuera).
Concepto aprendido (redactado por Claude a pedido de Ivania): hash. La base no guarda la contraseña, sino su hash:
una «huella» que se calcula a partir de ella y de la que no se puede volver atrás. Al iniciar sesión, el panel
calcula el hash de lo que escribí y lo compara con el guardado; si coinciden, la contraseña era correcta, sin
haberla guardado nunca. Ejemplo: si alguien copia `sicop.db`, ve algo como `$argon2id$v=19$m=65536…`, no mi
contraseña. Argon2 hace cada cálculo lento a propósito y le agrega una sal distinta a cada usuario, así que adivinar
probando contraseñas una por una tomaría demasiado tiempo.
Error encontrado y cómo se resolvió: al poner `SESSION_SECRET`, el panel no arrancó: «SESSION_MAX_AGE_HOURS debe ser
un número de horas». La línea de `SESSION_MAX_AGE_HOURS` en `.env` no tenía un número válido; se corrigió a
`SESSION_MAX_AGE_HOURS=8` y arrancó. Lección: la app revisa la configuración al encender y prefiere detenerse con
un mensaje claro antes que funcionar con un valor dudoso; el mensaje no muestra el valor por si fuera un secreto.
Otro caso: al abrir `/docs`, el navegador hizo una búsqueda en Google en vez de ir a la dirección; no era un fallo del
panel (con `curl` respondía 303 → login).
Bloqueo, responsable y próximo paso: bloqueos del despliegue (`docs/DESPLIEGUE.md`, sección 7) · Oscar · antes del
mié 14/10: usuario SSH, HTTPS (sin proxy con certificado no se puede iniciar sesión en el servidor), GitHub privado y
versión de Python. Acceso a la API de Google · Oscar · mar 13/10 (lección 7, paso 3). Pedido de Oscar para la lección 7:
destinatarios de los avisos editables desde el panel.
Autoevaluación de la lección 6 (respuestas de Ivania, con ajustes de Claude):
1. Si alguien copia el archivo de la base, ¿puede saber tu contraseña? No directamente, porque la base no guarda la
   contraseña, sino su hash, y del hash no se puede volver atrás. Lo único que puede hacer es adivinar, probando
   contraseñas una por una. Argon2 hace que cada intento sea lento y gaste memoria, y con 12 caracteres o más hay
   demasiadas combinaciones. Además, cada hash lleva su propia sal: 2 contraseñas iguales dan hashes distintos.
2. ¿Qué ataque evita el token CSRF? Que otra página que visito con mi sesión abierta envíe un formulario a mi panel,
   por ejemplo una revisión «No interesa», usando mi cookie, que el navegador adjunta solo. La cookie prueba quién
   soy y el token prueba que la petición salió de mi propio formulario. La página maliciosa no conoce el token, así
   que el servidor responde 403. `SameSite=Lax` ayuda como segunda barrera.
3. ¿Por qué /health puede ser público y el resto no? Porque lo que expone y para qué sirve son muy distintos.
   `/health` solo dice si la app y la base funcionan, sin nada sensible, y sirve para que un monitor revise el
   servidor sin iniciar sesión. El panel tiene decisiones comerciales y permite cambiar datos. Se deja público solo
   lo mínimo indispensable, y todo lo demás pide login. Por eso hay que vigilar que `/health` nunca empiece a mostrar
   datos de más, como rutas, versiones de librerías o variables de configuración.
Commit: `a459953` Golden set cerrado · `acdb76b` Pendiente de la bitácora del día 4 · `88169b7`, `41265b6` httpx2 ·
`78439ab`, `4f7432a` Encargo A (panel protegido) · `40df691` DESPLIEGUE.md · `2a91b22` Encargo B (carga de archivos) ·
`ed6e1e6` requirements.lock.txt · `751c185` Revisión ligada al usuario · `5a0a3ad` Límite de intentos de login ·
`08b66c3` Gestión de usuarios por terminal.
Demo para mañana: abrir el panel en una ventana privada (pide login), entrar, ir a «Cargar archivo» y subir un CSV
ya importado: muestra «ya se importó (#7: carteles, 09/10/2026)» sin cambiar nada. Muestra que el panel está protegido
y que la carga no duplica datos.

### Día 6 — continuación de la tarde (2026-10-12)

Horas realizadas (además de las 7 h de arriba): 3 h (10 h en el día)
Objetivo: aplicar la decisión de Oscar sobre los niveles de acceso y empezar la lección 7 (avisos por correo).
Trabajo y archivos cambiados:
- Niveles de acceso aprobados por Oscar: 2 niveles. Encargado: ve oportunidades, guarda revisiones y sube archivos.
  Administrador: además gestiona usuarios y destinatarios. Administradores: Oscar, Anabelle e Ivania.
  Regla «solo administrador» (`exigir_admin`): un encargado recibe 403 aunque escriba la dirección a mano. El nivel
  se lee de la base en cada clic.
- Página «Usuarios» (`/usuarios`): crear, cambiar nivel, activar o desactivar y poner contraseña nueva. Nadie puede
  quitarse a sí mismo el acceso y siempre queda un administrador activo. Terminal: `create-user --rol`, `set-role`.
- Historial de cambios (migración `0005`, tabla `audit_log`): quién cambió qué y cuándo, desde el panel o desde la
  terminal. No se borra ni se modifica y nunca guarda contraseñas.
- Lección 7, encargo A: página «Destinatarios» (solo administradores, con historial; ya no se usa `MAIL_TO`) y
  `python -m app.cli notify --dry-run`. Elige Alta y Media con plazo no vencido, vistas en los últimos 7 días
  (`NOTIFY_LOOKBACK_DAYS`); motivo nueva, cambio de plazo o cambio del cartel. Migración `0006`: outbox con estados
  preparado, aceptado, fallido e incierto, y clave destinatario + oportunidad + versión + motivo. Vista previa HTML y
  texto en `data/exports/`.
- Contraseñas: el mínimo bajó de 12 a 10 caracteres porque a la empresa le parecía tedioso; a cambio, el panel y la
  terminal sugieren una frase de 3 o 4 palabras. Las contraseñas existentes siguen sirviendo.
Evidencia y comando de comprobación:
- `python -m pytest -q` → 276 passed (eran 233 al cierre de la mañana).
- `python -m app.cli migrate` aplicó `0005` y `0006` en `data/sicop.db`.
- Pruebas a mano (Ivania): página Usuarios; usuario encargado de prueba sin acceso a Usuarios (después desactivado);
  usuarios de Oscar y Anabelle creados como administradores; destinatarios agregados; `notify --dry-run` dos veces
  (la segunda, «Avisos nuevos en la outbox: 0»); vista previa abierta en el navegador; contraseña de 9 caracteres
  rechazada con el consejo y una frase de 3 palabras aceptada.
Datos: reales en `data/sicop.db` (la vista previa usa oportunidades reales; no se envió ningún correo); las pruebas
usan datos sintéticos en una base temporal.
Claude: interacciones usadas no registrado · % de la segunda ventana de hoy 28 % · % semanal 33 % (según /usage)
Concepto aprendido (redactado por Claude a pedido de Ivania): outbox. Es una tabla donde se anota cada aviso antes
de enviarlo, con su estado: la memoria de qué se envió a quién. Funciona como el libro de correspondencia de una
oficina: antes de mandar una carta se anota a quién va y de qué trata, y si alguien pregunta «¿ya le mandamos esta a
Oscar?», se revisa el libro. Cada aviso tiene una clave única (destinatario + oportunidad + versión + motivo); si la
clave ya está, no se vuelve a preparar. Por eso el segundo `notify --dry-run` dijo «Avisos nuevos en la outbox: 0».
Y si SICOP cambia el cartel o su plazo, la versión es otra, así que sí se avisa, con el motivo «Cambió el plazo».
Error encontrado y cómo se resolvió: al entrar a «Usuarios» salió «Internal Server Error» con la página en blanco. La
base todavía no tenía la migración `0005`, así que faltaba la tabla del historial. Se resolvió con
`python -m app.cli migrate`. Mejora: el panel ahora compara la base con el código; si falta una migración, avisa
«Faltan migraciones… ejecuta migrate» en vez de un error 500. Lección: al traer código nuevo, migrar antes de
reiniciar el panel (también en el servidor).
Bloqueo, responsable y próximo paso: paso 2 de la lección 7 · Ivania con Oscar · mostrarle la vista previa (¿se
entiende en 30 s?, ¿falta o sobra algo?, ¿incluir los «No interesa»?, ¿a qué hora?). Encargo B (API de Google) ·
Oscar da el acceso y pone las credenciales en el `.env`. Bloqueos del despliegue · Oscar · antes del mié 14/10.
Commit: `50e7b7e` Niveles de acceso, usuarios e historial · `6983336` Lección 7, encargo A · `b80d33e` Contraseñas
de mínimo 10.

## 2026-10-19 — cierre de la lección 9 (por calendario, lección 11)

Horas realizadas: (completar, Ivania)
Objetivo acordado en la reunión: cerrar la lección 9 (app en el servidor) y destrabar la 10 (avisos de cada mañana).
Trabajo y archivos cambiados:
- Fin de línea LF en todo el repositorio (decisión de Oscar); los CSV se guardan byte por byte con el CRLF de SICOP.
  Primer push y primeros PR: #1 (LF) y #2 (página «Avisos»). Oscar los unió a `main`.
- `docs/ACTA_DESPLIEGUE.md` (nuevo): la instalación del 15/10 la hizo un asistente de IA de Oscar y el código fue
  del servidor a GitHub. Revisado: en GitHub no hay secretos. En la consola: app como `sicop`, permisos de la guía,
  `health` ok, puerto 8000 solo de SICOP, el proxy pasa la IP real, ciclo diario `disabled`.
- Base del servidor: tenía carteles cargados pero nunca evaluados. Oscar corrió `evaluate` (camino B) y el panel
  del servidor mostró las oportunidades.
- Datos al día en Windows (importaciones #12 y #13, 614 carteles nuevos) y prueba paso a paso de `OPERACION.md`,
  secciones 1–6: 13 hallazgos corregidos en el manual. Simulacros #3 (restaurar) y #4 (ciclo sin datos) en Windows.
- Archivos de Google instalados en el servidor por la herramienta de Oscar (sin registro de los comandos).
Evidencia y comando de comprobación:
- `python -m pytest -q` → 337 passed (rama LF) y 348 passed (con «Avisos»).
- `run-cycle --origen real --dry-run` → ciclo #22 «FALLO · no llegó ningún archivo nuevo», código 1, no avisó.
- `notify --dry-run` → 3 destinatarios, las mismas 3 oportunidades que se avisaron a mano.
- `backup` → `sicop_20261019-114809` (huella igual al manifiesto); restaurado en una carpeta aparte, revisiones #1–#5.
- En el servidor: revisiones de Corredores, Puriscal, OIJ, Santa Ana y CCSS desde otra computadora.
Datos: reales (SICOP, 19/10) en Windows y en el servidor; ningún correo enviado.
Claude: (completar, Ivania, según /usage)
Estimado vs. real (horas humanas por tarea): (completar, Ivania)
Autoevaluación de la lección 9: las tres correctas (Mac / servidor, por qué no `root`, código y datos aparte).
Concepto aprendido (redactado por Claude a pedido de Ivania): separar código, datos y configuración. El código va en
`/opt/sicop-connect` y se puede reemplazar en cada versión o volver a sacar de GitHub; los datos van en
`/var/lib/sicop-connect` y son únicos; los secretos van en `/etc/sicop-connect`, solo legibles por `sicop`. Como
cambiar el motor de un carro sin vaciar la maleta: se actualiza el código sin tocar las revisiones, y un respaldo
solo necesita la carpeta de datos.
Error encontrado y cómo se resolvió: en la consola del servidor, `python -m app.cli evaluate` dio «Command 'python'
not found». En el servidor no se usa `python` suelto: se corre con `systemd-run` como `sicop`, con el `.venv` y
`app.env` del panel (`OPERACION.md`, «Cómo se corre un comando»). Con `python3` desde `~` habría usado otra base.
También: marqué «Interesa» por error en la CCSS (`20261001749`) en vez de Puriscal (`20261002246`); se corrigió
con una revisión nueva. Lección: mirar el título, no solo el número.
Bloqueo, responsable y próximo paso: lección 10 (ciclo de las 8:00 y envío real) · Ivania con Oscar · confirmar que
los avisos del servidor siguen en dry-run, confirmar destinatarios, envío supervisado y activar el temporizador.
Commit: rama `acta-despliegue` (ver su PR).
Demo para mañana: el panel del servidor con las oportunidades de hoy y sus revisiones.

## 2026-10-20 — preparación de la lección 10 (Hito 2) y pendientes sin Oscar (por calendario, lección 12)

Horas realizadas: 6 h
Objetivo acordado: dejar lista la sesión del Hito 2 con Oscar y avanzar los pendientes que no dependen de él.
Trabajo y archivos cambiados:
- Servidor (Ivania con Oscar): los JSON de Google ya están en el servidor; `notify --send` desde el servidor
  entregó el correo. ☑ Hito 2: correo real recibido desde el servidor.
- `docs/ACTA_LECCION_10.md` (nuevo): hoja de la sesión y acta, pasos 0–4 (estado del servidor, ciclo en dry-run,
  envío supervisado, temporizador, reinicio). El paso 1 tiene dos caminos: A (ZIP) o B (CSV), según la versión.
- `docs/AMPLIACIONES.md` (nuevo): tabla A1–A6 con valor, esfuerzo y riesgo; orden recomendado A4 → A5 → A3.
  Oscar elige.
- Regla de «cámaras» (rama `regla-camaras-intraorales`): exclusión «intraoral» en `videotelematica` por el falso
  positivo de la CCSS (`20261001749`); se descartó «equipo medico» por el riesgo con ambulancias. Reglas
  `b880e0d350e1`; el cartel entra al golden set (34 carteles).
- Aviso en el panel de datos importados sin evaluar (rama `panel-aviso-sin-evaluar`): migración 0008
  (`evaluation_runs`); opción elegida por Ivania.
- ZIP de pliegos sin descomprimir, en el ciclo y en el panel (rama `zip-pliegos`; opción O4a de A1).
- `docs/DECISION_OBTENCION.md` (nuevo, borrador de A1): la descarga no se puede automatizar del todo, porque cada
  solicitud pide un código por correo. Recomendación provisional: mejorar el modo asistido.
- Práctica del reto de la semana 2, autoevaluación de A1 y autoevaluación de la lección 10 (en `ESTADO_PROYECTO.md`
  y `DECISION_OBTENCION.md`).
- GitHub: `leccion-10` rebasada sobre `acta-despliegue`; PR de las 6 ramas creados por Ivania en la web.
Evidencia y comando de comprobación:
- `python -m pytest -q` → 356 passed en `zip-pliegos`, 351 en `panel-aviso-sin-evaluar`, 348 en
  `regla-camaras-intraorales`; golden set 34/34 = 100 %.
- `evaluate` (base de Windows): la CCSS pasa de Media a «sin coincidencia»; el OIJ (`20260903798`) sigue Alta.
- `notify --dry-run` dos veces → 0 nuevos · 12 ya avisados las dos veces. Fila de `20261001587` en la outbox:
  3 destinatarios, motivo `nueva`, `aceptado` el 13/10.
- Respaldo `sicop_20261020-094004` y `migrate` → 0008 en la base de Windows: aviso antes de `evaluate`, sin aviso
  después.
- `run-cycle --dry-run` con el ZIP real del 9/10 sobre una copia de la base: los dos CSV «YA IMPORTADO» (#7 y #8).
Datos: reales en `data/sicop.db` (Windows) y en el servidor; las pruebas usan datos sintéticos; la prueba del ZIP
usó una copia de la base, que después se borró. Desde Windows no se envió ningún correo.
Claude: interacciones y uso no registrados
Estimado vs. real (horas humanas por tarea): lección 10 · estimado 7,25 h (agenda de la guía) · real 6 h hasta
ahora, en preparación y pendientes; **la lección sigue abierta**: falta la sesión con Oscar (pasos 1–4 de la
hoja, revisión semanal 2).
Autoevaluación de la lección 10: las tres correctas, con ajustes (el temporizador corre de lunes a viernes, no
todos los días; sin archivo nuevo igual evalúa; condiciones para avisar). Ver `ESTADO_PROYECTO.md`.
Concepto aprendido (redactado por Claude a pedido de Ivania, a partir de sus respuestas del reto): idempotencia.
Una operación es idempotente si hacerla dos veces deja todo igual que hacerla una vez. Lo comprobé con
`notify --dry-run`: la primera vez dejó 12 avisos en la outbox y la segunda dijo «0 nuevos · 12 ya avisados». Es
como un sello de «recibido»: si llega otra copia del mismo documento, ya se sabe que se registró. Gracias a eso,
si el temporizador lanzara el ciclo dos veces por error, nadie recibiría el correo repetido.
Error encontrado y cómo se resolvió:
- El resumen de pendientes salió de `main` y estaba desactualizado: lo más nuevo estaba en `acta-despliegue`, que
  todavía no se ha unido. Lección: antes de decir qué falta, mirar también las ramas sin unir.
- `leccion-10` y `acta-despliegue` cambiaban las mismas líneas de `ESTADO_PROYECTO.md`. Se resolvió con un rebase
  y `push --force-with-lease` (solo de `leccion-10`).
- PowerShell 5.1 rompe las comillas dobles dentro de `python -c` y de `git commit -m`. Se resolvió con un
  here-string (`@'…'@ | python -`) y con `git commit -F archivo`. Uno de los commits falló por esto y la rama se
  subió sin él; se repitió.
- Al preparar la hoja se vio que el ciclo no aceptaba el ZIP de pliegos; de ahí salió O4a.
Bloqueo, responsable y próximo paso: Oscar revisa y une las 6 ramas (primero `acta-despliegue`, luego
`leccion-10`) y actualiza el servidor (9.8: respaldo, `migrate` → 0008, `evaluate`) · luego, la sesión del Hito 2
con `docs/ACTA_LECCION_10.md`, el reto oficial de la semana 2 y la elección de las ampliaciones · decidir quién
deja el archivo de SICOP antes de las 8:00. Ivania: copiar el respaldo a la USB y buscar los códigos de catálogo
de las 6 familias.
Commit: `leccion-10` (`d75fc22` → `4b91f5a`) · `regla-camaras-intraorales` (`a707895`) · `panel-aviso-sin-evaluar`
(`b734ccc`) · `zip-pliegos` (`41cf4db`), cada una con su PR.
Demo para mañana: en la rama `zip-pliegos`, abrir http://127.0.0.1:8000, ir a «Cargar archivo» y subir el ZIP de
pliegos tal como lo baja SICOP. El panel muestra sus dos partes («ZIP › Detalle de pliegos de condiciones.csv» y
«ZIP › Detalles lineas.csv»), cada una con «ya se importó (#7 / #8)». Muestra que ya no hay que descomprimir el ZIP a
mano, y también la idempotencia: el mismo archivo no se importa dos veces.
