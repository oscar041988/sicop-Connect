# Arquitectura de SICOP CONNECT

Cómo está construida la app: qué piezas tiene, por dónde pasa un dato y por qué se decidió así (guía, sección 15).
Comprobado contra el código de la rama `desarrollo` el 2026-10-23. Cómo se usa: `docs/OPERACION.md`; cómo se
instala: `docs/DESPLIEGUE.md`; cómo deciden las reglas: `docs/REGLAS.md`.

## 1. Vista general

**Una sola aplicación Python, sin microservicios.** El panel web y el ciclo diario comparten la base SQLite, pero
corren como **procesos separados**: el ciclo lo lanza el programador del sistema (systemd en el servidor, el
Programador de tareas en Windows). Nunca se programa nada dentro del proceso web: con dos procesos web, o con un
reinicio a mitad, se podrían duplicar envíos.

```text
  PORTAL SICOP (datos abiertos)                                  GMAIL (licitaciones@)
        │ ZIP / CSV                                                ▲ envío (gmail.send)
        │                                                          │
        ▼                                                          │
 ┌─────────────────────┐   descarga manual  ┌──────────────────┐   │       ┌──────────────────────┐
 │ Obtención           │ ─────────────────▶ │  INCOMING_DIR    │   │       │  Panel web (FastAPI) │
 │ · manual (hoy)      │                    │  (carpeta de     │   │       │  sicop-web.service   │
 │ · obtain auto       │ ── ZIP validado ─▶ │   entrada)       │   │       │  login · lista ·     │
 │   (construida, NO   │                    └────────┬─────────┘   │       │  detalle · revisión ·│
 │   activada)         │                             │             │       │  carga · Excel ·     │
 └─────────────────────┘                             ▼             │       │  competencia · admin │
                                    ┌─────────────────────────────────┐    └──────────┬───────────┘
                                    │ run-cycle (sicop-cycle.service, │                │
                                    │ lunes a viernes 8:00)           │      carga de archivos
                                    │ recoger → importar → evaluar →  │      (mismos importadores)
                                    │ avisar (+ resumen los lunes)    │                │
                                    └───────────────┬─────────────────┘                │
                                                    ▼                                  ▼
                              ┌───────────────────────────────────────────────────────────────┐
                              │ SQLite (DATABASE_PATH) · migraciones 0001–0016                │
                              │ raw_snapshots · tenders · tender_lines · catálogo · instit.   │
                              │ opportunity_assessments · reviews · notification_outbox ·     │
                              │ adjudicaciones · users · audit_log · source_runs · …          │
                              └───────────────────────────────────────────────────────────────┘
                                                    ▲
                     config/hermatix_rules.yaml ────┘ (las reglas: se leen al evaluar)
```

Tres formas de que un archivo entre, **el mismo importador** para las tres: la carpeta de entrada (el ciclo), la
página «Cargar archivo» del panel y la terminal (`python -m app.cli import --path ARCHIVO --report TIPO --origen real`).

## 2. Componentes

| Componente | Tecnología | Responsabilidad | Dónde |
|---|---|---|---|
| Panel | FastAPI + Jinja2 + HTML/CSS (sin JavaScript de terceros) | Rutas web, formularios, sesión, CSRF | `app/main.py`, `app/web/` |
| Almacenamiento | SQLite con migraciones versionadas | Datos, revisiones, outbox, auditoría | `app/database.py`, `migrations/` |
| Importadores | Python (`csv`, `zipfile`), todo como texto | Validar y guardar los reportes de SICOP | `app/importers/` |
| Reglas | `config/hermatix_rules.yaml` + Python | Familia, prioridad y evidencia de cada cartel | `app/matching/` |
| Avisos | API de Gmail (OAuth, solo `gmail.send`) | Vista previa, envío explícito, deduplicación | `app/avisos.py`, `app/resumen.py`, `app/notifications/` |
| Obtención | Manual; automática con Playwright + lectura de Gmail (no activada) | Llevar archivos completos a la carpeta de entrada | `app/sources/` |
| Operación | CLI `python -m app.cli` + systemd / Programador de tareas | Ciclo, respaldo, diagnóstico, usuarios | `app/cli.py`, `app/ciclo.py`, `deploy/` |

Sin API de IA (`AI_MODE=none`).

## 3. Procesos

| Proceso | Qué lo lanza | Qué hace | Estado |
|---|---|---|---|
| Panel | `sicop-web.service` (uvicorn, **un solo worker**, 127.0.0.1:8000 detrás del proxy HTTPS) | Atiende el navegador | En el servidor desde el 15/10 (versión vieja, `02b569b`) |
| Migración | `sicop-migrate.service` (una vez, antes del panel) | `migrate` | En el servidor |
| Ciclo diario | `sicop-cycle.timer` → `sicop-cycle.service`; en Windows, la tarea de `deploy/windows/sicop-ciclo.ps1` | `run-cycle --origen real` | Servidor: **timer no activado** (lección 10). Windows: dry-run |
| Obtención automática | Tarea de `deploy/windows/sicop-obtencion.ps1`, cada 15 min | `obtain auto`: pide, sondea, valida, corre el ciclo | **No activada** (`SOURCE_MODE=manual`) |

Un solo proceso web es lo correcto con SQLite en el piloto: el límite de intentos de login vive en su memoria
(`app/web/intentos.py`). Ciclo, sondeo y obtención usan **bloqueos de archivo** del sistema operativo
(`app/bloqueo.py`): dos ciclos a la vez no pueden pasar, y si un proceso se cae, el bloqueo se suelta solo.

## 4. Recorrido de un dato

1. **Llega** el ZIP «Detalle pliego de condiciones» a `INCOMING_DIR`. El ciclo espera 60 s desde la última
   modificación (podría estar copiándose) e ignora `.part`, `.crdownload` y similares.
2. **Se reconoce** por su contenido, no por el nombre (`app/ciclo.py`: encabezados, o los nombres dentro del ZIP).
   Un archivo cortado, ilegible o desconocido va a `con_error/`; nunca se lee como «cero oportunidades».
3. **Se importa** (`app/importers/comun.py`):
   - La huella SHA-256 del archivo: si ya se importó, no se repite.
   - El original se copia a `RAW_DATA_DIR`; cada fila aceptada queda tal cual en `raw_snapshots`.
   - Cada fila se valida; las malas se rechazan con línea y motivo, sin detener el resto.
   - Todo en una transacción: o entra el archivo completo o nada.
   - Orden: instituciones → carteles → catálogo → líneas → adjudicaciones. Una línea cuyo cartel aún no
     existe espera en `raw_snapshots` y entra sola cuando llega el cartel.
4. **Se evalúa** (`app/matching/`): cada cartel contra cada familia del YAML, con el título y el nombre de
   catálogo de sus líneas. Resultado en `opportunity_assessments`: encaje, plazo, calidad de datos, regla y
   evidencia, con la **versión de reglas** (huella del YAML). Una evaluación completa queda en `evaluation_runs`.
5. **Se muestra** en el panel: la versión vigente es la de la última evaluación completa. Una persona revisa y
   decide; cada decisión es una fila nueva de `reviews`.
6. **Se avisa** (`app/avisos.py`): carteles Alta o Media con plazo abierto y vistos en los últimos
   `NOTIFY_LOOKBACK_DAYS` días, más los marcados «Interesa» o «Revisar requisitos» que cierran pronto. Cada aviso
   es una fila de `notification_outbox` con una clave única (destinatario | cartel | versión | motivo). Un correo
   resumen por destinatario; los lunes, además, el resumen semanal (`app/resumen.py`).
7. **Se registra**: cada ciclo en `source_runs` (archivos vistos, qué pasó con cada uno, avisos).

## 5. Módulos

```text
app/
  main.py            crea la app web: sesión, middlewares, /health
  cli.py             todos los comandos (python -m app.cli --help)
  config.py          variables: entorno > .env > valores por defecto
  database.py        conexión, transacciones, migraciones
  ciclo.py           run-cycle;  bloqueo.py  bloqueo de archivo entre procesos
  panel.py           consultas del panel (lista, detalle, revisión), sin HTML
  compras.py         un cartel con su comprador y sus líneas
  avisos.py · resumen.py · reintentos.py · destinatarios.py   avisos por correo
  competencia.py     quién gana qué (adjudicaciones)
  calidad.py         precisión y cobertura de las reglas por familia (score-rules, página «Calidad de reglas»)
  seguimiento.py     gestor de documentos: carteles en seguimiento y su encargado (página «Seguimiento»)
  exportar.py        listado a Excel (identificadores como texto)
  usuarios.py · historial.py   usuarios (Argon2) y auditoría de cambios de administración
  respaldo.py        respaldo consistente con manifiesto
  dinero.py          Monto = Decimal + moneda; nunca se suman monedas distintas
  importers/         comun.py (lo compartido) · carteles · lineas · catalogo · instituciones ·
                     adjudicaciones · zip_pliegos · csv_reader
  matching/          reglas.py (YAML, normalizar, buscar) · evaluar.py (encaje, plazo, calidad)
  notifications/     gmail.py (envío por la API de Gmail)
  sources/           obtencion.py · automatico.py · sicop_browser.py (Playwright) · gmail_reader.py
  web/               rutas.py · seguridad.py (sesión, CSRF, niveles) · intentos.py · carga.py ·
                     templates/ · static/
```

## 6. Modelo de datos

| Grupo | Tablas | Nota |
|---|---|---|
| Procedencia | `source_runs`, `imports`, `raw_snapshots` | Cada fila importada se rastrea hasta su archivo y su ciclo |
| Datos de SICOP | `tenders`, `tender_lines`, `catalog_items`, `institutions`, vista `v_tender_lines` | Clave natural: Número SICOP (texto) |
| Adjudicaciones | `adjudicaciones`, `adjudicacion_proveedores`, `adjudicacion_lineas` | El ganador viene solo como cédula |
| Evaluación | `opportunity_assessments`, `evaluation_runs` | Una fila por cartel × familia × versión de reglas |
| Calidad de reglas | `rule_score_runs`, `rule_scores` | Cada medición de `score-rules`, por familia; no se borra (trigger) |
| Revisión | `reviews` | Solo se agrega: triggers impiden borrar o modificar |
| Seguimiento | `seguimientos`, `seguimiento_asignaciones` | Un seguimiento por cartel; el encargado vigente es la última asignación; no se borran ni se modifican (triggers) |
| Avisos | `notification_recipients`, `notification_outbox` | La outbox no se borra (trigger) |
| Obtención | `solicitudes_sicop` | Máquina de estados de cada solicitud automática |
| Acceso | `users`, `audit_log` | `audit_log` no se borra ni se modifica (triggers); un usuario no se borra: «Eliminar» es una baja definitiva (`eliminado_en`, 0016) |
| Esquema | `schema_migrations` | Versión y huella de cada migración aplicada |

## 7. Decisiones de diseño

| Decisión | Por qué |
|---|---|
| Identificadores SICOP siempre como texto | Tienen 8, 16 o 24 dígitos con ceros iniciales; como número se pierden (y Excel los daña) |
| Dinero en `Decimal` con su moneda | Sin errores de redondeo; nunca se suman CRC y USD |
| Hora de Costa Rica fija (UTC−6) | SICOP la usa y Costa Rica no tiene horario de verano; no depende de `tzdata` en Windows |
| Importación y avisos idempotentes | Repetir un archivo o un ciclo nunca duplica datos ni correos (hash del archivo, clave única de la outbox) |
| Nunca borrar revisiones ni avisos | Un cartel que se reimporta conserva su historia; los triggers lo hacen cumplir en la base |
| Reglas en YAML, versión = huella | Se cambian sin tocar código, y cada evaluación dice con qué reglas se hizo |
| Datos reales, sintéticos y simulados separados | `data_origin` en cada importación; las pruebas nunca usan `data/` |
| Sin datos del día, no se avisa | Un correo vacío daría a entender que no hubo compras; el ciclo queda en «fallo» a propósito |
| Envío solo con dos llaves | `NOTIFICATIONS_ENABLED=true` y `NOTIFICATIONS_DRY_RUN=false`; por defecto, vista previa |
| Fallido o incierto nunca se reenvía solo | Una persona decide en «Avisos» (quizá sí salió) |
| Sin programador dentro del proceso web | Ver la sección 1 |

## 8. Seguridad

- **Sesión** firmada (`SessionMiddleware`, `SESSION_SECRET` obligatorio fuera de development), cookie `Secure`
  en producción, `SameSite=Lax`, vencimiento de `SESSION_MAX_AGE_HOURS`. En cada petición se comprueba en la base
  que el usuario siga activo y no haya cambiado su contraseña.
- **CSRF**: token por sesión en cada formulario POST.
- **Contraseñas** con Argon2id; mínimo 10 caracteres. **Límite de intentos**: 5 fallos en 15 min por correo + IP.
- **Niveles**: encargado (ver, revisar, cargar) y administrador (además usuarios, destinatarios y avisos).
- Sin `/docs` ni `/openapi.json`; `/health` no muestra rutas, usuarios ni secretos; `Cache-Control: no-store`.
- Subidas: tamaño máximo, extensión permitida y nombre limpiado; se guardan en una carpeta que decide la app.
- Secretos fuera de Git: `.env` local, `/etc/sicop-connect/app.env` en el servidor; los JSON de Google fuera del
  proyecto.

## 9. Despliegue

```text
 WINDOWS (Ivania)              GITHUB (privado)       MAC (Oscar)                 SERVIDOR (Ubuntu, Hostinger)
 desarrolla y prueba  ─push─▶  ramas + PR      ─▶   git archive + sha256  ─scp─▶  /opt/sicop-connect   (código)
                                                                                  /var/lib/sicop-connect (datos)
                                                                                  /etc/sicop-connect   (secretos)
```

El servidor solo instala y ejecuta, con el usuario `sicop` sin privilegios. Código y datos van separados: el
código se reemplaza en cada versión y los datos se respaldan aparte. Pasos: `docs/DESPLIEGUE.md`, sección 9.

## 10. Pendiente de verificar

Esto no se puede comprobar desde Windows; queda para la actualización del servidor (lección 15):

- Que el servidor tenga instalada la versión de `desarrollo` (hoy tiene `02b569b`) con las migraciones hasta la 0016.
- Que el proxy HTTPS de Hostinger pase la IP real del visitante (`--proxy-headers`; comprobado el 19/10 con la
  versión vieja).
- El timer del ciclo y la obtención automática, cuando se activen.
