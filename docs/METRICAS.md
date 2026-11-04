# Métricas semanales (plan vs. real)

Para la revisión semanal (guía 8.3) y para las métricas del mes (guía, sección 22). Estimado: agenda de cada
lección en la guía. Real: horas humanas que informa Ivania. Lo que no se anotó se escribe «no registrado»; nunca
se estima después.

## Semana 2 — lecciones 6 a 10 (calendario: 12 al 16/10; se extendió al 19 y 20/10)

### Horas por lección (estimado de la guía)

| Lección | Estimado | Estado al 20/10 |
|---|---|---|
| 6 · Proteger el panel | 7,5 h | cerrada el 12/10 |
| 7 · Avisar sin repetir | 7,5 h | cerrada el 13/10 (prueba real de envío, vista previa aprobada por Oscar) |
| 8 · Un solo comando para todo el ciclo | 7,5 h | cerrada el 13/10 (según `ESTADO_PROYECTO.md`) |
| 9 · Llevar la aplicación al servidor | 7,5 h | cerrada el 19/10 (la instalación del 15/10 la hizo la herramienta de Oscar) |
| 10 · Que funcione solo cada mañana (Hito 2) | 7,25 h | abierta: falta la sesión con Oscar |
| **Total** | **37,25 h** | |

### Horas reales por día

| Día | Horas | Trabajo | Fuente |
|---|---|---|---|
| lun 12/10 | 10 h | lección 6 (7 h) y comienzo de la 7 (3 h) | bitácora |
| mar 13/10 | 7 h | resto de la lección 7 y la lección 8 (las dos cerradas ese día) | Ivania, 20/10 · `ESTADO_PROYECTO.md` |
| mié 14/10 | 7 h | no registrado por lección | Ivania, 20/10 |
| jue 15/10 | 7 h | no registrado por lección (ese día Oscar instaló en el servidor) | Ivania, 20/10 |
| vie 16/10 | 7 h | página «Avisos» (rama `reintento-avisos`) y otros no registrados | Ivania, 20/10 · `ESTADO_PROYECTO.md` |
| lun 19/10 | 5 h | cierre de la lección 9 | bitácora |
| mar 20/10 | 6 h | lección 10 y pendientes sin Oscar | bitácora |
| **Total** | **49 h** | | |

Plan vs. real: 37,25 h estimadas para las 5 lecciones · 49 h reales en 7 días, con la lección 10 todavía abierta
(+11,75 h, un 32 % más). Las horas de Oscar y de su herramienta en el despliegue no están incluidas.

Por qué se pasó (a confirmar con Oscar en la revisión):
- El despliegue dependió del calendario de Oscar: la lección 9 se cerró el 19/10, cuatro días después de lo previsto.
- Trabajo fuera de la guía: niveles de acceso y página «Usuarios» (pedido de Oscar), fin de línea LF, prueba paso a
  paso de `OPERACION.md` (13 hallazgos), regla de cámaras, aviso de datos sin evaluar, carga del ZIP de pliegos.
- 13 al 16/10 no tienen entrada en la bitácora, así que no se puede repartir ese tiempo por lección. Dato a
  favor: las lecciones 7 y 8 juntas (15 h estimadas) se cerraron con 3 h el 12/10 y 7 h el 13/10, unas 10 h.

### Uso de Claude

| Día | Encargos | % de ventana | % semanal |
|---|---|---|---|
| lun 12/10 | no registrado | 29 % (mañana) · 28 % (tarde) | 33 % |
| 13 al 16/10 | no registrado | no registrado | no registrado |
| 19 y 20/10 | no registrado | no registrado | no registrado |

La guía estima 8–12 encargos y ≈ 45–60 min de Claude por lección. Sin registro diario no se puede comparar;
para la semana 3: anotar `/usage` al cerrar cada día.

### Aprendizaje y entregas

- Reto de comprensión de la semana 2: practicado el 20/10 (cuatro respuestas); el oficial, con Oscar.
- Autoevaluaciones: lección 9 y lección 10 (las tres correctas en cada una, con ajustes).
- Hito 2: **parcial**. Funciona el ciclo en dry-run y el envío real con `notify --send`; falta activar el
  temporizador y la prueba con Oscar (`docs/ACTA_LECCION_10.md`, pasos 0–4).

## Semana 3 — ampliaciones y obtención automática (21 al 23/10)

Desde el 21/10 todo se trabaja en local (decisión de Oscar) y las lecciones de la guía no se siguieron una por una,
así que esta semana no se compara por lección: se registran las horas reales y lo que se hizo.

### Horas reales por día

| Día | Horas | Trabajo | Fuente |
|---|---|---|---|
| mié 21/10 | 7 h | cambio a trabajo en local y rama `desarrollo`; ciclo local en Windows con datos reales; obtención automática, lecciones 1 a 3 (pruebas simuladas) | Ivania, 23/10 · `ESTADO_PROYECTO.md` |
| jue 22/10 | 7 h | prueba real de la obtención con Oscar (SICOP bloqueó la descarga) y consulta a soporte; lección 4 (`obtain auto`); A2 Competencia; A4 cierre próximo y resumen semanal; A5 Excel | Ivania, 23/10 · `ESTADO_PROYECTO.md` |
| vie 23/10 | 7 h | revisión general del código (3 errores y 4 menores); lock con `playwright`; documentación verificada y `ARQUITECTURA.md`; pruebas con Python 3.12 (falla de seguridad corregida); PR #3; `OPERACION.md` en instalación limpia (10 trabas); respaldo al Drive; informe final | Ivania, 23/10 · `ESTADO_PROYECTO.md` |
| **Total** | **21 h** | | |

### Uso de Claude

No registrado (no se anotó `/usage` al cerrar cada día). Para la semana 4: anotarlo cada día, porque es la
métrica que la guía considera más valiosa para Hermatix (sección 22).

### Aprendizaje y entregas

- Ampliaciones A2, A4 y A5 hechas y probadas en local; falta la aceptación de Oscar y verlas en producción.
- `OPERACION.md` seguido al pie de la letra en una instalación limpia (lección 18, paso 2, adelantada).
- Informe final escrito por Ivania (Google Docs).
- Reto de comprensión: el de la semana 2 sigue pendiente con Oscar.

## Semana 4 — enriquecimiento, reporte con IA y mejoras de Oscar (26 al 29/10)

Igual que la semana 3: trabajo en local, fuera del orden de la guía; se registran las horas reales y lo que se hizo.
El sábado 24 y el domingo 25 no se trabajó.

### Horas reales por día

| Día | Horas | Trabajo | Fuente |
|---|---|---|---|
| lun 26/10 | 7 h | mejoras de la exposición con Oscar (ayuda en «Cargar archivo», eliminar usuario, obtención en dos turnos y envío real en código); gestor de documentos paso 1A; los vencidos salen del panel; propuesta «telemetría»; 7 competidores con nombre; informe (secciones 6, 7 y 9); respaldos al Drive | Ivania, 29/10 · `ESTADO_PROYECTO.md` |
| mar 27/10 | 7 h | enriquecimiento lecciones 1 a 4 (exploración, fichas, documentos, cola y tarea de las 10:00, panel, reglas sobre los PDF), con 4 pruebas reales; PR #4 | Ivania, 29/10 · `ESTADO_PROYECTO.md` |
| mié 28/10 | 7 h | primera corrida automática del enriquecimiento (13 de 13); arreglo del ciclo que no corrió (despertar la computadora); reporte con IA lecciones 1 (expedientes leídos, 3 hallazgos) y 2 (cliente de OpenAI sin clave) | Ivania, 29/10 · `ESTADO_PROYECTO.md` |
| jue 29/10 | 7 h | `DECISION_IA.md` aceptado; primera prueba con OpenAI (401); botón «Ver» en los documentos; esquema del informe (6 y 9) al día; autoevaluaciones (enriquecimiento 1 a 4, IA 1); PR #4 | Ivania, 29/10 · `ESTADO_PROYECTO.md` |
| **Total** | **28 h** | | |

### Uso de Claude

No registrado.

## Métricas del mes (guía, sección 22) — preliminar al 23/10

**Preliminar.** La lección 19 (29/10) calcula las métricas del mes con dos semanas de uso real en el servidor;
hoy el servidor tiene una versión vieja y el uso real está en la base local de Windows. Estas cifras salen de esa
base (`data/sicop.db`, leída en solo lectura el 23/10, reglas `b880e0d350e1`) y de las bitácoras. Hay que
recalcularlas el 29/10 con la base del servidor.

### Valor comercial

| Métrica | Valor al 23/10 | Fuente |
|---|---|---|
| Carteles procesados | 12 260 (publicados del 07/07 al 21/10), con 87 344 líneas | `tenders`, `tender_lines` |
| Importaciones reales | 22, todas con **0 filas rechazadas** | `imports` |
| Oportunidades Alta / Media | 28 carteles (22 Alta y 7 Media; uno es Alta en una familia y Media en otra) | `opportunity_assessments` |
| Que el proceso manual no habría visto (señal **solo en las líneas**) | 3 de los 28 (en 21 la evidencia incluye alguna línea) | evidencia de `opportunity_assessments` |
| Revisadas | 4 carteles (5 revisiones): 3 «Interesa», 1 «No interesa» | `reviews` |
| Adjudicaciones para Competencia | 9 155 carteles adjudicados (julio a octubre) | `adjudicaciones` |
| Tiempo de revisión manual ahorrado por semana | **pendiente: estimarlo con Oscar** | — |

### Calidad

| Métrica | Inicio | Hoy | Fuente |
|---|---|---|---|
| Acierto del golden set | 25/26 = 96,2 % (09/10, primer YAML) | 34/34 = 100 % (20/10) | `docs/REGLAS.md`, sección 6 |
| Precisión por cartel (`score-rules`) | — (A3 no existía) | 95,0 % (19/20) | `docs/REGLAS.md`, 4.1 (copia de la base real) |
| Cobertura por cartel (`score-rules`) | — | 100 % (19/19) | ídem |

La primera medición de `score-rules` es del 23/10: el «inicio vs. final» por familia se podrá comparar después del
próximo ajuste de reglas.

### Operación

| Métrica | Valor al 23/10 | Fuente |
|---|---|---|
| Ciclos ejecutados | 16 (13/10 al 22/10, todos a mano o con la tarea de Windows, en dry-run) | `source_runs` |
| Ciclos fallidos | 12 de 16: casi todos «no llegó ningún archivo nuevo» (correcto: sin datos no se avisa) | `source_runs` |
| Correos enviados | 3 correos reales aceptados por Gmail, uno por destinatario, el 13/10 (9 avisos), con autorización. El envío desde el servidor del 20/10 está en la base del servidor | `notification_outbox` |
| Avisos duplicados | **0** (meta: 0) | `notification_outbox` |

### Uso de Claude

| Semana | Horas humanas | Uso de Claude registrado | Fuente |
|---|---|---|---|
| 1 (06–09/10) | 25,5 h | % semanal al cierre: 24 % (09/10) | `docs/BITACORA.md` |
| 2 (12–20/10) | 49 h | 33 % el 12/10; después, no registrado | sección «Semana 2» |
| 3 (21–23/10) | 21 h | no registrado | sección «Semana 3» |
| 4 (26–29/10) | 28 h | no registrado | sección «Semana 4» |
| **Total** | **123,5 h** | incompleto | |

Interacciones totales y veces que se agotó la ventana: **no registradas**. Comparación con la estimación del anexo
A de la guía: pendiente para la lección 19.

### Aprendizaje

| Reto de comprensión | Estado |
|---|---|
| Semana 1 | Superado (Hito 1, 09/10) |
| Semana 2 | Practicado el 20/10 (3 correctas, 1 a medias); el oficial con Oscar, pendiente |
| Semana 3 | Pendiente |
