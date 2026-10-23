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
