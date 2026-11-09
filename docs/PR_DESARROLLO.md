# Pull request de `desarrollo` → `main`

> Texto para pegar en GitHub al abrir el PR (título y cuerpo). Actualizado el 2026-11-09. El PR anterior (#4,
> unido el 29/10) llevó `main` a `7f5c558`.

**Título:** Rama desarrollo: gestor de documentos, Reporte con IA, asistente de elegibilidad, ayuda y detalle del
cartel rediseñado

---

## Qué trae esta rama

**102 commits** sobre `main` (`7f5c558`), sin conflictos. Migraciones **0024 a 0041**. Todo se construyó y se probó
en local; el servidor sigue en `02b569b`. La actualización está en **`docs/ACTUALIZACION_SERVIDOR.md`**.

### Gestor de documentos (pasos 1B a 5)
- Correo al nuevo encargado con el ciclo diario (0024), etapas del seguimiento: preparando, enviada, ganada y
  perdida (0025).
- Expediente del cartel: subir y bajar archivos (0027), notas (0028) y descargar todo en un ZIP.

### Reporte con IA (DECISION_IA.md, aceptado por Oscar el 29/10)
- Resumen ejecutivo con salida estructurada (0026), cola automática diaria con presupuesto, extracto en el correo.
- Prompts versionados v1 a v8: criterio de Hermatix (v2), garantías y plazos (v5), explicación detallada de la
  recomendación (v6–v7), FleetRun no es un taller (v8).
- **Reporte de cartel en PDF** (0036): hasta **3 páginas** (0039), con «¿Cumple?» (0038) y «Por qué se
  recomienda» al final.

### Asistente de elegibilidad (DECISION_IA.md §7, aprobado el 2/11)
- Perfil de Hermatix con documentos confidenciales (0029, 0035), lista de verificación con IA (0030), preguntas
  al encargado (0031–0032, 0034), resultado por requisito y constancia descargable (0033).
- Interruptor `ASSISTANT_ENABLED`. Los documentos de Hermatix no se mandan a la IA (`ASSISTANT_SEND_DOCUMENTS=false`).

### Ayuda dentro de la app
- 25 misiones paso a paso con capturas automáticas (base de EJEMPLO), botón «?» en cada pantalla, glosario y
  «¿Te sirvió?» por misión (0037).

### Panel y reglas
- Detalle del cartel rediseñado (franja arriba y 4 pestañas) y lista compacta de carteles.
- Exclusiones «elaboracion de planos», «construccion de paradas» y «basureros»; «grabacion de video» pasa a
  contexto. Golden set: 39 casos, 39/39.
- Perfil sin avisos de vencimiento (decisión de Ivania, 9/11).

### Robustez (9/11)
- Las transacciones empiezan con `BEGIN IMMEDIATE` y la base espera hasta 30 s si está ocupada: el ciclo del 5/11
  falló con «database is locked».
- Correos del enriquecimiento apagados por defecto (`ENRICH_EMAILS=false`).
- Tarea de Windows del ciclo: corre tarde si se perdió las 8:00.

### Documentos nuevos
- `docs/DECISION_PROPUESTA.md` (borrador, **sin aprobar**): que la app arme la oferta para SICOP.
- `docs/revision_reglas_vs_ia_20261109.md`: desacuerdos entre las reglas y la IA.

## Qué cambia al actualizar el servidor (`docs/ACTUALIZACION_SERVIDOR.md`)
- [ ] Respaldo de la base del servidor y de las unidades de systemd.
- [ ] La base del servidor se reemplaza por **la base local de Ivania** (esquema 0039; `migrate` aplica la 0040 y la 0041)
      con sus carpetas de datos.
- [ ] `pip install -r requirements.lock.txt`: se suman `playwright`, `openpyxl`, `pdfplumber` y `openai`.
- [ ] Carpetas nuevas en `/var/lib/sicop-connect` y variables nuevas en `app.env` (la clave de OpenAI, Oscar).
- [ ] El ciclo de las 8:00 y la cola de IA (10:45) pasan al servidor; se apaga la tarea de Windows. El
      enriquecimiento queda en pausa hasta terminar la fase 2 (`docs/ENVIO_ENRIQUECIMIENTO.md`).

## Para decidir (Oscar)
- [ ] Aprobar el Reporte PDF con la explicación y activar el prompt **v8**.
- [ ] ¿Le interesan a Hermatix los sensores IoT en general, no solo de frío y temperatura?
      (`docs/revision_reglas_vs_ia_20261109.md`, caso A2).
- [ ] La sección 6 de `docs/DECISION_PROPUESTA.md`.
- [ ] Fase 2 (en construcción): la PC manda el enriquecimiento al servidor con un token (`ENRICH_TOKEN`). Ya
      están las direcciones del servidor; falta el comando de la PC.

## Pruebas
- Suite completa con **Python 3.14** y con **Python 3.12** (el del servidor, entorno limpio con
  `requirements-dev.txt`): los resultados, en `ESTADO_PROYECTO.md`. Volver a correr las dos justo antes de unir. SICOP, Gmail y la IA se prueban con datos SIMULADOS.

## Importante
- Las guías en Word de `docs/` no están en Git (`.gitignore`).
- Las capturas de la ayuda tampoco: se llevan en el paquete de datos o se generan en el servidor.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
