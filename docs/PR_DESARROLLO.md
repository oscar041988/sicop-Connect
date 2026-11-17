# Pull request de `desarrollo` → `main`

> Texto para pegar en GitHub al abrir el PR (título y cuerpo). Actualizado el 2026-11-17, al cerrar el proyecto.
> El PR anterior (#4, unido el 29/10) llevó `main` a `7f5c558`.

**Título:** Rama desarrollo: gestor de documentos, Reporte con IA, asistente de elegibilidad con chat, oferta
completa, ayuda, panel y «Productividad»

---

## Qué trae esta rama

**311 commits** sobre `main` (`7f5c558`), sin conflictos. Migraciones **0024 a 0047**. Todo se construyó y se probó
en local; el servidor sigue en `02b569b`. La actualización está en **`docs/ACTUALIZACION_SERVIDOR.md`**, y lo que
hay que hacer cada día o semana sin Ivania, en **`docs/TRASPASO.md`**.

### Gestor de documentos
- Correo al nuevo encargado con el ciclo diario (0024), etapas del seguimiento: preparando, enviada, ganada y
  perdida (0025).
- Expediente del cartel: subir y bajar archivos (0027), notas (0028) y descargar todo en un ZIP.
- Seguimiento con «Todos» y «Solo los míos». Revisión obligatoria antes de dar seguimiento y al salir del cartel
  (pedido de Oscar, 11/11).

### Reporte con IA (DECISION_IA.md, aceptado por Oscar el 29/10)
- Resumen ejecutivo con salida estructurada (0026), cola automática diaria con presupuesto, extracto en el correo.
- Prompts versionados v1 a **v10** (v8 aprobado por Oscar el 12/11; v9: hoja «De qué trata, explicado en detalle»;
  v10: esa hoja más larga, con cada característica y su cifra).
- **Reporte de cartel en PDF** (0036): hasta **5 páginas** (0039, 0046, 0047), con «¿Cumple?» (0038), «Por qué se
  recomienda» y «Explicado en detalle».
- Segunda vuelta de la cola a las 14:00 (si la de la mañana falló). `ia recomparar`: vuelve a comparar con SICOP
  los resúmenes guardados sin llamar a la IA.
- **Anthropic junto a OpenAI** (`AI_MODE=anthropic`, DECISION_IA §8, SDK oficial `anthropic` 2.8.0). Construido y
  probado con IA simulada; **falta la clave y el modelo** (Oscar). Hoy la app usa OpenAI.

### Asistente de elegibilidad (DECISION_IA.md §7 y §10)
- Perfil de Hermatix con documentos confidenciales (0029, 0035), lista de verificación con IA (0030), preguntas
  (0031–0032, 0034), «Lo tiene · archivo pendiente», resultado por requisito y constancia descargable (0033).
- **Asistente como chat** (0044, `ASSISTANT_CHAT`, aprobado por Oscar el 11/11): la IA propone las respuestas; la app
  las valida y las guarda. Con `ASSISTANT_SEND_DOCUMENTS=true` la IA lee el texto de los archivos subidos en el chat
  (Oscar, 11/11: sí, sin modificarlos). Probado con la IA real (prompt v7).
- Página propia con el diseño de la maqueta; «Lo que falta antes de pedir la oferta», con «Resolver» en cada punto.

### Propuestas (DECISION_PROPUESTA.md, aprobado por Oscar el 9/11)
- **Oferta completa con un botón** (0043), con el diseño de la de Tarrazú, en **PDF y en Word** (`python-docx`).
- Corregir la oferta desde el chat, con «Aplicar» y versiones (0045).
- Matriz de cumplimiento (respuesta técnica, primera parte, 0042). Formulario con borrador (0041).
- Comando: `python -m app.cli oferta economica --datos OFERTA.yaml`.

### Panel
- Detalle del cartel rediseñado (franja arriba y 4 pestañas) y lista compacta.
- **Una fila por cartel**: las otras familias van como etiquetas y en «Ver más»; el Excel, igual.
- Todo cartel revisado sale de «Todos» y queda en el chip de su decisión.
- «Último correo» arriba de la lista y el resumen semanal en su propia página.
- **«Productividad»** (menú): por semana, candidatos nuevos, revisados, los que cerraron sin revisión y, para
  administradores, «Por persona». Solo lee la base.
- Bitácora: «7 de 20 consultados hoy» y una persona picando mientras el enriquecimiento trabaja (también en el
  cartel); el aviso de FALLO o CAPTCHA solo el día del fallo.
- Competencia: nombre de todas las empresas ganadoras; la cédula de una persona física se etiqueta «Persona física»,
  sin guardar su nombre.

### Reglas
- Exclusiones «elaboracion de planos», «construccion de paradas», «basureros» y «aislamiento termico»; «grabacion
  de video» pasa a contexto. Golden set: 39 casos, 39/39 (reglas `a90bf850e7e5`).

### Ayuda dentro de la app
- 25 misiones paso a paso con capturas automáticas (base de EJEMPLO, 164 capturas), botón «?» en cada pantalla,
  glosario y «¿Te sirvió?» por misión (0037). La 26 es «Productividad».

### Robustez
- `BEGIN IMMEDIATE`; las tareas programadas esperan hasta 10 min si la base está ocupada; el panel, 30 s.
- La base queda en **modo WAL** con `migrate` (el panel lee mientras una tarea escribe). El respaldo sigue siendo un
  solo `.db`.
- El gasto de la IA se anota aunque la base esté ocupada (3 intentos).
- Correos del enriquecimiento apagados por defecto (`ENRICH_EMAILS=false`).
- **Fase 2 del enriquecimiento** (`docs/ENVIO_ENRIQUECIMIENTO.md`): la PC manda fichas y documentos al servidor con
  un token. Probado con la PC como servidor de prueba; falta contra el servidor real.

## Qué cambia al actualizar el servidor (`docs/ACTUALIZACION_SERVIDOR.md`)
- [ ] Respaldo de la base del servidor y de las unidades de systemd.
- [ ] La base del servidor se reemplaza por **la base local de Ivania** (ya en 0047) con sus carpetas de datos.
- [ ] `pip install -r requirements.lock.txt`: se suman `playwright`, `openpyxl`, `pdfplumber`, `openai`,
      `anthropic` y `python-docx`.
- [ ] Carpetas nuevas en `/var/lib/sicop-connect` y variables nuevas en `app.env` (las claves de la IA, Oscar).
- [ ] El ciclo de las 8:00 y la cola de IA (10:45 y 14:00) pasan al servidor; se apagan las tareas de Windows.
- [ ] El enriquecimiento sigue en una PC con Windows y manda lo suyo al servidor (fase 2).

## Para decidir (Oscar)
- [ ] La clave y el modelo de Anthropic, o seguir con OpenAI.
- [ ] Las opciones provisionales de «Productividad» (solo Alta y Media; «Por persona» solo para administradores).
- [ ] La evaluación del asistente con 5 carteles reales (`docs/evaluacion_asistente_20261117.md`).
- [ ] ¿Le interesan a Hermatix los sensores IoT en general, no solo de frío y temperatura? (caso A2 de
      `docs/revision_reglas_vs_ia_20261109.md`).
- [ ] Si se consulta a SICOP por el bloqueo de la solicitud automática (tiene ID de soporte).
- [ ] Qué computadora corre el enriquecimiento cuando Ivania no esté (`docs/TRASPASO_ENRIQUECIMIENTO.md`).

## Pruebas
- Suite completa con **Python 3.14**: **1136 passed** (17/11). Con **Python 3.12** (el del servidor) la última
  corrida fue de 964 (9/11): **volver a correrla antes de unir**. SICOP, Gmail y la IA se prueban con datos
  SIMULADOS.

## Importante
- Las guías en Word de `docs/` no están en Git (`.gitignore`).
- Las capturas de la ayuda tampoco: se llevan en el paquete de datos o se generan en el servidor.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
