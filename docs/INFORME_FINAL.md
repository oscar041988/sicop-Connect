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

> Actualizado el 2026-11-12. Ivania ya escribió en el Google Doc (26/10) la parte de **Windows** y la del
> **servidor como plan**. Lo marcado **(nuevo)** pasó entre el 26 y el 29/10, y lo marcado **(nuevo 12/11)**, entre
> el 30/10 y el 12/11: agrégalo a la parte de Windows. La parte del servidor se completa con los resultados reales
> de la lección 15 y de los simulacros allí: **el servidor todavía no se actualizó** (espera que Oscar una el PR).

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
- **(nuevo 12/11)** El PR #4 se unió por error el 29/10 desde la cuenta de Ivania (`main` = `7f5c558`; el servidor no
  cambió). Acuerdo desde entonces: solo Oscar une los PR. Hoy `desarrollo` lleva **146 commits** sobre `main`.
- **(nuevo 12/11)** Actualización del servidor **preparada, sin ejecutar** (`docs/ACTUALIZACION_SERVIDOR.md`, 09/11):
  de `02b569b` (esquema 0007) a `desarrollo`; se lleva la base local con sus carpetas; el ciclo de las 8:00 pasa al
  servidor y se apaga la tarea de Windows (si no, correos dobles). Falta que Oscar una el PR y elija el día.
- **(nuevo 12/11)** Enriquecimiento hacia el servidor (fase 2, `docs/ENVIO_ENRIQUECIMIENTO.md`, 09/11): la PC consulta
  SICOP y manda cada cartel al servidor con un token, solo HTTPS. Probado con la PC haciendo de servidor; falta
  probarlo contra el servidor real. Guía para otra computadora: `docs/TRASPASO_ENRIQUECIMIENTO.md` (11/11).
- **(nuevo 12/11)** Solicitud automática del reporte: la primera vuelta real (10/11, 15:00) encontró el **bloqueo de
  SICOP** («control no automatizable», con ID de soporte). El reporte se sigue pidiendo a mano (`SOURCE_MODE=manual`,
  confirmado con `doctor` el 12/11). `DECISION_OBTENCION.md` §8.

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
- **(nuevo 12/11)** **Envío real desde Windows** desde el lunes 2/11 a las 8:00 (antes la tarea corría siempre en
  dry-run). Del 2 al 12/11 Gmail aceptó **21 avisos de cartel nuevo, 3 de cambio de plazo, 3 de cierre próximo y 7
  resúmenes semanales**, más el correo de asignación de un encargado (30/10). Los enlaces del correo solo abren en
  la laptop (`APP_BASE_URL` local).
- **(nuevo 12/11)** Del 3 al 6/11 **no salió ningún aviso** (según el estado del 9/11, 18 «nueva» quedaron
  preparados; en la base, los 18 preparados que quedan tienen fecha del 13 al 27/10: por revisar): un día despertó tarde, otro la
  sesión se abrió después de las 8:00, otro la base estaba ocupada y otro Windows detuvo la tarea. Arreglo (9/11):
  la tarea corre tarde si se perdió las 8:00 (`StartWhenAvailable`) y la app espera hasta 30 s a la base. Ciclo
  del 9/11: OK, 12 avisos. Desde el 30/10, **22 cargas y ciclos, todos OK**.
- **(nuevo 12/11)** Tarea «SICOP CONNECT - resumenes IA» (lunes a viernes 14:00, creada el 11/11): segunda
  oportunidad si la cola de IA de las 10:00 falló. Las tareas programadas esperan hasta 10 min a la base (el 10/11
  una carga grande en el panel la ocupó más de 2 min y tumbó el enriquecimiento).
- **(nuevo 12/11)** Enriquecimiento: **13 corridas** (7 OK, 5 con algún fallo, 1 sin cola). Desde el 10/11 un cartel
  ya enriquecido no se vuelve a consultar (antes 44 de 173 consultas eran repetidas). Los correos del
  enriquecimiento se apagaron (9/11, decisión de Ivania).
- **(nuevo 12/11)** IA en operación: **158 llamadas, ≈ 4,48 USD estimados** del 29/10 al 11/11 (`ia_usage`); 85
  resúmenes (68 OK, 8 Revisar, 9 fallidos, sin resumen inventado) y 11 reportes PDF. Topes: 10 resúmenes y 5 USD
  al día. El 12/11, `ia recomparar` corrigió 2 resúmenes marcados Revisar por error, sin llamar a la IA.
- Ciclos reales a mano: #23, #25 y #28 importaron ZIP reales con 0 rechazadas.
- Respaldos: `backup` con manifiesto y huella; copia en ZIP al Drive de Hermatix (23/10; 26/10: `sicop_20261026-093951`
  y `sicop_20261026-115002`; **(nuevo)** 29/10: `sicop_20261026-135112`). **(nuevo)** Desde el 27/10, el respaldo
  también guarda los documentos de SICOP (`_documentos.zip`). **(nuevo 12/11)** Desde el 4/11 el respaldo va
  directo a `G:\Mi unidad\sicop-respaldos` (Google Drive para escritorio), carpeta compartida solo con Oscar (5/11);
  trae también expedientes, perfil, asistente y reportes. Último: `sicop_20261112-083011`.
- `OPERACION.md` seguido al pie de la letra en una instalación limpia (23/10): 10 trabas encontradas y corregidas.

**Datos de apoyo — simulacros** (`docs/OPERACION.md`, sección 7):

| # | Simulacro | Windows | Servidor |
|---|---|---|---|
| 1 | Reiniciar el servicio | no aplica (no hay servicio) | pendiente |
| 2 | Reiniciar el servidor | no aplica | pendiente |
| 3 | Restaurar un respaldo | ☑ 13/10, 19/10 y 23/10 (huella igual, revisión presente) | pendiente |
| 4 | Ciclo con fuente fallida | ☑ 19/10, ciclo #22: «FALLO… no significa que no haya compras», no avisó. También el 28/10, ciclo #38 (el reporte del día no estaba): FALLO, 0 avisos. **(nuevo 12/11)** Sin simulacro, pasó de verdad del 3 al 6/11: el ciclo no corrió y no salió ningún aviso (ver arriba) | pendiente |
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

> Actualizado el 2026-11-12. Ivania ya escribió esta sección en el Google Doc (26/10). Lo marcado **(nuevo)** no
> estaba el 26/10; lo marcado **(nuevo 12/11)** pasó entre el 30/10 y el 12/11. Lo «sin novedad registrada» no
> tiene cambios en `ESTADO_PROYECTO.md` desde el 29/10: confírmalo antes de escribirlo.

**Lo que cambió entre el 30/10 y el 12/11 (nuevo 12/11):** la IA pasó de construida sin clave a **operar todos
los días** (resúmenes, reporte PDF de hasta 3 páginas, asistente de elegibilidad y su chat); nacieron dos mejoras
que no estaban en el plan, **la oferta para SICOP** (económica, técnica y completa, en PDF y Word) y el **perfil
de Hermatix**; el gestor de documentos se terminó (pasos 1B a 5); el envío real de avisos empezó desde Windows; y
SICOP bloqueó la solicitud automática del reporte.

**Pendientes conocidos al 12/11, por responsable:**

*Para terminar el mes (lo que falta para que funcione solo):*
- ~~Oscar: revisar y unir el PR #3~~ unido (26/10). ~~Oscar: revisar y unir el PR #4~~ **unido por error el 29/10**
  (ver sección 6). **(nuevo 12/11)** Oscar: unir el PR `main` ← `desarrollo` (**146 commits**, migraciones hasta la
  0045; texto en `docs/PR_DESARROLLO.md`) y elegir el día de la actualización.
- Oscar con Ivania: actualizar el servidor (lección 15) **con la guía `docs/ACTUALIZACION_SERVIDOR.md`** (nuevo
  12/11); simulacros allí (lección 16); primera prueba real de punta a punta; apagar la tarea del ciclo en Windows
  el mismo día; probar el envío del enriquecimiento contra el servidor real; correr allí `ia recomparar`. ~~Activar
  dos solicitudes al día~~ **descartado por ahora: SICOP bloqueó la solicitud automática (10/11).** Sesión de la
  lección 10 con Oscar: sin novedad registrada.
- Oscar: cierre del acta (JSON de Google en USB y Mac, cargas del 16 y 19/10, historial del asistente, quitar el
  permiso de escritura en GitHub del servidor). Sin novedad registrada.
- Respaldos automáticos en el servidor (los hace Oscar). Sin novedad registrada. **(nuevo 12/11)** En Windows, el
  respaldo va al Drive compartido con Oscar desde el 4/11.
- Ivania: autoevaluaciones pendientes (enriquecimiento, lecciones 1 a 4; IA, lección 1). Sin novedad registrada.
- **(nuevo 12/11)** Ivania con Oscar: evaluar 5 carteles reales con el asistente de elegibilidad y anotar las
  diferencias con su criterio (solo se anotó `20261002824`).

*Decisiones abiertas:*
- ~~Obtención automática: espera la respuesta de SICOP~~ **Decidido por Oscar (26/10):** solicitud automática a las
  06:30 y 14:00 y descarga a mano con recordatorio. **(nuevo 12/11)** La primera solicitud real (10/11) también
  quedó bloqueada por SICOP, con un ID de soporte. **Oscar decide** si se consulta a SICOP con ese ID.
- Falso positivo «telemetría… Acueducto» (`20261000990`) en `iot_frio`: propuesta lista (pasar «telemetria» a señal
  media); falta que Oscar diga si Osmia IoT vende telemetría para acueductos (`docs/REGLAS.md` §6). **(nuevo
  12/11)** Va junto con `20261003868` (64 sensores LoRaWAN para inundaciones, salió Alta y se avisó; la IA dice
  descartar): ¿interesan los sensores IoT en general o solo frío y temperatura?
- Confirmar N = 3 días del cierre próximo y el contenido del resumen semanal. Sin novedad registrada.
- Adjudicaciones que llegan solas: hoy el ciclo queda en «fallo» y no avisa (decisión de Claude, por revisar). Sin
  novedad registrada.
- Que Oscar acepte `docs/DECISION_OBTENCION.md`; falta el Reglamento de SICOP. **(nuevo)** Que una persona relea
  las Condiciones de SICOP para el enriquecimiento (§9, punto 6). Sin novedad registrada.
- ~~IA: que Oscar acepte `docs/DECISION_IA.md` y cree el proyecto de OpenAI~~ **hecho:** aceptado el 29/10, clave y
  primera llamada real el 29/10. **(nuevo 12/11)** Abiertas: que Oscar apruebe el reporte para activar el prompt
  **v8** y confirme el **v5**; para **Anthropic** (aprobado el 5/11, construido el 11/11 sin llamar a la API real),
  la clave, el modelo, los precios y la comparación en 3 carteles; cuánto saldo queda en OpenAI.
- **(nuevo 12/11)** Oferta y chat (`DECISION_IA.md` §10, `DECISION_PROPUESTA.md`): qué significa «terminada» y qué
  se borra, dónde se guardan los documentos reales, adjuntos en el Word, el tarifario y los datos del representante
  (`config/oferta.yaml`), cómo se elige la ficha técnica de cada cartel y la oferta técnica de Tarrazú.
- **(nuevo)** Grabaciones del enriquecimiento: cuántos días guardarlas (728 MB en un día; ≈ 15 GB con 30 días). Sin
  novedad registrada.
- **(nuevo)** Revisar con Oscar las evidencias que salen de los PDF y ajustar el YAML si hay más falsos positivos.
  **(nuevo 12/11)** Revisión reglas vs IA del 9/11 (`docs/revision_reglas_vs_ia_20261109.md`): 41 carteles, 10
  desacuerdos; dos arreglados (A1 en las reglas, B1 en el prompt v8) y uno espera a Oscar (A2, arriba).
- **(nuevo)** El competidor `0702950024` es persona física: confirmar con Oscar que no se guarda su nombre. Sin
  novedad registrada.

*Mejoras (nuevo: empezadas después del 26/10; todas solo en local hasta actualizar el servidor):*
- **Enriquecimiento de carteles** (idea de Oscar): lecciones 1 a 4 hechas. Ficha y documentos desde SICOP, reglas
  sobre el texto de los PDF (como máximo suben a Media), panel con la información de SICOP y bitácora de consultas.
  Corre todos los días a las 10:00 en Windows. **(nuevo 12/11)** Fase 2 (envío al servidor) construida; falta
  probarla contra el servidor real.
- **Reporte de cartel con IA** **(nuevo 12/11: en operación):** cola automática de resúmenes (Alta → Media → Baja,
  10 al día), citas que abren el documento en su página (revisión de 11 citas en 10 carteles: 0 errores), extracto
  en el correo diario, Reporte PDF de hasta 3 páginas con «Por qué se recomienda» y «¿Cumple?». Prompt activo v5.
- **(nuevo 12/11) Asistente de elegibilidad** (lecciones 1 a 5): lista de verificación con IA, preguntas primero de
  los excluyentes, resultado «¿podemos participar?» con constancia, y desde el 11/11 **como chat**. Prueba completa
  en 2 de 3 carteles (5/11): funciona. Siguiente: paso 5 del chat, «Oferta terminada» y el borrado de los datos
  personales (`DECISION_IA.md` §10.4).
- **(nuevo 12/11) Perfil de Hermatix** (`/perfil`): lo que el asistente usa para responder. La **parte A** (datos,
  no documentos) está cargada; los documentos delicados van solo al servidor actualizado (decisión de Oscar, 4/11).
- **(nuevo 12/11) Oferta para SICOP** (pedido de Oscar; `DECISION_PROPUESTA.md` aprobado el 9/11): oferta económica
  con el formato de la ganadora de Tarrazú (la reproduce al céntimo), respuesta técnica punto por punto y la **oferta
  completa con un botón**, como la de NAVSAT, en PDF y en Word; se corrige conversando en el chat y cada cambio es
  una versión. La firma y la sube a SICOP una persona.
- **Gestor de documentos:** ~~paso 1A hecho~~ **(nuevo 12/11) pasos 1A a 5 hechos (29 y 30/10):** encargado, correo al nuevo
  encargado (salió el 30/10), notas, descarga del expediente y etapas preparando · enviada · ganada · perdida.
  **(nuevo 12/11)** Desde el 11/11, «Dar seguimiento» exige una revisión vigente (pedido de Oscar).

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
- ~~Pruebas: 667 passed (29/10)~~ **(nuevo 12/11)** Pruebas: **1083 passed** (12/11, `desarrollo` = `1d25e8f`).
- **(nuevo 12/11)** Dependencias nuevas: `python-docx` (Word) y `anthropic` (SDK oficial); en el servidor, `pip
  install -r requirements.lock.txt` con el PR.
- **(nuevo 12/11)** «database is locked» cuando dos programas escriben a la vez: arreglado el 9 y el 10/11 (`BEGIN
  IMMEDIATE`; espera de 30 s en el panel y de 10 min en las tareas). Consejo: subir el ZIP antes de las 10:00 o
  después de las 10:30.

**Datos para estimar horas** (`docs/METRICAS.md`): semana 2, 37,25 h estimadas · 49 h reales (+32 %); semana 3,
21 h (7 h por día, sin desglose por tarea); **(nuevo)** semana 4 (26–29/10), 28 h (7 h por día). Total del mes
hasta el 29/10: **123,5 h**. **(nuevo 12/11)** Del 30/10 al 12/11 **no hay horas anotadas** en `METRICAS.md`:
anótalas antes de estimar. Uso de Claude casi sin registrar: dilo así en la estimación.

**Escribe tú:** ordena los pendientes por valor para Hermatix y estima las horas de cada uno con los datos del
mes (sección 7). Incluye las tres mejoras en curso: ¿cuál va primero y por qué? Este es el entregable E10: lo
acepta Oscar el día 20.
