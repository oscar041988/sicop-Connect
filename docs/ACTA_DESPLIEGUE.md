# Acta de despliegue de SICOP CONNECT

Primera instalación en el servidor (lección 9, guía 17.2 paso 6). Pasos de referencia: `docs/DESPLIEGUE.md`,
sección 9.

**Cerrada el 2026-10-19 (Ivania, con Claude)** sin dos datos que Oscar no llegó a pasar: la salida del `evaluate`
del servidor y el reporte de la herramienta que instaló los archivos de Google. Quedan como «sin registro» y en
pendientes. Si llegan, se agregan aquí con su fecha.

Solo se anota lo que Ivania u Oscar confirmaron o lo que mostró el servidor. Lo que nadie recuerda queda
**«sin registro»**, sin suponer. Aquí **nunca** van contraseñas, llaves, `SESSION_SECRET`, el contenido de
`app.env`, los JSON de Google ni direcciones IP de personas.

## Datos de la instalación

| Dato | Valor | Fuente |
|---|---|---|
| Fecha y hora | jueves 15/10/2026, desde las 15:00 aprox. | Ivania (2026-10-19) |
| Presentes | Ivania y Oscar | Ivania |
| Servidor | VPS Ubuntu 24.04 en Hostinger (`DESPLIEGUE.md`, sección 1), nombre `soluciones` | `DESPLIEGUE.md`; consola (2026-10-19) |
| Servidor compartido | sí: junto con Nexus y otras apps web de la empresa | Ivania (2026-10-19) |
| Dirección del panel | https://sicop.hermatix.com | `ESTADO_PROYECTO.md` |
| Cómo se instaló | **Oscar no ejecutó comandos a mano:** usó un asistente de programación con IA (parecido a Claude Code), le dio las direcciones y la guía, y el asistente hizo la instalación y lo relacionado con GitHub. Qué comandos corrió y en qué orden: ☐ sin registro; la fuente es el historial de esa sesión del asistente. (El 19/10 Ivania había dicho «paquete `git archive` desde la Mac»; lo corrigió el mismo día.) | Ivania (2026-10-19) |
| Sentido de GitHub | **del servidor a GitHub**: el código ya estaba en el servidor y el asistente lo subió a GitHub (la historia nueva del 16/10, con fin de línea CRLF). Es al revés de lo planeado (GitHub → Mac → servidor). Cómo llegó el código al servidor: ☐ sin registro | Ivania (2026-10-19) |
| Secretos en GitHub | revisado el 19/10 (`main`, `diseno-fenova` y toda la historia): **ningún archivo secreto** (`.env`, `app.env`, base, JSON de Google, llaves) ni secretos dentro de archivos; solo valores de prueba inventados | Claude (2026-10-19) |
| Commit instalado | **`02b569b67103e37f4cdb83aa8ffbbfbfa7284315`** = `main` de GitHub (mostrar/ocultar contraseña). Que `app/COMMIT` traiga el hash indica que se usó `git archive` (es lo único que lo llena), salvo que se escribiera a mano. No incluye los PR #1 y #2 | `cat app/COMMIT` (Ivania, 2026-10-19) |
| Hash del paquete (SHA-256) | **no se comparó** (o no hay registro). Se compara sin falta en la próxima actualización (9.8) | — |
| Versión de Python | **3.12.3** | `python3 --version` (2026-10-19) |
| Base inicial | **No es el respaldo de Windows**, pero **sí tiene datos**. `/var/lib/sicop-connect/sicop.db` pesa 74,4 MB (la de Windows, 78,4 MB), su huella es `82495791…` (no `f32a3168…`) y no tiene evaluaciones (la de Windows sí). Se cargaron archivos en el servidor: `raw/` cambió el 16/10 a las 17:56 UTC (11:56 CR) e `incoming/` y la base el 19/10 a las 17:22 UTC (11:22 CR). Quién los cargó: ☐ sin registro. El respaldo del 16/10 **no está en el servidor** (`find` no lo encontró). Conclusión: se importó, pero **nunca se corrió `evaluate`** (caso 1 de la tabla 5.3 de `OPERACION.md`) | consola (Ivania, 2026-10-19) |
| HTTPS | lo configuró Oscar con las herramientas de Hostinger | Ivania |

## Estado del servidor (consola de Hostinger, Ivania, 2026-10-19 ~13:10)

| Qué se comprobó | Resultado |
|---|---|
| `sicop-web.service` | ☑ `enabled` y `active (running)`: arranca solo con el servidor. Corre `/opt/sicop-connect/.venv/bin/python -m uvicorn … --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers`, igual que `deploy/systemd/sicop-web.service` |
| Último arranque del servicio | sáb 17/10, 15:38 UTC (09:38 en Costa Rica). Por qué se reinició ese día: ☐ sin registro |
| Ajuste extra del servicio | el asistente agregó `/etc/systemd/system/sicop-web.service.d/hermatix.conf`: limita la memoria (máximo 512 MB), razonable en un servidor compartido. Qué más cambia: ☐ sin registro |
| Usuario con el que corre | ☑ **`sicop`**, no `root` |
| Carpetas y permisos | ☑ `/etc/sicop-connect` `700` y `app.env` `600`; `/var/lib/sicop-connect` `750` y `sicop.db` `600`; todo de `sicop`. Las otras apps no pueden leer la base ni la configuración. Los JSON de Google todavía no están (pendiente). Hay una carpeta `.cache` (`775`) que no está en la guía: probablemente de `pip` |
| `sicop-cycle.timer` | ☑ `disabled`: el ciclo diario no está activo, como estaba previsto (lección 10) |
| `curl -f http://127.0.0.1:8000/health` | ☑ `{"app":"ok","version":"0.1.0","environment":"production","database":{"status":"ok","detail":"Esquema aplicado (versión 0007)."}}` |
| Puerto 8000 | ☑ solo lo usa SICOP (el mismo proceso del servicio), y solo dentro del servidor (`127.0.0.1`) |
| IP real del visitante | ☑ el registro del panel muestra la IP pública de quien entra, no la del proxy: `--proxy-headers` funciona y el límite de intentos de login distingue a cada persona |
| Consola | se entró como `root` por la consola web de Hostinger. Para la operación diaria no hace falta |

## Pasos (`DESPLIEGUE.md`, sección 9)

| Paso | Máquina | Responsable | Resultado |
|---|---|---|---|
| 9.1 Publicar el commit revisado | Windows | Ivania | no se hizo así: el código salió del servidor hacia GitHub |
| 9.2 Empaquetar con `git archive` y copiar | Mac | asistente de IA de Oscar | probable (ver «Commit instalado»); ☐ sin registro de dónde ni cómo se copió |
| 9.3 Verificar el hash, usuario `sicop`, carpetas, instalar | Servidor | asistente de IA de Oscar | ☑ código en `/opt/sicop-connect` con su `.venv`, usuario `sicop`, carpetas con los permisos de la guía (15/10, 21:39–21:40 UTC); hash no comparado |
| 9.4 Configuración privada (`app.env`, sin envíos) | Servidor | asistente de IA de Oscar | `environment: production` ☑; ☐ sin registro del resto (no se lee `app.env`) |
| 9.5 Servicios, migración, `sicop-web` | Servidor | asistente de IA de Oscar | ☑ servicio activo, esquema 0007, `health` ok |
| Proxy con HTTPS | Hostinger | Oscar | ☑ el panel abre con HTTPS (Ivania, 2026-10-16) y pasa la IP real (2026-10-19) |
| 9.6 Activar el ciclo diario | Servidor | — | **no se hizo**, como estaba previsto (lección 10); timer `disabled` ☑ |

## Comprobación de la guía (lección 9)

- ☐ El hash del paquete coincide en la Mac y en el servidor: **no se comparó**. Queda anotado; se hace en la
  próxima actualización.
- ☑ `curl -f http://127.0.0.1:8000/health` responde en el servidor (Ivania, 2026-10-19).
- ☑ El panel abre en la dirección real con HTTPS (Ivania, 2026-10-16) y pide inicio de sesión: Ivania entró
  desde su celular (2026-10-19).
- ☑ Una oportunidad real revisada desde otra computadora (Ivania, 2026-10-19), después de que Oscar corrió
  `evaluate` en el servidor (camino B). Revisiones guardadas en el servidor, con las decisiones de Oscar y
  Anabelle en el comentario:
  - Corredores `20261001497`: No interesa («no es para la empresa»).
  - Puriscal `20261002246`: Interesa.
  - OIJ `20260903798`: No interesa (encaja, pero se decidió no participar).
  - Santa Ana `20261001587`: Interesa (copia de la revisión #4 de Windows).
  - CCSS `20261001749`: primero «Interesa» por error, corregida con una revisión nueva «No interesa»
    (cámaras intraorales). El historial guarda las dos.
  - Salida de ese `evaluate`: sin registro.
- ☑ Acta cerrada el 2026-10-19, con los «sin registro» señalados.

**Servidor compartido.** El usuario `sicop` y los permisos `700`/`600` de sus carpetas evitan que las otras apps
lean la base o `app.env`, y que SICOP toque las suyas. Confirmado el 19/10.

## Pendientes

| Pendiente | Responsable |
|---|---|
| Pedir el historial de la sesión del asistente de IA que hizo la instalación (sin contraseñas ni llaves) para reconstruir los pasos y saber qué hace `hermatix.conf` | Oscar |
| Como se subió a GitHub desde el servidor: en qué carpeta está ese repositorio y con qué permiso entra el servidor a GitHub (llave o token, y de qué cuenta). Un permiso para escribir en GitHub guardado en un servidor compartido es un riesgo: si no se va a usar, quitarlo | Oscar |
| ~~Base del servidor sin evaluar~~ | cerrado 2026-10-19: camino B, Oscar corrió `evaluate` en el servidor |
| ~~Revisar una oportunidad real desde otra computadora~~ | cerrado 2026-10-19: Corredores y otras 4 (Ivania) |
| Quién cargó archivos en el servidor el 16/10 y el 19/10 | Oscar |
| Pasar la salida del `evaluate` del servidor y el reporte de la herramienta que instaló los archivos de Google (comandos y salida de `doctor`) | Oscar / Ivania |
| Que los respaldos del servidor incluyan `/var/lib/sicop-connect/sicop.db` (con `app.cli backup`, no copiando el archivo) | Oscar |
| ~~Pasar al servidor los dos JSON de Google~~ | hecho 2026-10-19 por la herramienta de Oscar, según Ivania («ya pudimos habilitar la parte de avisos»). Sin registro de los comandos ni de `doctor`: ☐ confirmar que los avisos siguen **deshabilitados y en dry-run** hasta la lección 10, y que `sicop-cycle.timer` sigue `disabled` |
| Borrar los JSON de Google de la memoria USB y de la Mac | Oscar |
| Respaldos en el servidor: destino, retención, diario | Oscar (2026-10-19) |
| Repositorio de GitHub a privado | Oscar (2026-10-19) |
| Actualizar el servidor a `main` de hoy (LF y página «Avisos»; hoy corre `02b569b`), comparando el hash del paquete (9.8) | Oscar con Ivania, cuando se decida |
| Activar el ciclo diario, primero en dry-run | lección 10, aprobado por Oscar (2026-10-19) |
| ~~Confirmar que el proxy pasa la IP real~~ | cerrado 2026-10-19: sí la pasa |
| ~~Confirmar que el puerto 8000 es solo de SICOP~~ | cerrado 2026-10-19: sí |
