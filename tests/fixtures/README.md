# Fixtures de pruebas

Archivos pequeños y fijos que usan las pruebas como entrada.

## `carteles_muestra.csv`

- **Datos: REALES.** Extracto de datos abiertos públicos de SICOP; no contiene datos de personas.
- Origen: encabezado y 5 filas copiados byte a byte (sin abrir en Excel) de
  `Detalle de pliegos de condiciones.csv`, obtenido el 2026-10-07 (solicitud de las 08:55, sin filtros).
  SHA-256 del original: `5d850ce0d9dfc31c3f4765a146b8f3c7ea9a453d9986a4ddd346c5521b52afcc`
  (ver `docs/ACCESO_SICOP.md`). El original está en `data/raw/`, fuera de Git.
- Formato: UTF-8 con BOM, separador `;`, fin de línea CRLF, 15 columnas.
- Filas elegidas para cubrir casos del importador:

| Número SICOP | Caso que cubre |
|---|---|
| 20260700179 | Descripción con espacio duro (NBSP) y tildes |
| 20260700347 | `Excepción CD` con valor |
| 20260700580 | Sin fechas de recepción (vacías) |
| 20260700755 | `Pago Adelantado Pymes` = `Y` |
| 20260700384 | Caso común: sin excepción, con fechas, sin NBSP |

Todas tienen `Cod Unidad Compra` con ceros iniciales (`00001`, `01142`, `02102`): deben conservarse como texto.

## `carteles_sintetico.csv`

- **Datos: SINTÉTICOS.** Inventados para probar el importador; no corresponden a carteles reales
  (descripciones «SINTETICO …», cédula `9999999999`, números `2026990000x`).
- Mismo encabezado y formato que el reporte real (UTF-8 con BOM, `;`, CRLF).

| Línea | Caso | Resultado esperado |
|---|---|---|
| 2 | Válida, descripción con NBSP | aceptada |
| 3 | `Número SICOP` `00099900002` y `Cod Unidad Compra` de 24 dígitos con ceros iniciales | aceptada, ambos idénticos |
| 4 | `Cédula` en notación científica (`3.00704E+09`) | rechazada: código dañado por Excel |
| 5 | `Fecha Publicación` con formato distinto | rechazada: formato inválido |
| 6 | `Número SICOP` vacío | rechazada |
| 7 | Solo 3 columnas | rechazada: columnas de menos |
| 8 | `Número SICOP` repetido de la línea 2 | rechazada: repetido |
| 9 | Sin fechas de recepción | aceptada con advertencia |

## `lineas_muestra.csv`

- **Datos: REALES.** Encabezado y las 5 líneas (una por cartel) de los carteles de `carteles_muestra.csv`,
  copiados byte a byte de `Detalles lineas.csv` (2026-10-07, SHA-256 `99a5b8f8…a731`, ver `docs/ACCESO_SICOP.md`).
- Incluye una línea en USD (`20260700384`: 1425 × 12 = 17100 USD).

## `lineas_sintetico.csv`

- **Datos: SINTÉTICOS.** Usa los carteles válidos de `carteles_sintetico.csv` y códigos inventados
  (`99999901…`, `88888801…`, `00000001…`).

| Línea | Caso | Resultado esperado |
|---|---|---|
| 2 | Cartel `20269900001`, línea 1, CRC, código en el catálogo sintético | aceptada; 2 × 1500.50 = 3001.00 CRC |
| 3 | Mismo cartel, línea 2, USD, clasificación descargada pero código ausente | aceptada, marcada «no está en catálogo» |
| 4 | Mismo cartel, línea 3, CRC, clasificación no descargada | aceptada, marcada «sin catálogo» |
| 5 | Cartel `00099900002` (ceros iniciales), cantidad 0 | aceptada con advertencia |
| 6 | Cartel `20269900077`, que no existe | huérfana: solo en `raw_snapshots` |
| 7 | Código en notación científica | rechazada |
| 8 | Código de 15 dígitos | rechazada |
| 9 | Línea repetida de la línea 2 | rechazada |
| 10 | Moneda vacía | rechazada |
| 11 | Cantidad con coma decimal (`1,5`) | rechazada |

## `catalogo_identificacion_sintetico.csv`

- **Datos: SINTÉTICOS.** Mismo encabezado que `Codigos Identificacion.csv` del reporte 10.2 real.
  Las pruebas lo meten en un ZIP con la forma del portal.
- Filas 2–3 válidas (clasificación `99999901`); fila 4 con clasificación de 7 dígitos → rechazada.

## `instituciones_sintetico.csv`

- **Datos: SINTÉTICOS.** Mismo encabezado que el reporte 11 real. `Representante` = «PERSONA SINTETICA»
  para comprobar que ese dato no se guarda.
- Fila 2: cédula `9999999999` (la de los carteles sintéticos); fila 3: cédula con ceros iniciales;
  fila 4: cédula en notación científica → rechazada.

## `correo_codigo_simulado.eml` y `correo_envio_simulado.eml`

- **Datos: SIMULADOS.** Copias anonimizadas de dos correos reales de `info@sicop.go.cr` recibidos el
  2026-10-21 (13:34 y 13:36, hora de Costa Rica), descargados de Gmail como `.eml`. Los originales están en
  `data/correos_sicop/`, fuera de Git.
- Se conservó la forma real: remitente, asunto codificado (`=?UTF-8?Q?…?=`), fecha, `text/html; charset=utf-8`
  y la codificación del cuerpo (el del código en `quoted-printable`, con líneas cortadas por `=`; el del
  enlace en `7bit`).
- Se reemplazó: el código (6 letras y números, ahora `Zq9Xw4`), el `processId` del enlace (ahora `99999`),
  el destinatario (`buzon@example.com`) y el `Message-id`. Se quitaron las cabeceras de entrega y firmas
  (`Received`, `DKIM`, `ARC`, `List-Unsubscribe`, `Reporting-Meta`). La primera cabecera,
  `X-Datos-Sicop-Connect`, marca el archivo como SIMULADO.

## `sicop_simulado.html`

- **Datos: SIMULADOS.** Página que imita las ventanas de Datos abiertos de SICOP observadas el 2026-10-21
  (`docs/ACCESO_SICOP.md`): encabezado «Detalle pliego de condiciones» (`role=button`), `<img alt="CSV">`, y las
  ventanas `role=dialog` del correo, del código y de «Procesando el reporte», con sus textos exactos.
- `tests/test_sicop_browser.py` reemplaza `__VARIANTE__`, `__CODIGO__` y `__PID__`. Las variantes son `normal`,
  `codigo_rechazado`, `boton_cambiado`, `captcha`, `sin_url`, `animacion` (por un momento hay dos iconos CSV
  visibles, como en el portal real el 2026-10-21), `dos_csv` y `codigo_se_cierra` (la ventana del código
  desaparece sola, como el 2026-10-21 a las 15:18).

## `sicop_concursos_simulado.html` y `ficha_simulada/`

- **Datos: SIMULADOS** (las respuestas del servidor son de mentira). Sirven para `tests/test_ficha.py`
  (enriquecimiento, lección 2).
- `sicop_concursos_simulado.html` imita la consulta pública de concursos observada el 2026-10-27
  (`docs/DETALLE_CARTEL.md`): «Búsqueda avanzada» con `role=button`, la etiqueta «Número de SICOP» sin unir a su
  casilla, «Consultar», la fila del resultado con el enlace `[tipo] descripción` y los `fetch` de la ficha a las
  mismas rutas de `prod-api.sicop.go.cr`. Variantes: `normal`, `captcha`, `bloqueo`, `captcha_en_ficha`,
  `sin_avanzada`.
- `ficha_simulada/<Número SICOP>/` (`busqueda`, `ficha`, `lineas`, `documentos`, `criterios`, `impactos`.json):
  copiadas de las respuestas que SICOP le dio a la exploración de la lección 1 para los carteles públicos
  `20261002859` (GPS, abierto), `20261001258` (abarrotes, objetado, 432 líneas y 49 documentos) y `20261001587`
  (Santa Ana, modificado el 26/10), **sin los campos de personas** (funcionarios, identificaciones, correos,
  teléfonos y quien presentó un recurso; el mismo patrón `PERSONALES` de `app/sources/sicop_tender_detail.py`).
  Los números se dejaron tal como venían en el texto. Las líneas son solo la primera página (100), como la
  recibe la página.
- Lección 3: la ficha simulada muestra la tabla de documentos (10 por página, botones «Página anterior» y
  «Página siguiente») y, al hacer clic en un archivo, pide `downloadWithPAR` y luego el archivo al «almacén»
  (`objectstorage…/p/CLAVE-SIMULADA-NO-ANOTAR/…`; la prueba revisa que esa clave no quede en ningún lado).
  Variantes nuevas: `captcha_en_descarga` y `orden_distinto`.

## `documentos_simulados/`

- **Datos: SIMULADOS.** Documentos de prueba de `tests/test_documentos.py`, hechos con
  `hacer_documentos.py` (está en la misma carpeta; volver a correrlo da los mismos archivos):
  `con_texto.pdf` (2 páginas con texto «SIMULADO…», con tildes), `escaneado.pdf` (solo una imagen: sin texto),
  `falso.pdf` (HTML con extensión .pdf), `pliego.zip` (un PDF con texto adentro y un .txt) y `formulario.xlsx`
  (un ZIP mínimo). Las pruebas generan además un archivo distinto por documento con las mismas funciones.

**No editar estos archivos** (ni abrirlo y guardarlo con Excel). Si hace falta otro caso, agregar un fixture nuevo
y anotarlo aquí con su origen (real / sintético / simulado).
