# Ampliaciones de la semana 3 — propuesta para Oscar

Lección 10, paso 4 (guía 19.2). **Borrador (2026-10-20)**: preparado por Ivania con Claude; Oscar elige y prioriza.
Regla de la semana: cada ampliación tiene **un día como límite**. Si no cumple su criterio, se documenta y se pasa
a la siguiente. Hito 3 (viernes 23/10): al menos **tres** ampliaciones aceptadas y funcionando en el servidor.

Calendario: hoy es martes 20/10. Quedan 4 días de la semana 3 (20–23/10) y el viernes es para actualizar el
servidor. No alcanzan para las seis.

## 1. Tabla

Esfuerzo = días de trabajo de Ivania con Claude (los encargos de Claude según la guía).
Riesgo = qué tan probable es que no se termine o que dependa de algo que no controlamos.

| Código | Ampliación | Valor para Hermatix | Esfuerzo | Riesgo | Qué ya existe / qué falta |
|---|---|---|---|---|---|
| A4 | Aviso de cierre próximo y resumen semanal | **Alto.** Una oportunidad marcada «Interesa» no se vence olvidada. El portal deja de mostrar un cartel al cerrar (observado 2026-10-08) y el caso de Turrialba mostró que el plazo manda | 1 día (5–8 encargos) | **Bajo.** Reutiliza la outbox, la clave de deduplicación y la vista previa que ya funcionan | Ya hay plazo calculado y motivo `cambio_plazo`. Falta el motivo nuevo «cierre próximo» y el resumen del lunes |
| A5 | Exportar a Excel el listado filtrado | **Medio.** Compartir con ventas sin darles acceso al panel | ½ día (2–4 encargos) | **Bajo.** El riesgo conocido (Excel destruye códigos de 24 dígitos) se evita guardando las celdas como texto | Necesita una dependencia nueva para escribir `.xlsx` (p. ej. `openpyxl`). Hay que justificarla |
| A3 | Medir precisión y cobertura de las reglas | **Medio-alto.** Saber cuánto confiar en el correo y demostrar si un cambio de reglas mejora o empeora | 1 día (5–8 encargos) | **Bajo-medio.** El código es sencillo. El límite son los datos: el golden set tiene 33 carteles y hay **pocas revisiones humanas** (unas 5), así que las cifras por familia serán poco confiables por ahora | Golden set al 100 %. Falta el comando `score-rules`, la página y guardar cada medición |
| A2 | Competencia: quién gana qué | **Alto (estratégico).** Ver dónde ganan Navsat, Skydata o Stremax y los precios de referencia | 1,5–2 días (6–10 encargos) | **Alto.** Los reportes «Adjudicaciones en firme» y «Contratos» se vieron en el portal, pero **nunca se descargaron**: no sabemos si traen el nombre del adjudicatario. Además hay que armar los alias con Oscar | Antes de comprometer el día: bajar una muestra (≈ 15 min) y revisar las columnas |
| A1 | Automatizar la descarga de SICOP | **Alto si fuera posible:** nadie tendría que descargar antes de las 8:00 | 1 jornada máximo (evaluación) | **Alto.** Cada descarga pide un código por correo y luego un enlace por correo (observado 6 y 7/10). Automatizarlo exige leer el buzón (permiso de Gmail **más amplio** que el de enviar) y revisar los términos de uso. «No viable» es un resultado probable y válido | Ya está documentado el flujo (`ACCESO_SICOP.md`). Falta revisar los términos de uso con Oscar |
| A6 | Importar XLSX / JSON | **Bajo.** El CSV funciona: 0 rechazos en todas las importaciones reales | ½ día (3–5 encargos) | Medio. El JSON de Ofertas llegó vacío; Excel pone en riesgo los identificadores | La guía dice: solo si SICOP los entrega de forma más confiable. No hay evidencia de eso |

## 2. Orden recomendado

1. **A4: aviso de cierre próximo.** Es la de más valor con menos riesgo y protege el objetivo principal: no
   perder oportunidades. Se apoya en lo que ya está probado (outbox y deduplicación).
2. **A5: exportar a Excel.** Es medio día y se puede hacer el mismo día que A4, como en la guía (lección 14).
   Es fácil de ver y de aceptar.
3. **A3: métricas de las reglas.** Es barata y deja medido el punto de partida. Con pocas revisiones, el
   primer número sirve sobre todo para comparar más adelante.
   → Con 1, 2 y 3 se cumple el Hito 3 (tres ampliaciones) con riesgo bajo.
4. **A2: competencia**, solo si la muestra de adjudicaciones trae el adjudicatario. Si no lo trae, se
   documenta y pasa a la semana 4 o al plan de continuidad.
5. **A1: evaluación corta (½ día).** El resultado esperado es «asistido»: mejorar el modo manual (por
   ejemplo, recordar a quien descarga). Se escribe `docs/DECISION_OBTENCION.md`.
6. **A6: no se hace** mientras el CSV siga funcionando.

## 3. Preguntas para Oscar

- ¿Está de acuerdo con el orden? ¿Hay alguna que para él valga más (por ejemplo, A2 para ventas)?
- A4: ¿cuántos días antes del cierre avisar (N)? ¿El resumen semanal va el lunes a las 8:00, con el mismo
  correo diario o aparte?
- A5: ¿quién de ventas lo usaría y qué columnas necesita?
- A1: ¿revisamos juntos los términos de uso del portal? ¿Aceptaría dar permiso de **lectura** del buzón
  licitaciones@ a la app? (Sin eso, A1 es «no viable».)

## 4. Decisión de Oscar

- Fecha:
- Orden elegido:
- Comentarios:
