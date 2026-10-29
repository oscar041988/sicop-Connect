# Informe final de SICOP CONNECT — esquema

> **Esquema, no informe.** La guía (sección 21.3) pide que el informe lo escriba Ivania **con sus palabras**. Aquí
> solo están las partes que pide, los datos que ya existen (con su fuente) y las preguntas a responder. Las cifras
> son del 2026-10-23: las métricas finales se recalculan en la lección 19 (sección 22 de la guía).
> Al escribir, reemplazar cada bloque «Escribe tú» por el texto propio y borrar las notas.

---

## 1. Resumen ejecutivo (1 página)

**Debe responder:** qué problema resuelve, qué se entregó, qué funciona hoy, qué falta y qué recomiendas.

**Datos de apoyo:** objetivos de la sección 2 · métricas de la sección 5 · pendientes de la sección 9.

**Escribe tú:** 4 párrafos cortos.
- El problema de Hermatix antes de SICOP CONNECT: ¿cómo se enteraban de un concurso?
- Qué hace la app hoy, en una frase.
- El estado real: qué está en producción y qué solo en local.
- Tu recomendación principal para las próximas 160 horas.

Escríbelo **al final**, cuando las demás secciones estén listas.

---

## 2. Objetivos O1–O8: cumplido / parcial / bloqueado, con evidencia

Definiciones: guía, sección «Objetivos» (O1 a O8). Estado propuesto al 23/10, **para que lo confirmes o corrijas**:

| Obj. | Qué pedía | Estado propuesto | Evidencia (dónde está) |
|---|---|---|---|
| O1 | Acceso a SICOP probado con archivo real y documentado | Cumplido (día 1, 06/10) | `docs/ACCESO_SICOP.md` |
| O2 | Archivo real cargado, códigos íntegros, recarga sin duplicados | Cumplido (Hito 1, 09/10) | `docs/MAPEO_DATOS.md`; importaciones reales con 0 rechazos |
| O3 | ≥ 80 % de acierto sobre el conjunto etiquetado por Oscar | Cumplido: 34/34 = 100 % | `docs/REGLAS.md`, sección 6; `tests/test_golden_medicion.py` |
| O4 | Archivo real → candidatos → panel → decisión persistente | Cumplido (Hito 1, 09/10) | `docs/BITACORA.md`, día 5 |
| O5 | Panel protegido en el servidor, correo real recibido, ciclo programado | **Parcial**: panel con HTTPS ☑ (15–19/10) · correo real desde el servidor ☑ (20/10) · ciclo programado ☐ (timer sin activar) | `docs/ACTA_DESPLIEGUE.md`, `docs/ACTA_LECCION_10.md` |
| O6 | ≥ 3 ampliaciones aceptadas por Oscar | **Parcial**: A2, A4 y A5 hechas y probadas en local; falta aceptación de Oscar (`docs/AMPLIACIONES.md` §4 vacía) y verlas en producción | PR #3; `docs/AMPLIACIONES.md` |
| O7 | Reinicio, respaldo restaurado y reversión probados | **Pendiente**: restauración y ciclo con fuente fallida probados solo en Windows; nada en el servidor | `docs/OPERACION.md`, sección 7 |
| O8 | Presentación, manuales verificados, métricas y plan de continuidad | **En curso**: `OPERACION.md` verificado en instalación limpia (23/10) ☑; `DESPLIEGUE.md` sin probar literalmente; lo demás, lecciones 19–20 | `docs/ESTADO_PROYECTO.md` |

**Escribe tú:** para cada «parcial» o «pendiente», **por qué** y **qué falta exactamente**. ¿Fue por el
calendario del servidor, por una decisión, por SICOP?

---

## 3. Arquitectura y decisiones técnicas (con alternativas descartadas y por qué)

**Datos de apoyo:** `docs/ARQUITECTURA.md` (diagrama y tabla de decisiones) · `docs/DECISION_OBTENCION.md` ·
`docs/REGLAS.md`.

**Elige 4 o 5 decisiones** y, para cada una, explica qué se eligió, qué se descartó y por qué. Candidatas, con
lo descartado:

| Decisión | Alternativa descartada | Dónde está el porqué |
|---|---|---|
| Reglas explicables en YAML | IA por API (`AI_MODE=none`) | guía; `docs/REGLAS.md` |
| Frase exacta | Permitir palabras intermedias (simulado con 1–3, no ayudaba) | `docs/REGLAS.md`, 1.2 y sección 6 |
| SQLite y un solo proceso web | Una base de servidor (PostgreSQL) | `docs/ARQUITECTURA.md`, 3 |
| Gmail por API con OAuth, solo enviar | SMTP con contraseña | `docs/GOOGLE_API.md` |
| ZIP de pliegos sin descomprimir (O4a) | Descomprimir a mano | `docs/DECISION_OBTENCION.md` |
| Obtención automática que se detiene ante un control | Intentar saltar CAPTCHA o bloqueos | `docs/DECISION_OBTENCION.md` §8 |
| Límite de login en memoria (opción A) | Guardarlo en la base | `ESTADO_PROYECTO.md` (2026-10-12) |
| Sin datos del día, no se avisa | Mandar el correo igual | `docs/OPERACION.md`, 3 |

**Escribe tú:** con tus palabras, como se lo explicarías a Oscar. Si quieres un diagrama, usa el de
`docs/ARQUITECTURA.md`, sección 1.

---

## 4. Fuente SICOP: lo comprobado y lo pendiente

**Comprobado (con archivo real):**
- Reportes usados: «Detalle pliego de condiciones» (carteles y líneas, ZIP), catálogo 10.2, instituciones 11,
  «Adjudicaciones en firme» (6, 6.1, 6.2). `docs/ACCESO_SICOP.md`, `docs/MAPEO_DATOS.md`.
- Identificadores de 8, 16 y 24 dígitos con ceros iniciales: Excel los daña.
- Fechas en hora de Costa Rica.
- El catálogo se descarga **un código de clasificación por vez**: hoy, 41 de 87 344 líneas tienen nombre de catálogo.
- El adjudicatario viene solo como cédula; «sin valor» se marca con un espacio.
- El portal solo muestra carteles con la recepción abierta; los cerrados solo están en datos abiertos (08/10).
- La descarga hecha por un programa fue **bloqueada** (prueba real del 22/10).

**Pendiente:** respuesta de soporte de SICOP (consulta del 22/10) · Reglamento de SICOP (no conseguido) ·
reporte «Contratos» (no usado).

**Escribe tú:** ¿qué te sorprendió de la fuente? ¿Qué es automático y qué necesita una persona, y por qué?
(Es también la pregunta del minuto 2–4 de la presentación.)

---

## 5. Calidad de reglas: métricas y evolución

**Datos de apoyo** (`docs/REGLAS.md`, secciones 1.6 y 6):

| Fecha | Golden set | Nota |
|---|---|---|
| 09/10 | 25/26 = 96,2 % | primer YAML (9 familias) |
| 09/10 | 25/28 = 89,3 % → 27/28 con líneas | la medición empezó a usar las líneas |
| 09/10 | 29/29 = 100 % | «localizacion satelital» |
| 12/10 | 33/33 = 100 % | 4 provisionales confirmados |
| 20/10 | 34/34 = 100 % | exclusión «intraoral» (falso positivo de la CCSS) |

- Candidatos hoy (reglas `b880e0d350e1`, 12 260 carteles reales): 22 Alta y 7 Media.
- 14 decisiones de reglas registradas, con fecha, quién decidió y el efecto medido.
- Falsos positivos conocidos y sus causas: `docs/REGLAS.md`, sección 5 («Trampas conocidas»).

**Límites honestos:** el golden set tiene 34 carteles y hay muy pocas revisiones humanas (5 en la base). La
precisión y la cobertura **por familia** se miden desde el 23/10 con `score-rules` (A3): primera medición, 95,0 %
de precisión y 100 % de cobertura por cartel, con 2 errores (`docs/REGLAS.md`, 4.1).

**Escribe tú:** ¿cuánto se puede confiar en una alerta? ¿Por qué hay falsos positivos y cómo se corrigen? (Minuto
9–12 de la presentación.)

---

## 6. Operación: despliegue, simulacros, recuperación

> Actualizado el 2026-10-29. Ivania ya escribió en el Google Doc (26/10) la parte de **Windows** y la del
> **servidor como plan**. Lo marcado **(nuevo)** pasó después del 26/10: agrégalo a la parte de Windows. La
> parte del servidor se completa con los resultados reales de la lección 15 y de los simulacros allí.

**Datos de apoyo — despliegue:**
- Instalación del 15/10 en Hostinger, con HTTPS y login: `docs/ACTA_DESPLIEGUE.md`. El servidor sigue en
  `02b569b`; desde el 21/10 (decisión de Oscar) todo se hace en local y el servidor se actualiza una sola vez, al
  final.
- GitHub: Oscar unió el PR #3 (`main` = `2dc0e52`, 26/10). **(nuevo)** El PR #4 (`main` ← `desarrollo`) espera a
  Oscar: hoy lleva 26 commits (enriquecimiento lecciones 1 a 4, obtención en dos turnos, baja de usuarios, IA
  lecciones 1 y 2; migraciones 0016 a 0023).
- En el servidor los avisos están en dry-run y el ciclo programado no está activado. El plan para activarlo está en
  `docs/DESPLIEGUE.md` 9.9 (aprobado por Oscar el 26/10): solicitud a SICOP a las **06:30 y 14:00**, descarga a
  mano con un recordatorio por correo (SICOP bloquea la descarga hecha por un programa), «Cargar archivo» evalúa al
  subir y el **envío real solo a las 8:00**.
- Sin verificar en el servidor: Playwright (el enriquecimiento lo necesita) y el espacio en disco para documentos y
  grabaciones.

**Datos de apoyo — operación en Windows (hecho):**
- Tarea «SICOP CONNECT - ciclo diario», lunes a viernes 8:00, siempre dry-run, registro en
  `data\logs\ciclo-AAAA-MM.log` (`deploy/windows/README.md`).
- **(nuevo)** Tarea «SICOP CONNECT - enriquecimiento», lunes a viernes 10:00 (creada por Ivania el 27/10): consulta
  en SICOP la ficha y los documentos de hasta 20 carteles por día, como lo haría una persona, con video de cada
  consulta. Necesita la sesión de Windows iniciada (abre una ventana del navegador). Si aparece un CAPTCHA o un
  bloqueo, reintenta una vez a los 15 min y, si sigue, se detiene y avisa.
  - Corrida #1 (27/10, a mano): 3 de 3, sin CAPTCHA. Corrida #3 (28/10, la primera automática): **13 de 13**, 0
    fallos, sin CAPTCHA ni bloqueo, 10:00 → 10:40; 106 documentos guardados; 2 carteles borrados al cierre.
- **(nuevo)** La computadora suspendida: el 28/10 el ciclo de las 8:00 **no corrió** (despertó a las 08:02) y la
  tarea no corre tarde, a propósito. Arreglo (aprobado por Ivania): las dos tareas despiertan la computadora
  (`-WakeToRun`), solo cuando está conectada al cargador. **Comprobado el 29/10:** ciclo #41 a las 08:00:02, OK.
- **(nuevo)** Espacio después de un día de enriquecimiento: grabaciones 728 MB (se borran a los 30 días, menos las
  de un fallo sin revisar: podría llegar a ≈ 15 GB; por decidir con Oscar) y documentos 212 MB.
- Ciclos reales a mano: #23, #25 y #28 importaron ZIP reales con 0 rechazadas.
- Respaldos: `backup` con manifiesto y huella; copia en ZIP al Drive de Hermatix (23/10; 26/10: `sicop_20261026-093951`
  y `sicop_20261026-115002`; **(nuevo)** 29/10: `sicop_20261026-135112`). **(nuevo)** Desde el 27/10, el respaldo
  también guarda los documentos de SICOP (`_documentos.zip`).
- `OPERACION.md` seguido al pie de la letra en una instalación limpia (23/10): 10 trabas encontradas y corregidas.

**Datos de apoyo — simulacros** (`docs/OPERACION.md`, sección 7):

| # | Simulacro | Windows | Servidor |
|---|---|---|---|
| 1 | Reiniciar el servicio | no aplica (no hay servicio) | pendiente |
| 2 | Reiniciar el servidor | no aplica | pendiente |
| 3 | Restaurar un respaldo | ☑ 13/10, 19/10 y 23/10 (huella igual, revisión presente) | pendiente |
| 4 | Ciclo con fuente fallida | ☑ 19/10, ciclo #22: «FALLO… no significa que no haya compras», no avisó. También el 28/10, ciclo #38 (el reporte del día no estaba): FALLO, 0 avisos | pendiente |
| 5 | Repetir el ciclo | ☑ 22/10, ciclo #28: 0 avisos nuevos, los 6 del 21/10 no se repitieron; 24 avisos = 24 claves distintas. **(nuevo)** 29/10, ciclo #41: 3 ya avisados antes no se repitieron | pendiente |

**Falta** (lecciones 15 y 16): actualizar el servidor y hacer allí los 5 simulacros, con envío real supervisado.

**Escribe tú:** ¿qué sigue funcionando con tu computadora apagada o suspendida? ¿Qué hace Hermatix si se pierde la
base? ¿Y si se pierden los documentos? (Minuto 14–16 de la presentación.)

---

## 7. Uso de Claude: plan vs. real, lecciones para futuros proyectos

**Datos de apoyo** (`docs/METRICAS.md`):
- Horas humanas: semana 1 (06–09/10) 25,5 h · semana 2 (12–20/10) 49 h · semana 3 (21–23/10) 21 h (7 h por día,
  sin desglose por tarea) · **total 95,5 h**.
- Semana 2: 37,25 h estimadas por la guía · 49 h reales (+32 %), con la lección 10 todavía abierta. La semana 3
  no se compara por lección (trabajo en local y ampliaciones, fuera del orden de la guía).
- Uso de Claude: casi **no registrado**. Semana 1: 24 % semanal al cierre (09/10). Semana 2: solo el 12/10 (29 %
  y 28 % de la ventana, 33 % semanal). Semana 3: no registrado. La guía pedía anotar `/usage` al cerrar cada día.

**Para tus lecciones aprendidas** (ejemplos reales del proyecto):
- La revisión general del 23/10 encontró 3 errores que las 470 pruebas no detectaban.
- Probar con Python 3.12, el del servidor, encontró una falla de seguridad que en 3.14 no aparecía.
- Seguir el manual en una instalación limpia encontró 10 trabas que quien lo escribió no veía.

**Escribe tú:** ¿dónde estuvo el cuello de botella: Claude, tus horas, el servidor o las decisiones? ¿Qué harías
distinto? Sé honesta con lo que no se registró: la guía dice que nunca se estima después.

---

## 8. Aprendizaje por semana, con los retos de comprensión

**Datos de apoyo:**
- Semana 1: Hito 1 cerrado el 09/10; reto de comprensión **superado**.
- Semana 2: reto practicado el 20/10 (3 correctas, 1 a medias); el **oficial**, con Oscar, pendiente.
  Autoevaluaciones de las lecciones 9 y 10: las tres correctas en cada una, con ajustes.
- Semana 3: ampliaciones A2, A4 y A5, obtención automática, revisión general.
- Semana 4: pendiente.

**Escribe tú:** por semana, 2 o 3 conceptos que ahora entiendes y antes no, con un ejemplo del proyecto. Por
ejemplo: la huella del archivo frente a la huella del cartel; por qué el temporizador va al final.

---

## 9. Pendientes y plan de continuidad

**Datos de apoyo:** `docs/ESTADO_PROYECTO.md` («Pendientes») · guía, sección 23.2 (plan de las 160 horas).

> Actualizado el 2026-10-29. Ivania ya escribió esta sección en el Google Doc (26/10). Desde entonces: el PR #3 se
> unió, se agregaron tres mejoras (enriquecimiento de carteles, reporte con IA y gestor de documentos) y se
> cerraron varios pendientes. Lo marcado **(nuevo)** no estaba el 26/10.

**Pendientes conocidos al 29/10, por responsable:**

*Para terminar el mes (lo que falta para que funcione solo):*
- ~~Oscar: revisar y unir el PR #3~~ unido (26/10). **(nuevo)** Oscar: revisar y unir el **PR #4** (26 commits,
  migraciones 0016 a 0023); cerrar los PR de ramas ya incluidas; decidir «Para decidir» de la descripción.
- Oscar con Ivania: actualizar el servidor (lección 15) y activarlo según `DESPLIEGUE.md` 9.9 (dos solicitudes al
  día, recordatorio de descarga, envío real a las 8:00); simulacros allí (lección 16); primera prueba real de punta a
  punta; sesión de la lección 10 con Oscar.
- Oscar: cierre del acta (JSON de Google en USB y Mac, cargas del 16 y 19/10, historial del asistente, quitar el
  permiso de escritura en GitHub del servidor).
- Respaldos automáticos en el servidor (los hace Oscar).
- Ivania: autoevaluaciones pendientes (enriquecimiento, lecciones 1 a 4; IA, lección 1).

*Decisiones abiertas:*
- ~~Obtención automática: espera la respuesta de SICOP~~ **Decidido por Oscar (26/10):** solicitud automática a las
  06:30 y 14:00 y descarga a mano con recordatorio, porque SICOP bloquea la descarga hecha por un programa. Sigue
  sin registrarse la respuesta de soporte de SICOP a la consulta del 22/10.
- Falso positivo «telemetría… Acueducto» (`20261000990`) en `iot_frio`: propuesta lista (pasar «telemetria» a señal
  media); falta que Oscar diga si Osmia IoT vende telemetría para acueductos (`docs/REGLAS.md` §6).
- Confirmar N = 3 días del cierre próximo y el contenido del resumen semanal.
- Adjudicaciones que llegan solas: hoy el ciclo queda en «fallo» y no avisa (decisión de Claude, por revisar).
- Que Oscar acepte `docs/DECISION_OBTENCION.md`; falta el Reglamento de SICOP. **(nuevo)** Que una persona relea
  las Condiciones de SICOP para el enriquecimiento (§9, punto 6).
- **(nuevo)** IA: que Oscar acepte `docs/DECISION_IA.md` y cree el proyecto de OpenAI con límite de gasto, la clave,
  el modelo y los precios. Sin eso no hay primera llamada real (lección 2 construida sin clave).
- **(nuevo)** Grabaciones del enriquecimiento: cuántos días guardarlas (728 MB en un día; ≈ 15 GB con 30 días).
- **(nuevo)** Revisar con Oscar las evidencias que salen de los PDF y ajustar el YAML si hay más falsos positivos.
- **(nuevo)** El competidor `0702950024` es persona física: confirmar con Oscar que no se guarda su nombre.

*Mejoras en curso (nuevo: empezadas después del 26/10, todas solo en local):*
- **Enriquecimiento de carteles** (idea de Oscar): lecciones 1 a 4 hechas. Ficha y documentos desde SICOP, reglas
  sobre el texto de los PDF (como máximo suben a Media), panel con la información de SICOP y bitácora de consultas.
  Corre todos los días a las 10:00 en Windows.
- **Reporte de cartel con IA:** lección 1 (el expediente que se le mandaría a la IA; Ivania leyó 3) y lección 2 (el
  cliente de OpenAI, sin clave y sin llamar). Siguen las demás lecciones de la guía después de la aprobación
  escrita de Oscar.
- **Gestor de documentos:** paso 1A hecho (seguimiento y encargado). Siguiente: paso 1B, el correo al nuevo
  encargado; hasta el paso 5 (etapas preparando · enviada · ganada · perdida, aprobadas el 26/10).

*Mejoras con valor para Hermatix:*
- Competidores: 7 empresas ya tienen nombre en `config/competidores.yaml` (26/10). Falta decidir si se descarga
  «Contratos» y corregir que la página cuente como competidor a quien ganó cualquier línea de un cartel de la
  familia.
- Más catálogo: buscar por nombre los códigos de las 6 familias que aún no tienen.
- **(nuevo)** Cartel modificado en SICOP con otro cierre: los datos abiertos pueden llegar atrasados y el panel lo
  oculta como vencido (caso Santa Ana `20261001587`: SICOP dice 30/10, los datos abiertos 23/10). La ficha lo
  detecta; falta que el panel use ese cierre.
- **(nuevo)** Excel, Word e imágenes de los carteles no aportan texto a las reglas ni a la IA (ej.: lista de
  insumos del INS, especificaciones del kiosco de la CCSS).
- Candidatos de la guía (23.2): consolidación con el uso real, integración con ventas, ampliación regional.

*Técnico:*
- Una prueba falló una vez con Python 3.12 y no se repitió (sin identificar).
- Playwright en el servidor Ubuntu: pendiente de verificar (ahora lo necesita también el enriquecimiento).
- **(nuevo)** Dos avisos «FontBBox» al leer un PDF el 28/10: no detuvieron nada; no se revisó si ese PDF perdió
  texto.
- **(nuevo)** Pruebas: 667 passed (29/10, `desarrollo` = `b51b532`).

**Datos para estimar horas** (`docs/METRICAS.md`): semana 2, 37,25 h estimadas · 49 h reales (+32 %); semana 3,
21 h (7 h por día, sin desglose por tarea). Total del mes hasta el 23/10: 95,5 h. **Desde el 24/10 no hay horas
anotadas:** anótalas antes de estimar. Uso de Claude casi sin registrar: dilo así en la estimación.

**Escribe tú:** ordena los pendientes por valor para Hermatix y estima las horas de cada uno con los datos del
mes (sección 7). Incluye las tres mejoras en curso: ¿cuál va primero y por qué? Este es el entregable E10: lo
acepta Oscar el día 20.
