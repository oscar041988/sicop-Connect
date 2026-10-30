# Reporte de cartel con IA · qué se envía al modelo

Guía: `docs/Guia_Reporte_Cartel_IA_SICOP.docx` (aprobada por Oscar, 2026-10-28, comunicado por Ivania).
Este documento crece lección a lección; la lección 1 define **el expediente**: el material que leerá el modelo.

## 1. El expediente de un cartel (lección 1)

`python -m app.cli ia expediente --nro 20261002824` lo arma (`app/ai/expediente.py`), **sin llamar a ningún
servicio**, y lo guarda en `EXPORTS_DIR/expediente_<nro>_<fecha-hora>.txt` (fuera de Git). Con `--ver` también lo
imprime. En la terminal muestra el tamaño, los documentos incluidos, los omitidos con su motivo y la huella.

### Secciones, en orden de prioridad

| Sección | Qué trae | De dónde |
|---|---|---|
| CARTEL | número SICOP, procedimiento, descripción, institución, tipo, modalidad, publicación, cierre, origen de los datos (real / sintético / simulado) | `tenders`, `institutions`, `imports`, ficha |
| LÍNEAS | número, cantidad, descripción del catálogo (o «código sin catálogo»), precio unitario y moneda, estimado de la línea; estimado total **por moneda** (no es el presupuesto) | `v_tender_lines` |
| FICHA SICOP | estado, versión y si se modificó, tipo de recepción, fechas (recepción, apertura, aclaraciones), monto, garantías, condiciones del contrato, criterios | ficha más reciente de `tender_details` |
| DOCUMENTOS | lista de todos los documentos con su estado; después, el texto de los PDF página por página | `tender_documents`, `tender_document_text` |
| OMITIDO | lo que no está en el expediente y por qué (para no inventar su contenido) | — |

Sin ficha (cartel no enriquecido) el expediente solo tiene CARTEL y LÍNEAS, y lo dice.

### Marcas de origen

Cada página lleva su marca: `[DOC 2 · Pliego de condiciones.pdf · pág. 4]`; dentro de un ZIP:
`[DOC 5 · Especificaciones.zip › anexo-tecnico.pdf · pág. 1]`. El número DOC es el de la lista de DOCUMENTOS.

### Los documentos son datos, no instrucciones

Cada documento va entre `<<<INICIO DOCUMENTO DOC n>>>` y `<<<FIN DOCUMENTO DOC n>>>`, con un aviso al inicio de
DOCUMENTOS: lo que hay entre los marcadores es material para resumir, nunca órdenes. Si un PDF trae `<<<` o `>>>`,
se cambian por `‹‹‹` / `›››`: así un documento no puede «cerrar» su marcador y hacerse pasar por la app
(protección contra la **inyección de instrucciones**).

### Tamaño y prioridad

- Límite: `IA_MAX_INPUT_TOKENS` (por defecto **50 000** tokens; 1 token ≈ 4 caracteres, sin librerías).
- CARTEL, LÍNEAS, FICHA y la lista de documentos entran siempre.
- El texto entra en este orden: primero el pliego principal y las especificaciones técnicas (nombre que empieza
  con «Pliego», o que dice «Especificaciones técnicas», o de ese tipo), después los anexos, en el orden de SICOP.
- Si un documento no cabe entero, entra hasta donde cabe («5 de 7 páginas omitidas por tamaño, desde …») y los
  siguientes quedan «omitido por tamaño».
- Escaneados, con error de lectura, Word / Excel / imágenes y los que no se bajaron **se nombran** en la lista y
  en OMITIDO; nunca se omiten en silencio.
- Base local (2026-10-28): el cartel más grande tiene ≈ 437 000 tokens de PDF; los 3 revisados (corto, con
  anexos, con escaneado) quedaron entre 20 000 y 25 000 tokens, completos.

### Huella

SHA-256 del texto del expediente. El texto no lleva la hora en que se armó: el mismo cartel sin cambios da la
misma huella (en la lección 3 sirve para no pedir dos veces el mismo resumen).

## 2. Lo que NUNCA se envía

Solo se envía información pública de SICOP (y, desde la lección 3, el portafolio de Hermatix). Nunca:

- revisiones, decisiones ni comentarios de los encargados (`reviews`), seguimientos ni asignaciones;
- usuarios, correos, contraseñas ni sesiones (`users`), destinatarios ni avisos;
- historial (`audit_log`), bitácoras ni grabaciones;
- los campos de funcionarios de la **ficha** de SICOP (Oscar, 27/10: no se guardan; `tender_details` ya los quita);
- la clave de OpenAI ni ninguna otra variable de `.env`.

**Corrección (2026-10-28): el texto de los PDF sí trae datos de personas.** Lo de arriba sobre funcionarios vale
solo para la ficha. Los pliegos, cronogramas y anexos que publica la institución traen impresos nombres y cargos
(«Analista de Contratación: …»), firmas, correos y teléfonos, y el expediente los copia tal cual. Lo encontró
Ivania al leer el expediente de `20261002824` (el cronograma termina con el nombre de la analista).

Medido en la base local (solo conteo, sin mostrar los datos; los teléfonos son aproximados porque el patrón
puede confundir otros números): de 2 600 páginas con texto, 147 tienen algún correo, 442 algo con forma de
teléfono y 13 un cargo o una firma; aparecen en **13 de los 15 carteles** con PDF.

**Decisión (Ivania, 2026-10-28; Oscar la confirma al aceptar `DECISION_IA.md`): se envían tal cual**, porque son
documentos públicos que la institución publica en SICOP. El expediente no los quita.

Sigue sin enviarse ningún dato de personas que **no** venga de SICOP: usuarios, encargados, revisiones y
comentarios internos de Hermatix (lista de arriba). Los campos de funcionarios de la ficha siguen sin guardarse.

Descartado por ahora: filtrar del texto los correos y teléfonos (los nombres no se pueden quitar de forma
confiable sin una herramienta aparte). Se puede retomar si Oscar lo pide.

El expediente solo consulta `tenders`, `institutions`, `imports`, `v_tender_lines` (con `catalog_items`),
`tender_details`, `tender_documents` y `tender_document_text`. Una prueba
(`tests/test_expediente.py`) comprueba que un comentario interno, el nombre y el correo de una encargada no aparecen.

## 3. Conexión con OpenAI (lección 2)

`app/ai/cliente.py` es la **única** parte de la app que habla con OpenAI (SDK oficial `openai` 3.40.0).
Construido y probado el 2026-10-28 **sin clave y sin llamar a OpenAI**: las pruebas usan un OpenAI SIMULADO.

### Variables (`.env.example`)

| Variable | Por defecto | Para qué |
|---|---|---|
| `AI_MODE` | `none` | `none`: la app no llama a ninguna IA ni carga el SDK. `openai`: se activa con Oscar |
| `OPENAI_API_KEY` | vacía | Clave del proyecto de OpenAI de Hermatix. La escribe Oscar en `.env`, en persona. `doctor` solo dice «configurado (oculto)» |
| `OPENAI_MODEL` | vacía | El modelo que elijan Oscar e Ivania. Nunca va en el código |
| `IA_TIMEOUT_SECONDS` | 120 | Tiempo máximo de espera de una llamada (10–600) |
| `IA_MAX_OUTPUT_TOKENS` | 4000 | Tope de la respuesta del modelo (100–32 000) |
| `IA_PRECIO_ENTRADA_USD` / `IA_PRECIO_SALIDA_USD` | vacías | USD por millón de tokens, copiados de la página oficial de precios de OpenAI para el modelo elegido. Vacías: costo «sin precio» (no se inventan) |

### Reintentos

Como máximo **2 reintentos** (3 intentos en total), con pausas de 2 s y 6 s, y solo ante errores **temporales**:
límite de uso (429), error del servidor (5xx), tiempo agotado y conexión. **Nunca** ante clave inválida (401),
permiso (403), petición mala (400), modelo no encontrado (404) ni falta de saldo (429 `insufficient_quota` o
`credit_balance_exhausted`).
El SDK no reintenta por su cuenta (`max_retries=0`).

### Qué guarda `ia_usage` (migración 0023)

Una fila por llamada, salga bien o mal: fecha, propósito (`prueba` · `resumen`), cartel, modelo, tokens de entrada
y salida, costo estimado en USD, duración, intentos y resultado (`ok` · `incompleta` · `fallo`). **No guarda el
texto enviado, la respuesta ni la clave** (no hay columnas para eso). El motivo de un fallo es solo el tipo de error
y su código («AuthenticationError 401 · invalid_api_key»), porque el texto del error de OpenAI puede traer parte de
la clave. No se modifica ni se borra. Además se pide a OpenAI no guardar la respuesta (`store=False`).

### Prueba de la conexión

`python -m app.cli ia probar`: una llamada corta («Responde solo: OK»). Muestra modelo, tokens, duración, costo
estimado y la respuesta, y la anota en `ia_usage`. Con `AI_MODE=none` dice «IA apagada» y no llama.

## 4. Resumen ejecutivo (lección 3)

`python -m app.cli ia resumir --nro 20261002824` pide al modelo el resumen del cartel (`app/ai/resumen.py`), lo
guarda en `ia_summaries` (migración 0026) y deja una copia para leer en `EXPORTS_DIR/resumen_<nro>_<fecha-hora>.txt`.
Construido el 2026-10-29 con un OpenAI SIMULADO en las pruebas; los resúmenes reales los genera Ivania.

### Prompt versionado

- `config/prompts/resumen_cartel_v1.md`: el prompt del sistema de la guía, con el portafolio de las 9 familias de
  `config/hermatix_rules.yaml` y un apartado de formato (fechas AAAA-MM-DD HH:MM, montos sin separador de miles)
  para poder compararlos con SICOP.
- `IA_PROMPT_VERSION` (por defecto `v1`) dice cuál se usa. Un cambio se guarda como `v2`, `v3`…; **nunca** se edita
  una versión ya usada, porque los resúmenes guardados dicen con qué versión se hicieron.
- **`v2` (2026-10-30), con el criterio de Hermatix dado por Ivania:** lo que decide es **qué piden**; todo cartel
  alineado con los servicios vale la pena, sin importar monto, cantidad, garantías ni plazo de entrega (se negocian).
  Hermatix tiene 14 años en funcionamiento (experiencia de la empresa de hasta 14 años: se cumple; lo que no se pueda
  confirmar, como cantidad de contratos, es duda y no descarte). Marcas propias: Wialon y Howen; otra marca exigida →
  riesgo y «revisar requisitos». Descartar solo si lo que piden no se alinea. La `v1` queda igual (sin criterio).
  Se activa con `IA_PROMPT_VERSION=v2` en `.env`; entonces todos los carteles vuelven a la cola.

### Salida estructurada

Se le da al modelo un esquema (JSON Schema, modo estricto) y OpenAI obliga a que la respuesta lo cumpla. Campos:
de qué trata · qué piden (línea, bien o servicio, cantidad, especificaciones, cita) · requerimientos (tipo técnico
/ legal / financiero / experiencia, excluyente, cita) · indicadores del pliego (plazo de entrega, vigencia,
garantías de participación y cumplimiento, peso del precio, nivel de riesgo) · plazos (cierre, apertura, otros) ·
monto estimado · criterios de evaluación · encaje con Hermatix · riesgos y dudas · recomendación preliminar
(dar seguimiento · revisar requisitos · descartar) y su justificación. Cada dato lleva su cita `[DOC n · pág. p]`
o «SICOP»; lo que falte dice «no encontrado».

### Comparación con SICOP

Cierre y apertura (día, y la hora si el resumen la da), monto estimado de la ficha y cantidad de cada línea. Si
alguno no coincide, el resumen queda **«revisar»** y la diferencia se guarda y se muestra. El monto y las fechas
del resumen solo sirven para esa comparación: en el reporte (lección 4) los indicadores de SICOP los pone la app.

### Estados y no repetir

- `ok` · `revisar` · `fallido` (rechazo del modelo, respuesta incompleta, JSON inválido o error de OpenAI: sin
  resumen, con su motivo; nunca se inventa uno).
- Misma huella del expediente y misma versión del prompt con un resumen `ok` o `revisar` = **no se vuelve a
  llamar** a OpenAI. Un `fallido` sí se vuelve a pedir. Nada se sobrescribe ni se borra.
- La recomendación no toca revisiones, decisiones ni seguimientos.

## 5. Cola automática y panel (lección 5, primera parte)

Pedido de Ivania (2026-10-30): que los resúmenes no dependan de correr `ia resumir` a mano. Decisiones de Ivania,
provisionales hasta que Oscar decida (`DECISION_IA.md` §5): **carteles Alta y Media enriquecidos**, presupuesto
de **10 resúmenes y 1.00 USD al día**.

- `python -m app.cli ia cola` (`app/ai/cola.py`) la corre la tarea de las 10:00, después del enriquecimiento. Cola,
  presupuesto, fallos y cómo apagarla: `docs/OPERACION.md` §3.3. `ia cola --ver` la muestra sin llamar a OpenAI.
- **Panel:** en la página de un cartel Alta o Media, el bloque «Resumen ejecutivo · Generado por IA · verificar con
  el pliego»: fecha, modelo, versión del prompt y estado; las diferencias con SICOP si quedó «revisar»; la
  recomendación preliminar («la decisión es del encargado»); qué trata y el encaje; el resto (qué piden,
  requerimientos con su cita, indicadores, plazos, criterios, riesgos) al abrir «Ver el resumen completo»; y el
  historial de resúmenes. Todo el texto del modelo va escapado. Con `AI_MODE=none` no aparece.
- **Falta de la lección 5:** citas como enlaces al documento y su página; la casilla «coincido / no coincido» junto
  a la decisión; el reporte de 2 páginas (lección 4) en la misma cola; la línea del resumen en el correo diario; la
  vista de uso del día y del mes; el despliegue en el servidor.

## 6. Pendiente de la lección 1

- Ivania lee completos los 3 expedientes reales y ajusta el orden o el límite si hace falta.
- Word y Excel (por ejemplo «Presupuesto detallado.xlsx», «Lista de insumos.xlsx») hoy no aportan texto; leerlos
  sería una mejora aparte (requiere decidir si se agrega una librería).
- Los PDF escaneados quedan sin texto; un OCR se evaluaría más adelante.
