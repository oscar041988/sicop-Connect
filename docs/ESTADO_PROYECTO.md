# Estado de SICOP CONNECT

Última actualización: 2026-10-23 (revisión general del código, lock con playwright, auditoría de documentación y `ARQUITECTURA.md`, pruebas con Python 3.12, OPERACION probado en instalación limpia; rama `desarrollo`, 486 passed; **PR #3 abierto, espera a Oscar**) · Día / tarea: lección 10 preparada (hoja de la sesión, ampliaciones, práctica del reto 2); falta la sesión con Oscar (por calendario, lección 12) · Commit probado: `162afe8` (`main` de GitHub, 348 passed)

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

- **Enriquecimiento de carteles · lección 1, explorar la consulta (2026-10-27, rama `desarrollo`, solo local):**
  idea y aprobación de Oscar (`DECISION_OBTENCION.md` §9). Guía: `docs/Guia_Enriquecimiento_Carteles_SICOP (2).docx`.
  - Exploración manual de Ivania: la búsqueda avanzada encuentra el cartel por Número SICOP; la ficha no tiene URL
    propia.
  - Encargo 1: `scripts/explorar_concursos.py` (ventana visible, una consulta, sin descargas), corrido por Ivania
    con `20261002859`: **sin CAPTCHA ni bloqueo**. La ficha llega en respuestas JSON de `prod-api.sicop.go.cr`
    (ficha, líneas, documentos: 5, con PDF y `.xlsx`). Resultado y recomendación en `docs/DETALLE_CARTEL.md`:
    navegador + leer el JSON que recibe la página; no llamar a la API directamente.
  - Exploración de `20261001258` (Objetado; 432 líneas en páginas de 100; 49 documentos, la mayoría ZIP) y
    `20261001587`, sin bloqueo. **`20261001587` (Santa Ana, «Interesa») se modificó el 26/10 y cierra el 30/10
    23:59**, pero los datos abiertos de hoy siguen diciendo 23/10: el panel lo oculta como vencido. Avisado a Ivania.
  - Decisiones de Oscar (2026-10-27, por Ivania): campos útiles marcados en `DETALLE_CARTEL.md` §3 (todos menos
    clasificación del objeto y funcionarios); no se guardan datos de funcionarios; se guardan todos los tipos de
    documento. Commit `fa8fc4b`.
  - **Pendiente:** autoevaluación de la lección 1; tope de documentos por cartel (lección 3).
- **Enriquecimiento · lección 2, buscar el cartel y guardar su ficha (2026-10-27, rama `desarrollo`, solo local):**
  plan aprobado por Ivania.
  - `python -m app.cli enrich --nro N [--nro N…]` (1 a 3): navegador con ventana (`BROWSER_HEADLESS=false`),
    búsqueda avanzada como una persona y lectura del JSON que recibe la página (`app/sources/sicop_tender_detail.py`).
    Video y capturas en `RECORDINGS_DIR/<fecha>/<nro>/`; pausa `ENRICH_DELAY_SECONDS` (8) entre consultas.
  - Migración **0018** `tender_details`: una fila por versión de la ficha (copia fiel sin datos de personas, hash
    sin los campos que cambian con el reloj, campos marcados por Oscar); no se modifica ni se borra.
  - FALLO con captura: no encontrado, varios resultados, otro cartel, estructura o fecha cambiada, no JSON;
    CAPTCHA, «No fue posible acceder» o HTTP 403/429 detienen todo sin reintentar (código 2).
  - La terminal avisa si el cierre de la ficha no coincide con el de los datos abiertos (caso Santa Ana).
  - **561 passed** (25 nuevas en `tests/test_ficha.py`, SICOP SIMULADO en `tests/fixtures/ficha_simulada/`).
  - Ivania: respaldo y `migrate` (0018). **Primera prueba real (09:26): los 3 «no encontrado»**, sin bloqueo y sin
    guardar nada. Las capturas mostraron el número en «Código de clasificación»: la etiqueta «Número de SICOP» es
    flotante (va después de su casilla). Corregido: se usa la casilla del mismo contenedor que la etiqueta; la
    página simulada ahora tiene etiquetas flotantes y una prueba nueva lo comprueba (falla con el código anterior).
  - **Segunda prueba real (2026-10-27, Ivania): los 3 guardados** (fichas #1–#3), sin bloqueo. GPS: En
    recepción, cierre 28/10 09:00, 291782.16 CRC, 1 línea, 5 documentos · abarrotes: Objetado, cierre 09/11 08:30,
    sin monto, 432 líneas, 49 documentos · Santa Ana: modificado, cierre **30/10 23:59** (la terminal avisó que los
    datos abiertos dicen 23/10), 652190 CRC, 7 documentos. Coincide con lo explorado en la lección 1.
  - Comprobado por Ivania: el monto sale en **colones** en la pantalla de SICOP (la app lo guarda como CRC); el
    video muestra la consulta. Al repetir, un número quedó cortado (`202610015`): la app no abrió SICOP y avisó
    que no está en la base.
  - Repetido por Ivania con los 3 números completos: **los 3 «sin cambios»** (fichas #1–#3, sin filas nuevas).
    Comprobación de la lección 2 cumplida (commit `02b289e`).
  - **Pendiente · Ivania:** autoevaluación de la lección 2.

- **Mejoras de la exposición final con Oscar (2026-10-26):** se hacen una por una.
  - **1. Ayuda en «Cargar archivo» (hecho, 2026-10-26, rama `desarrollo`, solo local):** botones «Abrir el correo
    de SICOP en Gmail» (búsqueda de «Envío de reporte» en el buzón `SICOP_REQUEST_EMAIL`) e «Ir a SICOP (datos
    abiertos)» al lado del formulario; al final, un solo recuadro con las instrucciones completas paso a paso
    (descargar, pedir el reporte a mano, tipo de reporte, origen real/sintético/simulado, elegir archivo, subir,
    leer el resumen, `evaluate`). «real» viene elegido. El CSS lleva su huella en la URL (`estilo.css?v=…`) para
    que el navegador no use una copia vieja. **512 passed** (6 nuevas en `tests/test_carga.py`). Revisado por
    Ivania en el panel local.
  - **2. «Eliminar usuario» (hecho, 2026-10-26, rama `desarrollo`, solo local):** baja definitiva,
    no un borrado (las revisiones, seguimientos e historial lo siguen nombrando). Migración **0016**
    (`users.eliminado_en` + triggers: un eliminado no se modifica ni se reactiva; ningún usuario se borra). La baja
    lo desactiva, cambia su contraseña por una que no es de nadie, libera su correo y lo quita de la lista. Se
    bloquea si es encargado vigente de un expediente (primero reasignar), si su correo recibe los avisos, si es uno
    mismo o el último administrador. Casilla «Entiendo que no se puede deshacer». Va al historial
    (`eliminar_usuario`). **520 passed** (8 nuevas en `tests/test_baja_usuarios.py`). Probada en una copia de la
    base real (4 usuarios y 5 revisiones intactos; copia borrada).
    `migrate` 0016 en la base real y respaldo `sicop_20261026-115002` (esquema 0016, hash igual al manifiesto)
    hechos por Ivania (2026-10-26); probado por Ivania en el panel local.
    ZIP `sicop_20261026-115002.zip` (integridad ok, huella del `.db` igual al manifiesto) subido por Ivania al
    Drive de Hermatix (2026-10-26).
  - **3. Obtención y envío real en el servidor (hecho en código, 2026-10-26, rama `desarrollo`):**
    aprobado por Oscar (por Ivania): dos solicitudes por día, **06:30 y 14:00** (la de la mañana pasó de 07:30 a
    06:30 para alcanzar el correo de las 8:00); **descarga a mano** con un **recordatorio** a `OBTAIN_ALERT_TO`
    (SICOP bloquea la del programa); **«Cargar archivo» evalúa al subir** (≈ 15 s con la base real; ya no hay que
    correr `evaluate`); **envío real** de los avisos **solo a las 8:00** (`sicop-cycle.timer`, `run-cycle --send`).
    Migración **0017** (`turno` + índice único por día y turno + estado `enlace_recibido`),
    `OBTAIN_REQUEST_HOUR=06:30,14:00`, `OBTAIN_DOWNLOAD=manual`, `sicop-obtain.service` + `sicop-obtain.timer` (cada
    15 min de 06:00 a 19:45, lunes a viernes; la vuelta no corre el ciclo ni manda avisos), y el ciclo cuenta como
    nuevo un ZIP subido en el panel (antes no avisaba). Pasos para Oscar en `DESPLIEGUE.md` 9.9. En local nada se
    activó (`SOURCE_MODE=manual`).
    Respaldo `sicop_20261026-135112` (esquema 0016, huella igual al manifiesto) y `migrate` 0017 hechos por Ivania
    (2026-10-26); base local con integridad ok (4 usuarios, 5 revisiones, 3 solicitudes intactos).
    Evaluación al subir comprobada por Ivania (2026-10-26): importación 14:04:52 → evaluación 14:05:03, 12 820
    carteles (69 nuevos).
    **Pendiente · Ivania:** subir el ZIP del respaldo `sicop_20261026-135112` al Drive.
    **Pendiente · Oscar:** desplegar y
    activar (9.9); primera prueba real de punta a punta.

- **Gestor de documentos (mejora pedida por Oscar, 2026-10-26):** expediente por cartel con encargado, archivos
  (PDF, Word, Excel, ZIP; 10 MB configurable), notas, traspaso con descarga de todo, página de seguimiento y correo
  al nuevo encargado; las etapas se suman a «Ofertada» / «No se oferta». Propuesta en 5 pasos en
  `docs/GESTOR_DOCUMENTOS.md`. Decidido: cada expediente lo ven y editan solo su encargado y los
  administradores; los demás ven «En seguimiento · <nombre>», sin acceso; botón «Dar seguimiento» en la página
  del cartel para **cualquier usuario** (queda «sin encargado» hasta que un administrador lo asigne); solo un
  administrador asigna o cambia el encargado; el correo sale con el ciclo diario; paso 1 en dos entregas.
  - **Paso 1A hecho (2026-10-26, Claude a pedido de Ivania, rama `desarrollo`, solo local):** migración **0015**
    (`seguimientos`, `seguimiento_asignaciones`, sin borrado), `app/seguimiento.py`, botón y marca en el cartel,
    marca en el panel, página «Seguimiento» y expediente con su historial de encargados. **504 passed** (10 nuevas
    en `tests/test_seguimiento.py`; la prueba de CSRF de `test_acceso.py` ahora incluye las 2 rutas nuevas).
  - ~~Respaldo y `migrate`~~ **Hecho (2026-10-26, Ivania):** respaldo `sicop_20261026-093951` (esquema 0014,
    integridad ok, huella igual al manifiesto, ZIP creado) → `migrate` (0015); base local con integridad ok.
    Probado por Ivania en el panel local (2026-10-26): funciona.
    ZIP `sicop_20261026-093951.zip` subido por Ivania al Drive de Hermatix (confirmado el 2026-10-26).
  - **Siguiente:** paso 1B, el correo al nuevo encargado. Etapas del paso 5 **aprobadas** (26/10): preparando ·
    enviada · ganada · perdida.
- **Regla nueva (2026-10-26, Ivania): un cartel vencido sale solo del panel** en cuanto pasa su cierre (el plazo se
  calcula en cada consulta; no hay tarea programada). Se ve con el filtro «Vencido»; la exportación a Excel hace lo
  mismo; sigue en «Seguimiento»; nada se borra (`app/panel.py`, `listar`). 506 passed (pruebas del panel
  ajustadas y 1 nueva en `tests/test_seguimiento.py`).
- **Cambio de método (2026-10-21, Oscar):** todo se desarrolla y se prueba **en local**. El servidor queda fuera
  de las siguientes partes del proyecto; se actualiza una sola vez, cuando la app esté lista. Los pasos de
  servidor de este documento y de las actas (lección 10: dry-run, envío supervisado, timer, reinicio) quedan en
  espera hasta entonces. Oscar sigue revisando y uniendo los PR.
- **Rama `desarrollo` (2026-10-21):** junta todo para trabajar en local: `obtencion-automatica` (que trae
  `acta-despliegue` y `leccion-10`) + `doctor-sin-mail-to`, `regla-camaras-intraorales`,
  `panel-aviso-sin-evaluar` y `zip-pliegos`, sin conflictos. 360 passed; golden set 34/34. Desde aquí se sigue
  (ciclo local, lección 1); al final, Oscar revisa esta rama. Solo local.
- **Ciclo local en Windows (2026-10-21, Ivania, rama `desarrollo`):** respaldo, `doctor` (base 0008, avisos
  deshabilitados, dry-run sí, sin pendientes) y ciclos a mano en dry-run con datos REALES: #23 importó el ZIP
  del 19/10 (no estaba en la base; 10 778 carteles, 0 rechazadas); #24 «EN ESPERA» (ZIP copiado hace < 60 s,
  FALLO esperado); #25 importó el ZIP de hoy (cobertura al 21/10, 10 956 carteles, 0 rechazadas; 12 226 en la
  base), 3 avisos nuevos (`20261002692` × 3) y 6 que no se repitieron; vista previa revisada, bien.
  Tarea programada: `deploy/windows/sicop-ciclo.ps1` + `deploy/windows/README.md` (lunes a viernes 8:00,
  siempre dry-run, registro en `data\logs\`). Zona horaria de Windows cambiada a «América Central» (estaba
  en la de México). Tarea «SICOP CONNECT - ciclo diario» creada por Ivania; próxima ejecución 22/10 08:00.
  Prueba con `Start-ScheduledTask`: #26 corrió pero no escribió el registro (error del script, corregido en
  4330dd5); #27 FALLO esperado (sin ZIP nuevo), registrado en `data\logs\ciclo-2026-10.log` con código 1.
  ~~Pendiente · Ivania: `SCHEDULER_ENABLED=true` en `.env`~~ **Comprobado 2026-10-26 con `doctor`: «Programador:
  habilitado»** (leído de `.env`). Entrada de las 08:00 del 22/10: revisada (ver lección 3, «Pendientes de la prueba»).
  Enlace de SICOP: llegó 2 min después del correo del código (13:34 → 13:36; ver DECISION_OBTENCION.md §8).
- **Obtención automática · lección 1, lector de Gmail (2026-10-21, rama `desarrollo`):** hecha con pruebas
  SIMULADAS. `app/sources/gmail_reader.py`: permiso `gmail.readonly` con token aparte
  (`GOOGLE_READ_TOKEN_FILE`) y buzón `SICOP_REQUEST_EMAIL`; solo GET; filtra remitente `info@sicop.go.cr` y
  los dos asuntos exactos; usa solo el correo más reciente posterior a la solicitud; distingue «no llegó» de
  «formato desconocido»; nada sin enmascarar en mensajes. Comandos `obtain gmail-auth` y `obtain check-mail`.
  `gmail.py` reutilizado (clase `Permiso`; el envío no cambia). Fixtures `tests/fixtures/correo_*_simulado.eml`.
  391 passed (31 nuevas). **Prueba real de solo lectura hecha por Ivania (2026-10-21):** `obtain gmail-auth`
  aceptado como licitaciones@ (sin cambios en Google Cloud); `obtain check-mail` listó 11 correos de SICOP,
  todos reconocidos y enmascarados. El enlace llega 2 a 6 min después del código (DECISION_OBTENCION.md §8).
- **Obtención automática · lección 2, solicitud con navegador (2026-10-21, rama `desarrollo`):**
  - Playwright instalado por Ivania (`playwright>=1.45` en `requirements.txt`; `requirements.lock.txt` se
    rehace al final).
  - Exploración 2A hecha por Ivania (14:25, sin escribir el correo), registrada en `docs/ACCESO_SICOP.md`.
    Decisión: usar la interfaz y no la API interna.
  - 2B: `app/sources/sicop_browser.py` y el comando `obtain request [--ver]`:
    - selectores por texto y rol; una solicitud por día (tabla `solicitudes_sicop`, migración 0009);
    - código del lector de la lección 1, con espera de hasta `OBTAIN_CODE_TIMEOUT_MIN`;
    - CAPTCHA o bloqueo → «control no automatizable», sin reintentar; captura al fallar, con los campos vaciados.
  - Pruebas: página SIMULADA `tests/fixtures/sicop_simulado.html`, con Chromium sin ventana y la red cortada.
    402 passed (11 nuevas).
  - `migrate` (0009) aplicado por Ivania el 2026-10-21. Pendiente: UNA solicitud real con `obtain request --ver`
    (22/10, 7:30).
- **Obtención automática · lección 3, espera, descarga y validación (2026-10-21, rama `desarrollo`):**
  - Máquina de estados en `solicitudes_sicop` (migración 0010, que rehace la tabla):
    `solicitado → codigo_ingresado → esperando_enlace → descargado → validado`, o `fallido`, con la hora de cada
    cambio. Un índice único impide dos solicitudes el mismo día.
  - `app/sources/obtencion.py` y el comando `obtain poll [--seguir]`:
    - lee el enlace del buzón; descarga con Playwright (`sicop_browser.descargar`) a `data/raw/descargas/`, con SHA-256;
    - valida reusando `zip_pliegos` y `ciclo.revisar_csv`, más BOM, «;», encabezados y filas > 0;
    - copia el ZIP a `INCOMING_DIR`; plazo `OBTAIN_LINK_MAX_HOURS` (12 h); nunca pide otro reporte;
    - no importa: eso queda para la lección 4.
  - `obtain status` muestra las últimas solicitudes.
  - Pruebas SIMULADAS: reinicio, plazo, archivo vacío, HTML o con otros encabezados, enlace sin descarga.
    420 passed (18 nuevas).
  - `migrate` (0010) aplicado por Ivania el 2026-10-21.
  - **Primeras corridas reales (2026-10-21):**
    - #1, 15:12: FALLO antes del correo (dos iconos CSV durante la animación). Corregido en 1155896.
    - #2, 15:17: correo enviado y código hallado en 16 s, pero la ventana del código se cerró sola antes de
      escribirlo. Sin reporte; la solicitud del día ya contó.
    - Mejoras pedidas por Ivania: FALLO propio para la ventana cerrada, aviso de no tocar Chrome con `--ver` y
      capturas de cada paso con su resumen. 425 passed.
  - **Prueba real del 22/10 con Oscar (solicitud #3), empezó a las 08:04:**
    - `obtain request --ver` OK: código aceptado a las 08:05:22, sin `processId`. Capturas en
      `data\exports\obtencion-20261022-080438-3\`.
    - `obtain poll --seguir`: el enlace llegó a los ≈ 50 min (08:51–08:56). Al abrirlo, SICOP mostró una página
      de bloqueo («No fue posible acceder a la página solicitada… ID de soporte»). El programa lo reportó como
      «enlace vencido».
    - **Corregido:** esa página ahora es FALLO «control no automatizable», con el ID de soporte y una captura.
      Prueba SIMULADA nueva en `tests/test_obtencion.py`.
    - **Diagnóstico agregado (`eb91bcf`):** todo FALLO de descarga (bloqueo, descarga interrumpida o sin descarga)
      dice a qué hora se abrió el enlace, el código HTTP y la página final, sin parámetros (no muestra el
      `processId`). En la prueba del 22/10 no se registró el código HTTP; solo se sabe que no fue 403 ni 429.
      Revisado también: el enlace se copia bien del correo y la espera de 120 s alcanza (a mano, la descarga
      empieza en segundos). Causa del rechazo sin confirmar: solo SICOP puede verla con el ID de soporte.
      426 passed.
    - Ivania descargó el ZIP a mano con el mismo enlace y funcionó. Ciclo #28 (dry-run) OK: importaciones #18
      (10 990 carteles) y #19 (79 260 líneas), 0 rechazadas; cobertura al 21/10; 12 260 carteles en la base;
      evaluación con 0 nuevas y 9 actualizadas; 0 avisos nuevos y 6 preparados (los del 21/10). Detalle en
      `DECISION_OBTENCION.md` §8.
  - Pendientes de la prueba:
    - **Oscar:** preguntar a SICOP con el ID de soporte o dejar la descarga en manual. Hasta que decida, no se
      reintenta la descarga automática. Contacto (Condiciones Generales de Uso, sección 3): 1311 opción 3 o
      call-center@sicop.go.cr; piden usar su formulario de reporte de incidentes.
      **Enviado (22/10):** Ivania envió la consulta a call-center@sicop.go.cr con el ID de soporte. Se espera la
      respuesta; al llegar se anota en `DECISION_OBTENCION.md` §8 y se decide la activación de `obtain auto`.
      **Respuesta recibida (26/10), anotada en `DECISION_OBTENCION.md` §8 y reenviada a Oscar por Ivania:** SICOP no
      tiene API ni servicios web y no autoriza accesos ni integración de terceros. No menciona de forma expresa la
      descarga con un programa. Recomendación: descarga en manual (plan B). **Pendiente · Oscar:** decidir.
    - ~~La tarea de las 08:00 del 22/10 no dejó registro~~ **Revisado (22/10):** la computadora se encendió a las
      8:01. Windows marca 1 ejecución perdida y la tarea no la recupera (`StartWhenAvailable` apagado a propósito,
      como `Persistent=false` en el servidor). No es un error. **Decisión de Ivania: dejarla como está.**
    - **Para hablar con Oscar:** la hora del ciclo. Hoy el ZIP llegó hacia las 9:20 (solicitud a las 8:05 + enlace
      a los ≈ 50 min + descarga a mano), así que un ciclo a las 8:00 casi siempre correrá sin archivo nuevo
      (FALLO). Se decide junto con lo de la descarga bloqueada (respuesta de SICOP ya recibida, 26/10).
    - El OIJ `20260903798` sigue «preparado» aunque se descartó el 19/10 (cierra el 22/10). Es el comportamiento
      conocido: la revisión no saca un cartel de los avisos.
- **A4 · Cierre próximo y resumen semanal (2026-10-22, rama `desarrollo`, solo local, dry-run):**
  - Decisiones de Ivania (22/10):
    - decisiones finales nuevas «Ofertada» y «No se oferta»;
    - N = 3 días (`NOTIFY_CLOSING_DAYS`);
    - el resumen lo arma el ciclo del lunes.
  - Migración 0013: reconstruye `reviews` (dos decisiones más) y `notification_outbox` (motivos `cierre_proximo` y
    `resumen_semanal`). Se copian todas las filas con su id y se recrean los triggers.
  - **Cierre próximo:** se avisa si la última revisión es «Interesa» o «Revisar requisitos» y el cartel cierra en
    3 días o menos, aunque no sea Alta ni Media. Se avisa una vez por versión del cartel
    (clave `destinatario|N.º|versión|cierre_proximo`). Va en el mismo correo diario.
    - Si la fuente falla, el ciclo manda **solo** estos avisos, porque el plazo corre igual; el ciclo sigue en «fallo».
  - **Resumen semanal** (`app/resumen.py`) de la semana anterior:
    - Contenido: nuevas por familia, revisadas, pendientes sin revisar, cierres de los próximos 7 días y, si hay,
      adjudicaciones relevantes.
    - Un correo por destinatario y semana, con clave `destinatario|resumen|2026-W44|resumen_semanal`.
    - Uno viejo que quedó «preparado» no se envía.
    - A mano: `python -m app.cli notify --resumen-semanal --dry-run`.
  - Probado sobre una COPIA de la base real (sin tocar la outbox real):
    - el cartel `20261001587` («Interesa», cierra el 23/10) entra como «Cierra pronto…» para los 3 destinatarios;
    - asunto del resumen: «2 nuevas, 2 sin revisar, 3 por cerrar», más 1 familia con adjudicaciones.
  - Pendiente:
    - ~~un resumen «fallido» no aparece en la página «Avisos» (no es de un cartel)~~ corregido el 23/10 (ver
      «Revisión general»).
    - Que Oscar confirme N y el contenido del resumen.
- **A5 · Exportar a Excel (2026-10-22):**
  - Botón «Exportar a Excel» en el panel de carteles (`/oportunidades.xlsx`).
    - Usa los mismos filtros que la pantalla y exporta todas las páginas.
    - Hoja «Filtros» con lo aplicado, la fecha y la fuente.
  - Número SICOP y N.º de procedimiento como celdas de **texto** (formato «@»).
  - Ningún texto se guarda como fórmula (un título con «=» queda texto).
  - Montos: una columna por moneda, en Decimal.
  - Dependencia nueva `openpyxl` 3.1.5 (con `et_xmlfile` 2.0.0). El lock se regeneró en un entorno limpio y no
    cambió ninguna otra versión.
    - ~~Hallazgo: el lock no tiene `playwright`~~ **Corregido 2026-10-23:** entorno limpio con el lock +
      `playwright==1.64.0`; solo se sumaron `playwright`, `greenlet` 3.5.6 y `pyee` 14.0.0 (ruedas para Linux y
      Python 3.12 comprobadas). En el servidor, además: `.venv/bin/python -m playwright install chromium`.
      En el entorno limpio falló `test_cookie_alterada_no_sirve` por `httpx2` 2.16 (orden de las cookies, no la
      app): se arregló la prueba y `requirements-dev.txt` ahora usa el lock y fija las herramientas de prueba.
      Entorno nuevo con `requirements-dev.txt`: 483 passed.
  - Real (copia): 29 filas candidatas y 320 con «Todas».
- 470 passed tras A4 y A5 (11 nuevas en `tests/test_cierre_resumen.py`, 7 en `tests/test_exportar.py`).
- **Revisión general del código (2026-10-23, Claude a pedido de Ivania, rama `desarrollo`):** se leyó `app/`
  completo; 3 errores reales, comprobados en una base temporal (nunca en `data/`), corregidos con pruebas.
  - **Versión vigente de las reglas** (`app/panel.py`): era la de la última fila guardada. `evaluate --nro` con
    un YAML cambiado dejaba el panel, los avisos y el resumen con **un solo cartel**; volver a un YAML anterior
    dejaba la versión de la prueba. Ahora es la de la última evaluación completa (`evaluation_runs`).
  - **Resumen semanal fallido o incierto** (`app/reintentos.py`, página «Avisos»): no aparecía porque no tiene
    cartel. Ahora se lista como «Resumen semanal 2026-W43»; se reintenta solo en su misma semana y sale con
    `notify --resumen-semanal --send`.
  - **CSV ilegible** (`app/importers/csv_reader.py`): con un byte que no existe en cp1252 (p. ej. 0x81), el panel
    daba error 500 y el archivo quedaba en `INCOMING_DIR`. Ahora: «No se importó: no es UTF-8 ni cp1252…» y el
    archivo se borra. El ciclo ya lo manejaba bien.
  - 476 passed (6 nuevas en `test_panel.py`, `test_reintentos.py` y `test_carga.py`; 5 fallan con el código
    anterior). Commit `42a3386`, con push de `desarrollo` a GitHub (iba 11 commits adelante, nada nuevo de Oscar).
  - **Pendiente · Ivania:** abrir en la web el PR `main` ← `desarrollo` para Oscar (`gh` no está instalado).
  - **Menores, también corregidos el 23/10 (a pedido de Ivania):**
    - **Líneas huérfanas** (`app/importers/lineas.py`, `carteles.py`): las que llegaron antes que su cartel no
      entraban nunca (el mismo archivo no se importa dos veces). Ahora, al importar un cartel nuevo, se recuperan
      de `raw_snapshots` en su última versión; la importación avisa «Se recuperaron N líneas…».
    - **Bloqueos de login** (`app/web/intentos.py`): la lista de bloqueados crecía sin tope; ahora fallos y
      bloqueados tienen un tope juntos (en un ataque se sueltan primero los que están por vencer).
    - **Rendimiento de `evaluar_base`**: cada cartel revisa solo sus evaluaciones anteriores. Con 10 000 carteles
      sintéticos, de 21,3 s a 4,8 s (medido aparte; no cambia resultados).
    - **ZIP de adjudicaciones en el ciclo** (`app/ciclo.py`): antes iba a `con_error`; ahora se importa después de
      los carteles (cortado → `con_error` entero). **Decisión de Claude, para que Ivania/Oscar la revisen:** no
      cuenta como «datos del día»; si solo llegan adjudicaciones, se importan, no se avisa y el ciclo queda en
      «fallo · solo llegaron adjudicaciones».
    - 483 passed (7 nuevas en `test_importador_relaciones.py`, `test_acceso.py`, `test_evaluar.py` y
      `test_ciclo.py`; 6 fallan con el código anterior; la de `evaluar` pasa en los dos porque el resultado no cambia).
- **Lección 18 adelantada · auditoría de documentación y `ARQUITECTURA.md` (2026-10-23, Claude a pedido de Ivania,
  rama `desarrollo`):**
  - Un script comparó cada `python -m app.cli …`, ruta de archivo y variable de README, OPERACION, DESPLIEGUE y
    REGLAS con el código: ninguno roto. Lo desactualizado salió al leerlos completos.
  - **`docs/ARQUITECTURA.md` (nuevo):** diagrama de la sección 15.1 actualizado, componentes, procesos, recorrido
    de un dato, módulos, tablas, decisiones de diseño, seguridad, despliegue y lo pendiente de verificar.
  - **README:** decía «sin usuarios ni contraseña»; ahora: primer usuario, comandos frecuentes y páginas del panel.
  - **OPERACION:** ya no hay que descomprimir el ZIP; el panel sí avisa de datos sin evaluar; se agregaron
    adjudicaciones, «Ofertada» / «No se oferta», Excel, Competencia, cierre próximo, resumen semanal y mensajes
    nuevos; se quitó el defecto de `MAIL_TO` (ya corregido).
  - **DESPLIEGUE:** estado real (instalado el 15/10, GitHub por ramas), Playwright en el servidor (*pendiente de
    verificar en Ubuntu*), variables nuevas de `app.env` y `evaluate` después de `migrate` al actualizar.
  - **REGLAS:** cifras por familia con las reglas vigentes `b880e0d350e1` (base local en solo lectura: 12 260
    carteles, 7/7–21/10), campo de decisión y qué versión muestra el panel.
  - ~~Pendiente · Ivania (lección 18, paso 2): seguir `OPERACION.md` al pie de la letra en una instalación
    limpia~~ **Hecho 2026-10-23 (Ivania, guiada por Claude):** clon nuevo de `desarrollo` en
    `C:\Users\User\sicop-prueba`, Python 3.12, `.env` de ejemplo, datos REALES copiados de `procesados`. Se
    siguieron el README y `OPERACION.md` 1 a 6: carga por el panel, `evaluate` (11 134 carteles, 20 candidatos),
    revisión, Excel, adjudicaciones y Competencia, ciclo OK (#7) y FALLO sin archivos (#8), vista previa de avisos
    (3), archivo repetido sin duplicar, respaldo, ZIP y restauración (huella igual, revisión presente). Al terminar
    se borraron las dos carpetas de la prueba.
  - **10 trabas encontradas y corregidas** en README y OPERACION: cómo bajar el código; `python -m venv` falla con
    el Python Install Manager (`py -V:3.12`); comandos largos que se parten al copiarlos; qué «PENDIENTE» de
    `doctor` son normales; «pliegos (.zip)» una sola vez (Ivania subió tres veces los carteles con tipos
    distintos); el catálogo (sin él se pierden candidatos); lo subido por el panel queda en `INCOMING_DIR` y el
    ciclo lo ve como «YA IMPORTADO»; números de ciclo que saltan; nombre del respaldo elegido solo; comprobar que
    la restauración se hizo (el primer intento no se hizo y la revisión aparecía igual).
  - **Pendiente · Ivania:** el informe final con sus palabras (sección 21.3).
    **Esquema listo (2026-10-23):** `docs/INFORME_FINAL.md`, con las 9 partes de la sección 21.3, los datos de
    apoyo con su fuente y las preguntas a responder (no tiene texto redactado). Estado propuesto de los objetivos,
    **a confirmar por Ivania**: O1–O4 cumplidos · O5 y O6 parciales · O7 pendiente · O8 en curso. ~~Anotar las
    horas del 21 al 23/10~~ **anotadas en `docs/METRICAS.md`** (Ivania, 23/10: 7 h cada día, 21 h; uso de Claude no
    registrado). Las secciones 6 y 9 se completan después del servidor y los simulacros.
    **Informe escrito (2026-10-23, Ivania), en Google Docs** (no está en el repositorio; Claude no lo ha leído).
    Debe quedar en el Drive de Hermatix, compartido con Oscar. **Pendiente · Ivania:** actualizar las secciones 6
    (operación) y 9 (pendientes y plan de continuidad) después de la lección 15 y los simulacros.
    **2026-10-26:** datos de apoyo de las secciones 6 y 9 al día en `docs/INFORME_FINAL.md` (Claude no puede abrir
    el Google Doc). La 9 y la parte de Windows de la 6 ya se pueden escribir; la del servidor espera a la lección
    15. Simulacro 5 anotado en `OPERACION.md` §7 (Windows, dry-run, ciclo #28; 24 avisos = 24 claves distintas).
    **Hecho 2026-10-26 (Ivania, en el Google Doc; Claude no lo ha leído):** secciones 6 (parte de Windows), 7 y 9.
    **Queda · Ivania:** la parte del servidor de la sección 6, después de la lección 15 y los simulacros allí.
    **2026-10-26 (Ivania):** la parte del servidor de la sección 6 quedó escrita **como plan**. **Queda · Ivania:**
    completarla con los resultados reales de la lección 15 y de los 5 simulacros en el servidor (`OPERACION.md` §7).
- **A3 · Calidad de reglas (2026-10-23, Claude a pedido de Ivania, rama `desarrollo`):** `python -m app.cli
  score-rules` (`app/calidad.py`) mide precisión y cobertura por familia con el YAML actual, contra el golden set
  (filas confirmadas) y las revisiones (encaja: «Interesa», «Revisar requisitos», «Ofertada»; no encaja: «No
  interesa · No encaja»; lo demás no cuenta). Errores con su evidencia en tres tipos (falsa alerta, otra familia,
  no alertado). Cada medición se guarda con su versión de reglas (migración **0014**: `rule_score_runs`,
  `rule_scores`, sin borrado); una igual a la anterior no se repite. Página «Calidad de reglas» en Administración
  (solo admin). Documentado en `docs/REGLAS.md` 4.1.
  - Primera medición sobre una **copia** de la base real (la base real no tiene la 0014 hasta correr `migrate`):
    34 casos del golden set + 3 revisiones · precisión 95,0 % (19/20) · cobertura 100 % (19/19). Errores: falsa
    alerta en `iot_frio` (`20261000990`, «telemetría… Acueducto», revisado «No encaja») y otra familia en
    `rastreo_activos` (`20260802605`).
  - **Pendiente · Ivania/Oscar:** decidir el caso «telemetría» con la receta de `REGLAS.md` sección 3.
    **Propuesta lista (2026-10-26), pendiente · Oscar:** pasar «telemetria» a señal media en `iot_frio`. Simulado
    en memoria sobre la base: de 3 carteles con «telemetría», solo cambia el falso positivo (Alta → Baja). Pregunta
    para Oscar: ¿Osmia IoT vende telemetría para acueductos? Detalle en `REGLAS.md` §6. YAML sin tocar.
  - ~~`migrate` y `score-rules` en la base local~~ **Hecho 2026-10-23 (Claude, a pedido de Ivania):** respaldo
    `sicop_20261023-140005` (esquema 0013, integridad ok) → `migrate` (0014) → `score-rules`: **medición #1
    guardada** en la base real, igual a la de la copia (95,0 % / 100 %, los mismos 2 errores).
  - Pruebas: 494 passed con Python 3.14 y con 3.12 (8 nuevas en `tests/test_calidad.py`; las listas de
    migraciones y la versión de esquema de las pruebas pasan a 0014). En una corrida con 3.12 falló 1 prueba que
    no se pudo identificar y no se repitió en 3 corridas más: **prueba intermitente por investigar**.
  - **Investigada (2026-10-23):** sin identificar. Claude mostró solo la última línea de esa corrida y descartó
    el nombre de la prueba. Sin repetirse en 8 corridas completas más con 3.12; tampoco la prueba del bloqueo
    entre procesos (40 veces) ni las 16 de navegador Chromium real (12 veces), que son las sospechosas por
    depender del tiempo. 1 falla en unas 12 corridas: si vuelve a pasar, anotar el nombre (línea `FAILED`).
  - **Encontrado al investigar y corregido:** las pruebas del ciclo usan la fecha real y **fallaban los lunes**
    (16 pruebas): ese día el ciclo arma el resumen semanal y la outbox traía una fila más. La app estaba bien.
    Comprobado simulando un lunes. Corrección solo en `tests/test_ciclo.py` (en esas pruebas «no es lunes»; lo de
    los lunes se prueba con fechas fijas en `tests/test_cierre_resumen.py`). Sin esto, la suite habría fallado el
    lunes 26/10. 494 passed con 3.12 y 3.14.
- **Lección 19, paso 1 adelantado · métricas del mes PRELIMINARES (2026-10-23):** `docs/METRICAS.md`, sección
  «Métricas del mes», desde la base local (solo lectura) y las bitácoras: 12 260 carteles, 28 oportunidades Alta o
  Media (3 solo por las líneas), 0 rechazos, 16 ciclos (12 «fallo» por falta de archivo), 0 avisos duplicados,
  95,5 h humanas en 3 semanas; uso de Claude casi sin registrar. **Se recalculan el 29/10 con la base del
  servidor.** Falta: tiempo ahorrado (con Oscar). La presentación (pasos 3 y 4) la prepara y ensaya Ivania con
  sus palabras (guía 21.2).
- **Pruebas con Python 3.12, el del servidor (2026-10-23, Ivania instaló 3.12.10 con `py install 3.12`):** entorno
  aparte con `requirements-dev.txt`, sin conflictos. Falló 1 prueba que con 3.14 pasaba: con 3.12, un correo con
  remitente `info@sicop.go.cr <falso@otro.test>` se aceptaba como de SICOP (Python se quedaba solo con
  `info@sicop.go.cr`). Corregido en `app/sources/gmail_reader.py`: un remitente con defectos de formato se
  rechaza siempre; prueba nueva de que los remitentes de SICOP bien escritos siguen entrando. **486 passed con
  3.12 y con 3.14.** Descripción del PR (`docs/PR_DESARROLLO.md`) al día.
- **PR #3 `main` ← `desarrollo` abierto (2026-10-23, Ivania, en la web):** título y descripción de
  `docs/PR_DESARROLLO.md`; apunta a `a828c90` (58 commits sobre `main` = `162afe8`). Espera la revisión de Oscar.
  **Pendiente · Oscar:** revisar y unir el #3; cerrar sin unir los PR de las ramas que ya están dentro de
  `desarrollo`; decidir lo de «Para decidir» de la descripción. Después: actualizar el servidor (lección 15,
  `docs/DESPLIEGUE.md` 9.8). Si Oscar pide cambios, se hacen en `desarrollo` y el #3 se actualiza solo.
- **Inteligencia competitiva · A2 (2026-10-22, rama `desarrollo`, solo local):** hecha con el archivo REAL
  «Adjudicaciones en firme» (reportes 6, 6.1 y 6.2; mapeo en `docs/MAPEO_DATOS.md`).
  - **El adjudicatario viene solo como cédula, sin nombre.** El nombre y la unión de cédulas los pone Hermatix
    en `config/competidores.yaml` (hoy vacío; las cédulas sin nombre se muestran como «Cédula …»).
  - Migración 0012 (`adjudicaciones`, `adjudicacion_proveedores`, `adjudicacion_lineas`) e importador del ZIP tal
    como llega: `python -m app.cli import --report adjudicaciones --path "<ZIP>" --origen real`.
  - La familia es la del cartel, con las mismas reglas, porque las líneas adjudicadas no traen texto.
  - Página «Competencia» (cualquier usuario con sesión):
    - por familia: quién gana, cuántas veces, con qué instituciones y el monto por moneda (cantidad × precio −
      descuento, sin impuestos, sin convertir);
    - filtros por periodo en firme y por prioridad;
    - cada número lleva a sus registros, con la importación y el archivo de origen.
  - Las 88 líneas con más de un registro distinto no se suman: se cuentan aparte.
  - Importado en la base local: 0 rechazos.
    - En la primera pasada se rechazaron 4345 filas porque SICOP marca «sin valor» con un espacio. Se corrigió,
      se quitó solo esa importación (#20, copia de la base antes) y se reimportó como #23.
    - Resultado: 9155 carteles adjudicados (jul–oct 2026); 7096 con su cartel importado; **10 en Alta o Media**
      (iot_frio 5, gps_flotas 4, cámaras corporales 1, rastreo de activos 1); 13 cédulas ganadoras sin nombre.
  - 452 passed (15 nuevas en `tests/test_competencia.py`, datos SINTÉTICOS).
  - **Pendiente · Ivania/Oscar:**
    - poner nombre a las cédulas ganadoras en `config/competidores.yaml` (Registro Nacional o ficha del
      proveedor en SICOP); **avance 2026-10-26 (Ivania):** 7 empresas con nombre (las 7 que compiten de verdad). De las
      13: 5 solo ganaron otras líneas de compras mezcladas de la CCSS (no se buscan); `0702950024` es persona física
      (sin nombre, para no guardar datos personales en Git; a confirmar con Oscar).
      Hallazgo: la página cuenta como competidor a quien ganó cualquier línea de un cartel de la familia (mejora aparte;
      ejemplo: `3101941043` sale primera en `iot_frio` con 2 carteles, por líneas que no eran de Hermatix);
      **página revisada en el panel local por Ivania (2026-10-26): salen los 7 nombres**;
    - descargar «Contratos» si se quiere comparar;
    - revisar la página en el panel.
- **Obtención automática · lección 4, integrar al ciclo (2026-10-22, rama `desarrollo`, solo local):** hecha con
  pruebas SIMULADAS; **no activada**.
  - Oscar quiere todo automático. Mientras SICOP bloquee la descarga, el plan B es un clic: alerta por correo →
    descargar a mano con «Envío de reporte» → dejar el ZIP en `INCOMING_DIR`.
  - `app/sources/automatico.py` y el comando `obtain auto`: una vuelta cada 15 min, 07:00–20:00, lunes a viernes.
    - Con `SOURCE_MODE=manual` no hace nada.
    - Desde `OBTAIN_REQUEST_HOUR` (07:00) pide una vez por día; sondea el buzón.
    - Si falla, manda **una** alerta a `OBTAIN_ALERT_TO`, sin enlace ni código (en dry-run, solo
      `EXPORTS_DIR\alerta-obtencion-<n>.txt`).
    - Si hay un archivo en `INCOMING_DIR`, corre el ciclo en dry-run con modo `auto` en `source_runs`.
    - Tiene su propio bloqueo y respeta los de `obtain poll` y `run-cycle`.
  - Migración 0011: `alerta_estado` y `alerta_en` en `solicitudes_sicop`; las fallidas de antes quedan «anterior»
    (sin alerta). `obtain poll` ahora guarda `enlace_recibido_en` también cuando falla la descarga.
  - Decisiones de Ivania (22/10): la alerta va a licitaciones@; la tarea nueva reemplaza la de las 8:00.
  - Windows: `deploy/windows/sicop-obtencion.ps1` y su sección en `deploy/windows/README.md` (la tarea **no** se
    creó). `docs/OPERACION.md` 3.1: activar, volver a manual, qué hacer ante cada FALLO, renovar Gmail y dónde mirar.
  - `.env.example`: `OBTAIN_REQUEST_HOUR=07:00`, `OBTAIN_ALERT_TO=` (sin valor).
  - 437 passed (11 nuevas en `tests/test_automatico.py`).
  - Fuera de esta lección: plantillas de systemd y despliegue (al final, con el servidor) y las dos solicitudes
    al día (después de la respuesta de SICOP).
  - ~~`migrate` (0011) en la base local~~ hecho (22/10). **Pendiente · Ivania/Oscar:** para activar: `.env` (`SOURCE_MODE=auto`,
    `OBTAIN_ALERT_TO`), una vuelta a mano y crear la tarea, cuando Oscar y Ivania lo decidan.
- **Obtención automática (2026-10-21):** Oscar aprobó la opción de automatizar la descarga de SICOP; guía en
  `docs/Guia_Obtencion_Automatica_SICOP.docx` (revisada por Claude el 2026-10-21). Decisión y reglas nuevas
  escritas en `docs/DECISION_OBTENCION.md` (secciones 6 y 8): el código por correo se automatiza; CAPTCHA o
  bloqueo, nunca. Ajustes a la guía: la lección 4 solo en su parte local (servidor al final); token de Gmail de
  lectura aparte del de envío, con el mismo cliente; confirmar en la primera prueba real cuánto tarda el enlace
  (guía: horas · observado: ≈ 1 min). Términos de uso y 4 documentos de SICOP revisados el 2026-10-21: sin
  prohibición (detalle en la regla 3). Pendiente: el Reglamento de SICOP (no conseguido) y que Oscar acepte el
  documento. La guía `.docx` no va a Git: su captura 7 muestra un enlace real de descarga (`processId`).
- ~~Fin de línea CRLF vs LF~~ **Decidido 2026-10-19 (Oscar): LF**, normalizado con `.gitattributes`. **Hecho en la
  rama `fin-de-linea-lf` (2026-10-19), unido a `main` con el PR #1:** todo el texto en LF; excepción `*.csv -text` (byte por byte,
  con el CRLF de SICOP: 3 pruebas dependían de él y en Linux habrían fallado). 337 passed.
- ~~Forma de trabajo con GitHub~~ **Decidido 2026-10-19 (Oscar): por ramas** (Ivania sube ramas; nada directo a
  `main`). PR #1 y #2 **unidos por Oscar el 2026-10-19** (`main` = `162afe8`). Ramas `reintento-avisos`,
  `fin-de-linea-lf` y `reintento-avisos-lf` borradas (Ivania lo pidió, 2026-10-19).
  **2026-10-20:** `main` local = `origin/main`. Ramas esperando a Oscar: `acta-despliegue` y `leccion-10` (va
  encima de `acta-despliegue`: unir esa primero); independientes, desde `main`: `doctor-sin-mail-to`,
  `regla-camaras-intraorales`, `panel-aviso-sin-evaluar` y `zip-pliegos` (sus PR los crea Ivania en la web).
- ~~Cerrar la lección 9~~ **Cerrada 2026-10-19.** Queda del acta:
  borrar los JSON de Google de la USB y la Mac, quién cargó archivos en el servidor el 16/10 y el 19/10, el
  historial del asistente, y actualizar el servidor a `main` comparando el hash (9.8) · Oscar.
- **Siguiente: lección 10** (ciclo de las 8:00 y envío real) · Ivania con Oscar, en orden: confirmar
  destinatarios → `run-cycle --dry-run` en el servidor → envío supervisado con `notify --send --solo` → activar
  `sicop-cycle.timer` → comprobar que sobrevive a un reinicio. Decidir quién deja los archivos de SICOP antes de
  las 8:00 (sin archivo, el ciclo sale en «fallo»).
  **2026-10-20:** JSON de Google en el servidor y `notify --send` desde el servidor entregó el correo (ver
  «Bloqueos del despliegue»). Hoja de la sesión y acta: `docs/ACTA_LECCION_10.md`. Propuesta de ampliaciones
  para Oscar: `docs/AMPLIACIONES.md`.
- Salieron de la prueba de `OPERACION.md` (2026-10-19), cada uno es un cambio aparte y no se hace sin pedirlo:
  - ~~Regla de «cámaras»: que no cuente con «intraorales» o equipo médico (falso positivo CCSS `20261001749`);
    agregarlo al golden set~~ **Hecho 2026-10-20** en la rama `regla-camaras-intraorales` (`a707895`, PR para
    Oscar): exclusión «intraoral» en `videotelematica` (decisión de Ivania; «equipo medico» se descartó por el
    riesgo con ambulancias). Reglas `b880e0d350e1`; golden set 34/34 = 100 %; 348 passed. En la base de Windows
    la CCSS pasó a «sin coincidencia» y el OIJ sigue Alta. En el servidor aplica al actualizar y correr `evaluate`.
  - ~~El panel no avisa de carteles nuevos sin evaluar~~ **Hecho 2026-10-20** en la rama
    `panel-aviso-sin-evaluar` (`b734ccc`, PR para Oscar; opción elegida por Ivania: aviso en el panel).
    Migración 0008 (`evaluation_runs`): cada evaluación completa queda anotada; si hay una importación de
    carteles, líneas o catálogo posterior, la lista y el detalle dicen «Hay datos importados después de la última
    evaluación… ejecuta evaluate». 351 passed (3 nuevas). Base de Windows: respaldo `sicop_20261020-094004`,
    `migrate` → 0008, aviso antes de `evaluate` y sin aviso después. **Al actualizar el servidor:** `migrate` y
    luego `evaluate` (una base existente pide la primera evaluación).
  - ~~`doctor` marca `MAIL_TO` como pendiente aunque ya no se usa~~ Hecho en la rama `doctor-sin-mail-to`
    (`69172a0`, PR esperando a Oscar).
  - **ZIP de pliegos sin descomprimir (A1, opción O4a de `docs/DECISION_OBTENCION.md`): hecho 2026-10-20** en la
    rama `zip-pliegos` (`41cf4db`, PR para Oscar; Ivania pidió adelantarlo). El ciclo y el panel («pliegos
    (.zip)») importan los dos CSV del ZIP tal como llega; el ZIP se mueve entero a `procesados` o `con_error`.
    356 passed (8 nuevas). Con el ZIP real del 9/10 sobre una copia de la base: «YA IMPORTADO» #7 y #8, sin
    duplicar. El paso 1 de `docs/ACTA_LECCION_10.md` tiene los dos caminos (A: ZIP · B: CSV) según la versión
    del servidor.
  - ~~Destinatarios activos: confirmar que son los correctos~~ **Confirmados por Oscar (2026-10-21):** `aumana@`,
    `calvarez@` y `priaraya@`, sin cambios (anotado en `docs/ACTA_LECCION_10.md`).
  - ~~Copiar el respaldo más reciente a una memoria USB~~ **Hecho 2026-10-23, sin USB (Ivania no tiene):**
    respaldo `sicop_20261023-095705` (esquema 0013, integridad ok, huella `107ae1ed…`; 12 260 carteles,
    5 revisiones, 4 usuarios) comprimido en `C:\Users\User\respaldos-sicop\sicop_20261023-095705.zip` (32 MB; la
    huella de la base dentro del ZIP se comprobó contra el manifiesto) y subido por Ivania al Google Drive.
    **Pendiente · Oscar:** confirmar la carpeta: debe ser del Drive de Hermatix, compartida solo con él, sin
    enlace público (el ZIP tiene los usuarios del panel). Desde ahora, la copia fuera de la computadora va ahí.
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
- **Autoevaluación de la lección 10 (2026-10-20, Ivania, antes de la sesión con Oscar): las tres correctas.**
  - Si apaga su computadora: sigue lo que vive en el servidor (panel, base con las revisiones, ciclo); no está lo
    que solo existe en su Windows. *Ajustes:* el ciclo automático todavía no corre (temporizador apagado hasta la
    sesión); las ramas ya están todas en GitHub, así que solo la base local y los respaldos sin copiar a la USB
    dependen de su disco.
  - A las 8:00: `sicop-cycle.timer` lanza `sicop-cycle.service` (`run-cycle`): recoger → importar → evaluar →
    avisar; sin archivo nuevo registra «FALLO» y la outbox impide reenviar una versión ya avisada. *Ajustes:* es
    **de lunes a viernes** (`Mon..Fri 08:00 America/Costa_Rica`, `Persistent=false`), no todos los días; sin archivo
    nuevo igual evalúa (los plazos cambian), solo no avisa; se avisa solo Alta/Media con plazo abierto y vistos en
    los últimos 7 días, en un resumen por destinatario.
  - El temporizador va al final: dry-run y envío supervisado confirman cada paso; activado antes, un error se
    repetiría cada mañana sin nadie mirando.
  - Repasar: días y hora exactos del temporizador; condiciones para que un cartel se avise.
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