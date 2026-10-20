# Estado de SICOP CONNECT

Última actualización: 2026-10-19 · Día / tarea: **lección 9 cerrada**; siguiente, lección 10 (por calendario, lección 11) · Commit probado: `162afe8` (`main` de GitHub, 348 passed)

## Último resultado

- **Lección 9 cerrada (2026-10-19).** Por calendario toca la lección 11: vamos 2 lecciones atrás.
  - Cierre: autoevaluación ☑, `health` ☑, HTTPS con login ☑, oportunidad real revisada en el servidor desde otra
    computadora ☑ (Corredores y otras 4), acta cerrada (`docs/ACTA_DESPLIEGUE.md`) y bitácora. Hash del paquete:
    no se comparó; se hace en la próxima actualización. Sin registro: salida del `evaluate` del servidor y reporte
    de la herramienta que instaló los archivos de Google.
  - Oscar unió los PR #1 y #2: `main` de GitHub = `162afe8` (LF + página «Avisos»). El servidor sigue en `02b569b`.
  - Servidor (camino B): tenía carteles sin evaluar; Oscar corrió `evaluate` y el panel muestra las oportunidades.
    Archivos de Google instalados por la herramienta de Oscar; avisos en dry-run (confirmado por Oscar).
  - Respuestas de Oscar: LF; trabajar por ramas (nada directo a `main`); revisa si el repositorio quedó público;
    los respaldos del servidor los hace él; aprueba el ciclo diario (primero dry-run). No entendió la pregunta de
    los JSON de Google: se le explicó de nuevo.
  - Fin de línea LF en la rama `fin-de-linea-lf` (ver Pendientes). 337 passed.
  - Primer push a GitHub (Ivania lo pidió), después de un `fetch`: Oscar no había subido nada nuevo.
    `reintento-avisos` se copió sobre la rama LF como `reintento-avisos-lf` (mismo commit, sin conflictos de fin
    de línea); 348 passed.
  - Pull requests creados por Ivania en la web (`gh` no está instalado): **#1** `main` ← `fin-de-linea-lf` y **#2**
    `fin-de-linea-lf` ← `reintento-avisos-lf` (apilado: unir primero el #1). Esperan la revisión de Oscar.
  - `docs/ACTA_DESPLIEGUE.md` (borrador): instalación el jueves 15/10 desde las 15:00, Ivania y Oscar presentes,
    paquete `git archive` desde la Mac, HTTPS con las herramientas de Hostinger. El servidor es compartido con
    Nexus y otras apps de la empresa. Sin registro: commit instalado, hash del paquete, `health`, servicio y
    usuario `sicop`. Oscar tiene los comandos para completarlo.
  - Panel en el servidor (2026-10-19, Ivania desde el celular): el inicio de sesión funciona, pero dice «Todavía no
    hay evaluaciones». Ese mensaje solo sale con la tabla de evaluaciones vacía, así que la base del servidor **no
    parece ser el respaldo de Windows** acordado el 13/10. Se le plantearon a Oscar dos caminos: A, restaurar el
    respaldo de Windows (recomendado: conserva revisiones, usuarios, destinatarios y avisos enviados); B, importar
    archivos reales en el servidor y evaluar. Se le pidió `list-users` para decidir.
  - Corrección (Ivania, 2026-10-19): Oscar no ejecutó comandos; un asistente de IA hizo la instalación y subió el
    código **del servidor a GitHub** (por eso la historia nueva con CRLF). Revisado: en GitHub no hay secretos.
    Pendiente: el historial de esa sesión y quitar del servidor el permiso para escribir en GitHub si no se usa.
  - **Datos al día (2026-10-19, Ivania, panel local):** importaciones #12 (10 714 carteles, 614 nuevos, publicados
    hasta el 19/10 10:34) y #13 (77 434 líneas), 0 rechazos; `evaluate` (reglas `92aef8277e2e`): 19 filas nuevas.
    Abiertos sin revisar: Corredores GPS (`20261001497`, cierra mié 21/10 10:00, llegó el 13/10 y nadie lo vio),
    Puriscal bodycams (`20261002246`, mié 21/10 15:00), OIJ cámara para vehículo (`20260903798`, jue 22/10).
    Falso positivo: CCSS «Cámaras intraorales…» (`20261001749`, Media por «cámaras» + «transporte»). Ivania avisó a
    Oscar y Anabelle a mano. **Decisiones (Oscar y Anabelle, 2026-10-19):** Corredores no (vista la descripción,
    no es para la empresa) · Puriscal sí interesa · OIJ interesa, pero se descartó. Las tres Alta: la prioridad
    mide encaje con el portafolio, no si conviene participar. Respaldo `sicop_20261019-114809` (huella `1e461b55…`): reemplaza al del 16/10 para
    el camino A.
  - **`OPERACION.md` probado paso a paso, secciones 1–6 (2026-10-19, Windows):** 13 hallazgos, corregidos en el
    manual (ZIP del reporte, `INCOMING_DIR` en Windows, ciclo sin archivo = FALLO código 1, la revisión no saca un
    cartel de los avisos, restauración en Windows, respaldos en el mismo disco…). Simulacros #3 y #4 hechos en
    Windows. `run-cycle --dry-run` (#22) y `notify --dry-run`: el aviso habría traído las mismas 3 oportunidades
    que Ivania mandó a mano; 12 avisos quedan «preparado» en la base local.
  - **Autoevaluación de la lección 9 (2026-10-19, Ivania): las tres correctas.**
    - Mac / servidor: Windows desarrolla y prueba, la Mac empaqueta y transfiere lo revisado, el servidor solo
      instala y ejecuta; responsables claros, lo revisado llega igual y las credenciales quedan protegidas.
      Se agregó: el hash es lo que comprueba que llegó igual.
    - Sin `root`: un fallo como `root` pone en riesgo todo el servidor; como `sicop`, solo la app.
    - Código y datos aparte: el código se reemplaza y se puede reconstruir; los datos son únicos. Permite
      actualizar, respaldar y proteger cada uno sin arriesgar el otro.

- **Lección 9, GitHub (2026-10-16).**
  - Repositorio privado `git@github.com:oscar041988/sicop-Connect.git` (dueño: Oscar). Ivania entra con su
    cuenta `licitaciones-byte` y una llave SSH con frase (agente SSH de Windows; `core.sshCommand` en este
    repositorio apunta al ssh de Windows porque el de Git no ve ese agente).
  - Lo que subió Oscar: historia nueva. `3b2f0b2` = mismo contenido que `cc4da46`, pero con fin de línea CRLF;
    luego `7ded3f1` (paleta Fenova y logo de Hermatix) y `02b569b` (mostrar/ocultar contraseña en el login).
    La rama `diseno-fenova` tiene solo el primero.
  - Local: la historia anterior queda en la rama `historial-local` (`cc4da46`); se trabaja en `main`, que sigue
    a `origin/main`. 337 passed en `02b569b`; golden set 33/33.
  - Servidor (confirmado por Ivania, 2026-10-16): la app está instalada y funciona desde su enlace, con HTTPS.

- **Lección 8, encargo B (2026-10-13): preparación del despliegue.** 337 passed (15 nuevas en
  `tests/test_respaldo.py` y `tests/test_despliegue.py`).
  - `python -m app.cli backup --output CARPETA`:
    - copia con la API de backup de SQLite, consistente aunque alguien esté escribiendo;
    - manifiesto `.json` con fecha, commit, versión del esquema, SHA-256, `integrity_check` y filas por tabla;
    - nunca sobrescribe y no acepta la carpeta de la base.
    - `app/COMMIT` + `.gitattributes` (export-subst): el paquete de `git archive` lleva el commit.
  - `requirements.lock.txt`: un entorno limpio dio exactamente la misma lista (sin pytest ni httpx) y con ella
    pasaron 328 pruebas. Solo cambió el encabezado.
  - `deploy/systemd/` (LF, forzado en `.gitattributes`):
    - `sicop-web.service`, `sicop-migrate.service`;
    - `sicop-cycle.service` (`run-cycle --origen real --dry-run`);
    - `sicop-cycle.timer`: de lunes a viernes a las 08:00 America/Costa_Rica, `Persistent=false` (decisión de Oscar;
      la guía decía todos los días a las 07:00).
  - `docs/DESPLIEGUE.md`, sección 9:
    - pasos 🪟 Windows / 🍎 Mac / 🐧 servidor, con MARCADORES;
    - `app.env` con `EXPORTS_DIR`, `APP_BASE_URL` y las rutas de Google;
    - activación del ciclo en el orden de 17.5; respaldo, restauración, actualizar y revertir.
  - **Decisiones para Oscar:**
    - base inicial en el servidor: vacía o el respaldo de Windows;
    - cómo pasar los JSON de Google al servidor;
    - destino y retención de los respaldos (D8) y si hay respaldo diario automático.
  - Paso 4, probado a mano (2026-10-13, Ivania):
    - ☑ Instalación limpia: paquete `git archive` de `5b3eff9` descomprimido en
      `C:\Users\User\prueba-instalacion` (112 archivos, `app/COMMIT` correcto), entorno nuevo,
      `pip install -r requirements.lock.txt` sin errores, `migrate` → 0007, `/health` ok en el puerto 8001.
    - ☑ Respaldo restaurado y legible: `backup` → `sicop_20261013-151951.db` (commit `5b3eff9`, esquema 0007,
      integridad ok); `Get-FileHash` igual al SHA-256 del manifiesto (`f32a3168…`); copiado como base de
      `prueba-instalacion`, donde aparece la revisión #5 (`20261000674`, interesa, Ivania Reyes).
      El respaldo queda en `C:\Users\User\respaldos-sicop\`, fuera de git.
  - Autoevaluaciones hechas (2026-10-13, Ivania):
    - **Lección 7:** dedup_key UNIQUE + estado; aceptado ≠ recibido; incierto no se reenvía para no duplicar.
      Las tres correctas.
    - **Lección 8:**
      - fallo ≠ «cero oportunidades»: correcta;
      - sin bloqueo: se precisó que el riesgo principal es el correo duplicado, no el archivo (la huella lo evita);
      - copiar el `.db` mientras se escribe puede dejar una copia dañada: correcta al segundo intento.
  - Paso 5 (2026-10-13, Ivania con Oscar): mañana se sube al servidor.
    - Base inicial: la de Windows, con un respaldo nuevo antes de subir.
    - GitHub privado y Python ≥ 3.12: resueltos, según Oscar.
    - Siguen abiertos (sección 7 de `DESPLIEGUE.md`): usuario SSH, HTTPS y dominio, cómo pasar los JSON de
      Google, y destino y retención de los respaldos.
  - **Lección 8 cerrada.** Siguiente: lección 9, instalar en el servidor (`DESPLIEGUE.md`, sección 9).

- **Lección 8, encargo A (2026-10-13): `run-cycle` = recoger → importar → evaluar → avisar.** 321 passed
  (17 nuevas en `tests/test_ciclo.py`; datos SINTÉTICOS, proveedor SIMULADO).
  - `python -m app.cli run-cycle --origen real [--dry-run | --send]`: dry-run por defecto; `--send` exige lo mismo
    que `notify --send`. Salida: 0 = ok · 1 = fallo (registrado) · 2 = otro ciclo en curso.
  - Bloqueo del sistema operativo en `run-cycle.lock`, junto a la base (`app/bloqueo.py`): el segundo ciclo sale
    con «ya hay un ciclo en curso (empezó…, proceso…)»; si un proceso muere, el bloqueo se suelta solo.
  - Migración 0007: `source_runs.kind` ('import' | 'ciclo') y `coverage` (JSON: cada archivo y su resultado,
    evaluación, avisos). Las importaciones del ciclo apuntan a su fila. Un ciclo que quedó «en_curso» pasa a fallo.
  - El tipo de reporte se reconoce por el encabezado. Archivo vacío, cortado (sin salto de línea final o última
    fila con columnas de menos), ZIP dañado o no reconocido → ERROR, se aparta en `con_error/<fecha>/`, ciclo «fallo».
  - Si la fuente falla o no llega nada nuevo: se evalúa, pero **no se avisa** (no es «cero oportunidades»).
  - Importados y repetidos → `procesados/<fecha>/`. Se dejan para el próximo ciclo los temporales
    (`.crdownload`, `.part`…) y los modificados hace menos de 60 s.
  - Probado a mano (2026-10-13, Ivania): `migrate` aplicó la 0007 en `data/sicop.db`.
    - ☑ Ciclo completo con archivo real en dry-run, ciclo #13 OK: carteles importados (10 806 filas, publicados
      del 13/07 al 13/10), 9 evaluaciones nuevas, 3 avisos preparados (no enviados). El #12 dejó el archivo
      «en espera» (se corrió antes de 60 s); por eso se aclaró el mensaje (commit `8b1a8ae`).
    - Paso 2, los 4 fallos provocados, con el mensaje que quedó en `source_runs`:
      - ☑ Carpeta vacía (#14): «no llegó ningún archivo nuevo…».
      - ☑ Archivo cortado a 50 000 bytes (#15): ERROR «incompleto: termina a mitad de una fila», apartado
        en `con_error/`.
      - ☑ Archivo repetido con otro nombre (#16): «YA IMPORTADO … igual a la importación #11».
      - ☑ Dos ciclos a la vez (#17): «otro ciclo en curso (prueba de Ivania, terminal 1): no se hizo nada».
        Al soltarse el bloqueo, el #18 corrió normal.
      - Ninguno avisó.

- **Lección 7, encargo B (2026-10-13): envío por la API de Gmail.** Pruebas con pytest (proveedor y Google
  SIMULADOS) y primer envío real (ver abajo). 304 passed (antes 277; nuevas en `tests/test_avisos.py` y
  `tests/test_gmail.py`).
  - Acceso: OAuth de licitaciones@ con permiso `gmail.send` (más `openid`/`email`, solo para comprobar la cuenta).
    Cliente creado por Oscar; pasos en `docs/GOOGLE_API.md`. `python -m app.cli google-auth` hace la
    autorización única y se niega si la cuenta no es `MAIL_FROM`. Token en `GOOGLE_TOKEN_FILE`, fuera del proyecto.
  - `notify --send [--solo CORREO]`: exige `NOTIFICATIONS_ENABLED=true`, `NOTIFICATIONS_DRY_RUN=false`,
    `MAIL_PROVIDER=gmail_api`, `MAIL_FROM` y token válido; si falta algo, no toca la outbox. Un correo por
    destinatario; sus avisos pasan a «incierto» **antes** de llamar a Gmail y luego a «aceptado» (con el id de
    Gmail) o «fallido». 4xx → fallido; 5xx, timeout o sin id → incierto. Nada fallido o incierto se reenvía solo.
  - Los avisos con cierre vencido ya no se envían ni salen en la vista previa (quedan «preparado»). Si un cartel
    cambió dos veces antes de enviarse, va una sola vez.
  - Dependencias nuevas: `google-auth`, `google-auth-oauthlib`. `requirements.lock.txt` regenerado (incluye
    starlette 1.8.0, que exige Python 3.11+); `.venv` igualado al lock.
  - Probado a mano (2026-10-13, Ivania): `.env` con `MAIL_PROVIDER=gmail_api` y las rutas de Google;
    `google-auth` como licitaciones@ → «Autorizado»; `doctor` → cliente y token existen. Sin envío.
  - **Prueba real (paso 4 de la guía, 2026-10-13, Ivania con autorización de Oscar):** `notify --send`.
    (a) Gmail respondió «aceptado»: la outbox tiene 9 avisos aceptados, 3 destinatarios y 3 carteles, con 3 ids
    de Gmail, enviados entre 13:19 y 13:55. (b) Llegó a la bandeja de entrada unos 2 minutos después, con
    «Hola, equipo». (c) No cayó en «no deseado». Al repetir el comando no se reenvió nada.
    Los enlaces del correo apuntan a `127.0.0.1` hasta que el panel esté en el servidor (lección 9).

- **Contraseñas: mínimo 10 caracteres (antes 12), 2026-10-12, decisión de Ivania** (a la empresa le parecía tedioso
  12). A cambio, el panel y la terminal sugieren una frase de 3 o 4 palabras («cafe verde lunes»). Las contraseñas
  existentes siguen sirviendo. 276 passed. Probado a mano (2026-10-12, Ivania): 9 caracteres rechazados con el
  consejo, una frase de 3 palabras aceptada.

- **Lección 7, encargo A (2026-10-12): `notify --dry-run` y outbox.** Probado con pytest (datos sintéticos)
  y a mano con datos reales (2026-10-12, Ivania): `migrate` aplicó la 0006, destinatarios agregados en el panel,
  dos dry-run (el segundo sin avisos nuevos) y vista previa revisada.
  **Paso 2 hecho (2026-10-13): Oscar vio la vista previa y está de acuerdo.** Pidió un solo correo al día, que
  llegue todos los días a las 8:00 (hora de Costa Rica). El código ya junta todo en un resumen por destinatario
  en cada ejecución; falta programar una ejecución diaria a las 8:00 (temporizador de systemd en el servidor,
  lección 9, solo con instrucción explícita). También pidió (2026-10-13): saludo «Hola, equipo» en vez del nombre
  de la persona (hecho), y que no llegue nada los días sin oportunidades nuevas (ya era así; ahora con prueba).
  277 passed. Probado a mano (2026-10-13, Ivania): dry-run con datos reales, la vista previa dice «Hola, equipo».
  **Decisión de Oscar (2026-10-13): solo de lunes a viernes.** El lunes llega lo acumulado desde el viernes (se
  junta en el mismo resumen; los de plazo vencido no se incluyen). Horario en `docs/DESPLIEGUE.md`, nota 4.
  - Destinatarios en el panel (`/destinatarios`, solo administradores, con historial); `MAIL_TO` ya no se usa.
  - Selección: prioridad Alta/Media de la última evaluación, plazo no vencido, versión del cartel vista en los
    últimos `NOTIFY_LOOKBACK_DAYS` (7) días. Motivo por destinatario: nueva · cambio_plazo · nueva_version.
  - Migración `0006`: `notification_recipients` y `notification_outbox` reconstruida (preparado · aceptado ·
    fallido · incierto; `dedup_key` = destinatario|Número SICOP|versión|motivo, UNIQUE; no se borra).
  - Vista previa HTML y texto por destinatario en `EXPORTS_DIR/avisos_<fecha>/`, con enlace a `APP_BASE_URL`.
  - Dry-run nunca llama al proveedor ni pasa de «preparado»; sin `--dry-run`, el comando se niega (encargo B).
  - `python -m pytest -q` → 274 passed (19 nuevas en `tests/test_avisos.py`).

- **Lección 6, encargo B (2026-10-12): carga de archivos desde el panel** (`/cargar`, con sesión y CSRF).
  Probado con pytest (datos sintéticos) y con un CSV real de carteles (2026-10-12, Ivania): lo reconoció como la
  importación #7 y no cambió nada. El aviso dice qué era la importación anterior (reporte, fecha y nombre).
  - Se elige reporte (carteles, lineas, catalogo, instituciones) y origen (real, sintetico, simulado); se guarda en
    `INCOMING_DIR` con nombre seguro (`AAAAMMDD-HHMMSS-xxxxxx_Nombre_limpio.csv`) y se importa con el mismo
    importador de la CLI. Resumen en la página: leídas, aceptadas, rechazadas con línea y motivo, advertencias.
  - Límite `UPLOAD_MAX_MB` (25 MB): se rechaza antes de recibir si la petición declara más, y al copiar si no.
    Extensión `.csv`; `.zip` solo para el catálogo. Si no se importa o ya estaba importado, el archivo no queda
    en la carpeta de entrada.
  - Sin Post/Redirect/Get: el detalle de rechazos no se guarda; recargar no duplica porque el hash lo reconoce.
  - `python -m pytest -q` → 217 passed (30 nuevas en `tests/test_carga.py`).
- **Lección 6, encargo A (2026-10-12): panel protegido.** Probado con pytest (datos sintéticos) y a mano (2026-10-12, Ivania): ventana privada → login; URL directa de un
    detalle → login y vuelta al detalle; contraseña o correo incorrectos → mismo mensaje; cerrar sesión + «atrás» → sin
    datos; `/health` público; `/docs` → login. Usuario real creado con `create-user`.
  - Sin sesión, todo redirige a `/login` (menos `/health` y `/static`). `/docs` y `/openapi.json` desactivados.
  - Usuarios en la tabla `users` (ya existía desde `0001`): hash Argon2id con `argon2-cffi`; el rol queda en `admin`
    y no se usa. `python -m app.cli create-user` pide la contraseña con `getpass` (mín. 12 caracteres, se repite).
  - Sesión: cookie `sicop_sesion` firmada con `SESSION_SECRET` (SessionMiddleware de Starlette + `itsdangerous`),
    HttpOnly, SameSite=Lax, Secure fuera de `development`, vence a las `SESSION_MAX_AGE_HOURS` (8 h). Fuera de
    `development` la app no arranca sin un `SESSION_SECRET` de 32+ caracteres; en desarrollo usa uno temporal.
  - CSRF: token por sesión en un campo oculto de todo formulario POST (login, logout, revisión); sin él → 403.
  - Páginas protegidas con `Cache-Control: no-store`. Login con el mismo mensaje si falla el correo o la contraseña.
  - `python -m pytest -q` → 183 passed (39 nuevas en `tests/test_acceso.py`). Dependencias nuevas: `argon2-cffi`, `itsdangerous`.
- Qué funciona (verificado): `python -m uvicorn app.main:app --reload` → http://127.0.0.1:8000.
  - Diseño del prototipo de Hermatix (`index-comentado.html`): encabezado blanco con la marca, paleta verde,
    chips por estado de la revisión (Todos, Sin revisar, Interesa, No interesa, Revisar requisitos), buscador
    (institución, objeto o Número SICOP) y «Más filtros» (prioridad, familia, institución, plazo, tipo).
  - Lista en tarjetas (25 por página), por defecto solo candidatos (Alta y Media), ordenados por cierre más
    próximo: etiquetas «Nuevo» (llegó en la última importación), familia, cuenta regresiva y revisión; título e
    institución; prioridad a la derecha (no hay % de coincidencia); monto estimado por moneda, cierre y
    modalidad; «Ver toda la información» con regla y palabras clave detectadas. Sin botones de clasificación.
  - Al mostrar: espacios duros (NBSP) de SICOP como espacios normales y títulos en MAYÚSCULAS con mayúscula
    inicial (conserva siglas, códigos y números romanos). El texto guardado no cambia.
  - Plazo calculado al mostrar. Aviso si el YAML cambió y falta ejecutar `evaluate`.
  - Detalle: ficha con cuenta regresiva, evidencia resaltada en título y líneas, regla, comprador, procedimiento,
    líneas con catálogo, estimado por moneda, cobertura de la fuente; Número SICOP para buscarlo en el portal.
  - Revisión: Interesa / No interesa (motivo obligatorio) / Revisar requisitos, comentario y responsable;
    historial. No se borra ni se modifica (triggers); se conserva al reimportar.
  - Migración `0004`: `tenders.tipo_procedimiento` y `reviews` reconstruida. Dependencias: `jinja2`, `python-multipart`.
- Comandos ejecutados y resultado:
  - `python -m pytest -q` → 144 passed (1 aviso de deprecación de httpx en Starlette, no bloquea).
  - Datos nuevos 2026-10-13 (Ivania): importaciones #9 (10 678 carteles desde el panel, 288 nuevos) y #10
    (77 764 líneas), 0 rechazos. `evaluate` (reglas `92aef8277e2e`) después de las líneas: 1 Alta nueva y abierta,
    Santa Ana, body cams (`20261001587`, cierra 23/10 23:59), revisada «Interesa» (revisión #4, Ivania);
    9 Baja y 1 sin coincidencia. 15 de los 288 aún sin líneas (entran con la próxima descarga de líneas).
    Recordatorio: si `python` no se encuentra, falta activar `.venv` (`.\.venv\Scripts\Activate.ps1`).
  - Datos nuevos 2026-10-09 (ZIP de las 13:49; ver `ACCESO_SICOP.md`): importaciones #7 (10 587 carteles: 460
    nuevos, 119 actualizados) y #8 (74 824 líneas), 0 rechazos. `evaluate` (reglas `92aef8277e2e`): 18 Alta y
    6 Media; 3 candidatos abiertos: Turrialba (`20261000870`), Cervantes (`20261000990`), CCDR Santa Cruz (`20261000674`).
  - **Reimportación comprobada con datos reales:** la revisión #1 de Ivania (`20260802051`, «Interesa») sigue tras
    la importación #7, que volvió a pasar por ese cartel.
- Oscar vio el panel (2026-10-09). Turrialba (cierra el lunes 12/10 10:00): no da tiempo de preparar una propuesta,
  porque los fines de semana no se trabaja.
- Lección 4 (motor de reglas): golden set **29/29 = 100 %** midiendo título y líneas. Ver `docs/REGLAS.md`.
- Evidencia: datos **reales** en `data/sicop.db`; pruebas del panel con datos sintéticos en base temporal.
- Concepto que puedo explicar: Post/Redirect/Get y por qué la revisión va ligada al Número SICOP.

## Estado de integraciones

- Obtención: manual verificada en el portal (2026-10-06, 2026-10-07 y 2026-10-08; ver `docs/ACCESO_SICOP.md`)
- Correo: sin configurar. Decidido con Oscar (2026-10-12): API de Google, desde licitaciones@hermatix.com
- Servidor: local. Destino: VPS Ubuntu 24.04 en Hostinger, https://sicop.hermatix.com (ver `docs/DESPLIEGUE.md`).
  Código en GitHub (privado, de Oscar) desde 2026-10-16; app instalada en el VPS y funcionando con HTTPS (Ivania, 2026-10-16).

## Pendientes

- ~~Fin de línea CRLF vs LF~~ **Decidido 2026-10-19 (Oscar): LF**, normalizado con `.gitattributes`. **Hecho en la
  rama `fin-de-linea-lf` (2026-10-19), en el PR #1:** todo el texto en LF; excepción `*.csv -text` (byte por byte,
  con el CRLF de SICOP: 3 pruebas dependían de él y en Linux habrían fallado). 337 passed.
- ~~Forma de trabajo con GitHub~~ **Decidido 2026-10-19 (Oscar): por ramas** (Ivania sube ramas; nada directo a
  `main`). PR #1 y #2 **unidos por Oscar el 2026-10-19** (`main` = `162afe8`). Ramas `reintento-avisos`,
  `fin-de-linea-lf` y `reintento-avisos-lf` borradas (Ivania lo pidió, 2026-10-19).
- ~~Cerrar la lección 9~~ **Cerrada 2026-10-19.** Queda del acta:
  borrar los JSON de Google de la USB y la Mac, quién cargó archivos en el servidor el 16/10 y el 19/10, el
  historial del asistente, y actualizar el servidor a `main` comparando el hash (9.8) · Oscar.
- **Siguiente: lección 10** (ciclo de las 8:00 y envío real) · Ivania con Oscar, en orden: confirmar
  destinatarios → `run-cycle --dry-run` en el servidor → envío supervisado con `notify --send --solo` → activar
  `sicop-cycle.timer` → comprobar que sobrevive a un reinicio. Decidir quién deja los archivos de SICOP antes de
  las 8:00 (sin archivo, el ciclo sale en «fallo»).
- Salieron de la prueba de `OPERACION.md` (2026-10-19), cada uno es un cambio aparte y no se hace sin pedirlo:
  - Regla de «cámaras»: que no cuente con «intraorales» o equipo médico (falso positivo CCSS `20261001749`);
    agregarlo al golden set · Ivania / Claude.
  - El panel no avisa de carteles nuevos sin evaluar · Claude (mejora pequeña).
  - `doctor` marca `MAIL_TO` como pendiente aunque ya no se usa · Claude (arreglo pequeño).
  - Destinatarios activos: `aumana@`, `calvarez@`, `priaraya@`. En la lección 7 Oscar pidió al inicio Anabelle y
    él: confirmar que son los correctos · Ivania con Oscar.
  - Copiar el respaldo más reciente a una memoria USB (hoy está en el mismo disco que la base) · Ivania.
- Servidor compartido con Nexus y otras apps: puerto 8000 solo de SICOP ☑ y el proxy pasa la IP real ☑
  (2026-10-19). Falta · Oscar: respaldos que incluyan la base de SICOP (con `app.cli backup`) y quitar del
  servidor el permiso para escribir en GitHub.
- Repositorio público o privado · Oscar: cree que olvidó pasarlo a privado; lo revisa (2026-10-19).
- Respaldos en el servidor (destino, retención, diario) · **Oscar los hace él** (2026-10-19).
- Ciclo diario en el servidor: **aprobado por Oscar (2026-10-19)**, primero en dry-run; el envío real después.
- **Práctica del reto de la semana 2 (2026-10-20, Ivania):**
  - Explicación: 3 correctas y 1 a medias. La segunda vez del ciclo no avisa porque el **archivo** ya se
    importó (`YA IMPORTADO` → «no llegó nada nuevo»), no por la huella de cada cartel. El selector no descarta
    lo ya avisado: lo hace `motivo_para` y, de respaldo, la clave UNIQUE.
  - Demostración: dos `notify --dry-run` → 0 nuevos · 12 ya avisados las dos veces. Fila de `20261001587` en
    `notification_outbox`: 3 destinatarios, motivo `nueva`, `aceptado` el 2026-10-13.
  - Ventana de 7 días (`NOTIFY_LOOKBACK_DAYS`): bien explicada. Se corrigió que **solo afecta los avisos**
    (`app/avisos.py`, `candidatos`); el panel no la usa y muestra los carteles abiertos sin importar la fecha
    de importación.
  - Repasar antes del reto oficial: huella del archivo vs. huella del cartel; para qué sirve la ventana de 7 días.
  - Pendiente: reto oficial en la revisión semanal con Oscar (sin Claude). Hoja de la sesión: `docs/ACTA_LECCION_10.md`.
- ~~Confirmar el estado del servidor~~ **Cerrado 2026-10-16 (Ivania):** instalada, funcionando y con HTTPS.
- ~~Golden set: 4 provisionales~~ **Cerrado 2026-10-12 (Ivania):** confirmados sin el pliego (concursos cerrados);
  medición 33/33 = 100 %, sin provisionales. 33 carteles reales (17 interesan, 6 no interesan, 10 falsos positivos conocidos), etiquetas de Oscar del 2026-10-08;
  el 2026-10-09 se agregaron 2 data loggers de laboratorio (Oscar) y se confirmó `20260800233` como «interesa»
  (regla de Hermatix: medidor con pantalla o panel interesa; sin pantalla, no).
- `tests/golden/golden_lineas.csv` es una copia de la base: regenerarlo al agregar carteles al golden set o al
  descargar catálogo nuevo (ver `tests/golden/README.md`) · Ivania / Claude.
- **Revisión ligada al usuario de la sesión (2026-10-12, opción A de Ivania):** se guarda `reviews.user_id` de la
  sesión y su nombre en `responsable`; el formulario ya no pide «Responsable» (si se anota la decisión de otra
  persona, va en el comentario). Las revisiones de antes del login se muestran «(escrito a mano)». 220 passed.
  Probado a mano (2026-10-12, Ivania): sin campo Responsable, revisión nueva a su nombre, la #1 «(escrito a mano)».
- **Límite de intentos de login (2026-10-12, opción A de Ivania):** 5 fallos en 15 min por correo + IP → bloqueo de
  15 min (429), aunque luego acierte; entrar bien pone el contador en cero. En memoria (`app/web/intentos.py`): se
  pierde al reiniciar. Cada fallo queda en el log con correo e IP, nunca la contraseña. 225 passed.
  Probado a mano (2026-10-12, Ivania): bloqueo al quinto fallo, sigue bloqueado con la contraseña correcta.
  **Al desplegar (lección 9):** detrás del proxy, uvicorn debe leer la IP real del visitante
  (`--proxy-headers --forwarded-allow-ips` con la IP del proxy); si no, todos comparten la IP del proxy.
- **Gestión de usuarios por terminal (2026-10-12, opción A de Ivania):** `set-password` (sin mostrarla),
  `deactivate-user` / `activate-user` (nunca borra: las revisiones lo siguen nombrando) y `list-users` (sin hash).
  En cada petición se revisa en la base que el usuario siga activo y con la misma contraseña (huella en la sesión):
  si no, su sesión se cierra al instante. Las sesiones de antes de este cambio piden entrar otra vez. 233 passed.
  Probado a mano (2026-10-12, Ivania): list-users, set-password cerró la sesión abierta, entró con la nueva.
  Desde el panel: aprobado por Oscar (ver «Niveles de acceso»), solo para el administrador.
- `requirements.lock.txt` generado (2026-10-12) desde un entorno limpio; 217 pruebas pasan con esas versiones.
  El `.venv` de desarrollo se igualó al lock el mismo día (FastAPI 0.143.0); 217 pruebas pasan.
  Al agregar o actualizar una dependencia, regenerarlo (ver su encabezado) · Claude.
- Inicio de recepción antes de la publicación: queda 1 caso, `20260802713` (Banco Popular), que no aparece en el
  portal aunque sí en datos abiertos. **Decisión 2026-10-09 (Ivania): no se pregunta a soporte.** Queda la advertencia.
- **Confirmado 2026-10-08:** la búsqueda del portal solo muestra carteles con la recepción abierta. Los cerrados solo están en datos abiertos.
- Reporte 10.2 (catálogo) · Ivania: el portal pide un código de clasificación de 8 dígitos por consulta y no acepta
  códigos parciales; solo se descargan los de las familias comerciales. Descargados e importados: `83111602`
  (GPS/flotas), `41112301` (IoT/frío), `45121515` (BodyCams). Pendiente: buscar por nombre los de las otras 6 familias.
- Línea huérfana (cartel no importado): queda en `raw_snapshots`; para que entre a `tender_lines` hay que importar
  un archivo de líneas nuevo después de los carteles (el mismo archivo no se reimporta). Hoy hay 0 huérfanas.
- Docs restantes de 15.3 (ARQUITECTURA) · se crea en su fase. `OPERACION.md`: borrador (2026-10-16) con
  importar, revisar, ciclo, avisos, diagnosticar y recuperar; **probado en Windows el 2026-10-19** y corregido.
  Falta: partes 🐧 en el servidor y simulacros #1, #2 y #5. `REGLAS.md` ya existe;
  `DESPLIEGUE.md` es un borrador con los datos del servidor (los pasos de instalación, en la lección 9).
- Bloqueos del despliegue (`docs/DESPLIEGUE.md`, sección 7) · Oscar · antes del mié 14/10: usuario SSH, HTTPS
  (sin proxy con certificado no se puede iniciar sesión en el servidor), GitHub privado, versión de Python y
  acceso a la API de Google (este último para el mar 13/10).
  **2026-10-16:** resueltos HTTPS, GitHub privado y Python (la app funciona en el servidor). Siguen abiertos:
  cómo pasar los JSON de Google y destino/retención de los respaldos.
  **2026-10-19:** los respaldos los hace Oscar en el servidor. Los JSON de Google siguen abiertos (Oscar no
  entendió la pregunta; se le explica de nuevo).
  **2026-10-20 (Ivania):** los JSON de Google ya están en el servidor; prueba con `notify --send` desde el
  servidor y el correo llegó. Cuenta para el Hito 2: ☑ correo real recibido desde el servidor.
- **Pedido de Oscar para la lección 7:** destinatarios de los avisos editables desde el panel, no fijos en
  `MAIL_TO` (al inicio: Anabelle y Oscar). Solo el administrador cambia la lista, con historial (`audit_log`).
- **Niveles de acceso aprobados por Oscar (2026-10-12):** 2 niveles, los que ya admite `users.role`.
  - Encargado (`encargado`): ver oportunidades, guardar revisiones y subir archivos de SICOP.
  - Administrador (`admin`): lo mismo, más cambiar los destinatarios de los avisos y gestionar usuarios, ambos
    también desde el panel.
  Administradores: Oscar, Anabelle e Ivania (decisión de Oscar). Historial de cambios: sí.
  **Construido (2026-10-12):** regla «solo administrador» (`exigir_admin`, 403 aunque se escriba la dirección);
  el nivel se lee de la base en cada petición, así que un cambio aplica en el siguiente clic. Página `/usuarios`
  (crear, nivel, activar/desactivar, contraseña nueva); nadie puede quitarse a sí mismo el acceso y siempre queda
  un administrador activo. Migración `0005`: tabla `audit_log` (no se borra ni se modifica, nunca guarda
  contraseñas); registra cambios del panel (con el nombre del administrador) y de la terminal («terminal»).
  Terminal: `create-user --rol`, `set-role`, `list-users` con nivel. 254 passed (21 nuevas en `tests/test_niveles.py`).
  Los destinatarios se hacen en la lección 7 y usarán la misma regla y el mismo historial.
  `check_database` ahora compara con la última migración del código: si falta alguna, el panel avisa «Faltan
  migraciones… ejecuta migrate» (antes daba error 500). 255 passed.
  Probado a mano (2026-10-12, Ivania): `migrate` aplicó la 0005 en `data/sicop.db`; página Usuarios, niveles e historial.


## Siguiente encargo

- **Lección 6** (2026-10-12): encargo A cerrado (pasos 1 y 2), `SESSION_SECRET` en `.env`, paso 3 hecho
  (`docs/DESPLIEGUE.md`, borrador), encargo B cerrado y autoevaluación hecha. **Lección 6 cerrada**, con las 3
  mejoras que había dejado fuera (revisión ligada al usuario, límite de intentos, gestión de usuarios).
- Lección 7: encargo A cerrado (2026-10-13, vista previa aprobada por Oscar).
- Lección 7, encargo B: prueba real hecha (2026-10-13). En `.env` se vuelven a poner
  `NOTIFICATIONS_ENABLED=false` y `NOTIFICATIONS_DRY_RUN=true`; el envío diario solo se activa en la lección 9.
- Pendiente nuevo: forma de revisar y reintentar a mano un aviso «fallido» o «incierto» (hoy solo se ve en la
  outbox y en la salida de `notify`). **Hecho (2026-10-16), rama `reintento-avisos` (`91d4b35`), sin unir a
  `main`:** página «Avisos» (solo admin). Reintentar → «preparado» (sale en el siguiente envío); un incierto pide
  la casilla «Revisé Gmail › Enviados» o se marca «Sí salió» (→ aceptado, sin reenviar). No deja reintentar si
  el cartel cerró, el destinatario fue quitado o ya le llegó una versión más nueva. Cada decisión va a
  `audit_log` con el estado y el detalle de antes. 348 passed (11 nuevas en `tests/test_reintentos.py`).
  Probado a mano (2026-10-16, Ivania) con una base SINTÉTICA y envío SIMULADO (`C:\Users\User\prueba-avisos\`):
  fallido, incierto con y sin casilla, «Sí salió» y doble pestaña.
- **Decisión 2026-10-16 (Ivania): un cartel que cierra el fin de semana se procesa y se recomienda como cualquier
  otro.** Ya era así (`plazo_estado` no distingue días). Efecto conocido: el ciclo corre de lunes a viernes a las
  8:00, así que uno cargado el viernes después de las 8:00 que cierra el sábado o el domingo no llega a avisarse
  por correo (el lunes ya venció); sí aparece en el panel.

- **Lección 5 (Hito 1) cerrada** (2026-10-09): demo del viaje del dato ensayada y reto de comprensión de la semana 1
  superado (Ivania). Comprobación de la guía: ☑ caracteres especiales como texto · ☑ revisión conservada al
  reimportar (datos reales) · ☑ demo en vivo · ☑ reto de comprensión.