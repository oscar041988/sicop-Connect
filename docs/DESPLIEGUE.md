# Despliegue de SICOP CONNECT — borrador

Datos del servidor y del correo para instalar el panel en la lección 9 (jueves 15/10; guía, sección 17).
Reunión de Ivania con Oscar: 2026-10-12 (lección 6, paso 3).

**Estado: BORRADOR.** Lo marcado «confirmado» lo dijo Oscar en la reunión del 2026-10-12; todavía no se ha
comprobado en el servidor con los comandos de la última columna. Los pasos de instalación (Windows → Mac →
servidor) están en la sección 9 (lección 8, encargo B).

> **Actualizado 2026-10-23 (revisión contra el código).** La instalación se hizo el 15/10 (acta:
> `docs/ACTA_DESPLIEGUE.md`), con HTTPS por las herramientas de Hostinger; el servidor tiene `02b569b`. Las
> secciones 1 a 8 son el registro de la preparación y se dejan como estaban; lo que cambió desde entonces está
> marcado. Para actualizar el servidor a `desarrollo`: sección 9.8. Arquitectura: `docs/ARQUITECTURA.md`.

## Reglas al registrar

- **Este archivo va a Git:** se anotan datos, **nunca secretos**. Sí «usuario SSH: oscar»; no su contraseña,
  su llave privada, la llave de la API de Google ni `SESSION_SECRET`. Los secretos los coloca Oscar directamente
  en el servidor (`/etc/sicop-connect/app.env`).
- Si un dato no se sabe, **no se inventa**: se anota como bloqueo (sección 7) con responsable y fecha.
- Distinguir siempre: dato **confirmado** (lo dijo Oscar o el proveedor) / **comprobado** (se vio en el servidor
  con un comando) / **supuesto** / **pendiente**.
- Al cambiar un dato, actualizar la fecha y quién lo confirmó.

## 1. El servidor

| Pregunta | Respuesta | Estado | Cómo se comprueba |
|---|---|---|---|
| ¿Propio o alquilado? ¿Con qué empresa? | Alquilado a la empresa de hosting Hostinger | confirmado (Oscar, 2026-10-12) | contrato / panel del proveedor |
| ¿Servidor propio (VPS) o hosting compartido con cPanel? | Se puede crear un usuario sin privilegios y tiene Ubuntu: parece un VPS | supuesto | Oscar / proveedor |
| Sistema operativo y versión | Ubuntu 24.04 | confirmado (Oscar, 2026-10-12) | `cat /etc/os-release` |
| Versión de Python (se necesita 3.12 o más) | Oscar (2026-10-13): ya tiene 3.12 o más. Ver nota 1 | confirmado, falta comprobar | `python3 --version` |
| ¿Tiene systemd? | Ubuntu 24.04 lo trae | supuesto | `systemctl --version` |
| ¿Sale a internet? | Sí | confirmado (Oscar, 2026-10-12) | `curl -I https://pypi.org` |
| Zona horaria del servidor (el programador de la lección 8 depende de ella) | | pendiente | `timedatectl` |
| Dirección IP | 2.25.81.33 | confirmado (Oscar, 2026-10-12) | `ip -4 addr` |

**Nota 1 · Python.** Ubuntu 24.04 normalmente ya trae Python 3.12 (es parte del sistema). Antes de descargar
otro, conviene revisar con `python3 --version`. Si aparece 3.12, sirve para el proyecto y recibe las
actualizaciones de seguridad de Ubuntu (`apt`); solo faltaría el paquete `python3.12-venv` para crear el entorno.
Instalar «la última» por separado es posible, pero hay que actualizarla a mano. Decide Oscar.

## 2. Cómo se entra (SSH)

| Pregunta | Respuesta | Estado |
|---|---|---|
| Usuario SSH | Aún no definido | **bloqueo** (sección 7) |
| Dirección del servidor | 2.25.81.33 (o `sicop.hermatix.com` cuando el DNS apunte ahí) | confirmado (Oscar, 2026-10-12) |
| Método de acceso (llave SSH o contraseña) | Lo maneja Oscar | confirmado (Oscar, 2026-10-12) |
| Desde qué computadora se entra | La Mac de Oscar (guía, sección 17.1) | supuesto |
| ¿Quién puede usar `sudo` (permisos de administrador)? | | pendiente |

## 3. Usuario de servicio y rutas

La app corre con un usuario propio sin privilegios, nunca como root (guía, sección 17.2).

| Elemento | Propuesta de la guía | Decisión | Estado |
|---|---|---|---|
| Usuario de servicio | `sicop` (sin privilegios) | Sí se puede crear | confirmado (Oscar, 2026-10-12) |
| Código | `/opt/sicop-connect` | Sirve | confirmado (Oscar, 2026-10-12) |
| Base, originales y archivos de entrada | `/var/lib/sicop-connect` | Sirve | confirmado (Oscar, 2026-10-12) |
| Configuración privada | `/etc/sicop-connect/app.env` (propietario `sicop`, permisos 600) | Sirve | confirmado (Oscar, 2026-10-12) |
| Respaldos | | | pendiente |

## 4. Cómo se abrirá el panel (dirección web y HTTPS)

| Pregunta | Respuesta | Estado |
|---|---|---|
| Dirección web del panel | https://sicop.hermatix.com | confirmado (Oscar, 2026-10-12) |
| ¿Hay un proxy HTTPS (nginx, Apache, Caddy…)? | No. Por ahora se usará un DNS de pruebas | confirmado (Oscar, 2026-10-12) |
| ¿Quién gestiona el certificado HTTPS y cómo se renueva? | | pendiente |
| ¿El panel se abre desde internet o solo desde la red de Hermatix (o VPN)? | | pendiente |
| Puerto interno de la app (la guía: 8000, solo dentro del servidor) | | pendiente |

**Nota 2 · HTTPS es necesario para iniciar sesión.** En producción, la cookie de sesión lleva `Secure`
(lección 6): el navegador solo la envía por `https://`. Sin un proxy con certificado, el panel abriría la página
de login, pero **al entrar volvería al login** porque la cookie no viaja. Un DNS de pruebas hace que el nombre
llegue al servidor, pero **no da HTTPS**. Hace falta además un proxy con certificado (p. ej. nginx o Caddy con
un certificado gratuito de Let's Encrypt), y para el certificado el DNS de `sicop.hermatix.com` debe apuntar
a 2.25.81.33. La guía no permite quitar `Secure` en el servidor. Ver bloqueo en la sección 7.

## 5. Correo de los avisos

Primer envío real hecho el 2026-10-13 con autorización de Oscar (llegó a la bandeja, no a spam). Fuera de las
pruebas, los avisos quedan en modo prueba (`NOTIFICATIONS_DRY_RUN=true`) hasta activar el horario en la lección 9.

| Pregunta | Respuesta | Estado |
|---|---|---|
| Proveedor | API de Google (Gmail / Google Workspace) | confirmado (Oscar, 2026-10-12) |
| Remitente | licitaciones@hermatix.com | confirmado (Oscar, 2026-10-12) |
| Destinatarios | Anabelle y Oscar, al inicio. **Deben poder cambiarse** (ver nota 3) | confirmado (Oscar, 2026-10-12) |
| ¿Qué tipo de acceso a la API (cuenta de servicio, OAuth) y quién lo crea en Google? | OAuth de licitaciones@, solo `gmail.send`; cliente creado por Oscar (ver `docs/GOOGLE_API.md`) | confirmado (Oscar, 2026-10-13) |
| ¿Hay límites de envío del proveedor? | | pendiente |
| Quién coloca la credencial de Google en el servidor | Oscar | supuesto |
| Cuándo llega | Un solo resumen, de lunes a viernes a las 8:00 (hora de Costa Rica); nada si no hay oportunidades nuevas (ver nota 4) | confirmado (Oscar, 2026-10-13) |

**Nota 3 · Destinatarios que se cambian desde el panel (pedido de Oscar).** Oscar no quiere una lista fija de
correos en la configuración (`MAIL_TO`): quiere decidir quién recibe los avisos, cambiarlo con el tiempo y,
si se puede, hacerlo desde el panel. Es un requisito nuevo para la lección 7 (avisos). Decisiones pendientes:
qué usuarios del panel pueden cambiar la lista (hoy no hay roles) y si se guarda el historial de cambios.
Los correos de Anabelle y Oscar no se anotan aquí: se cargan en la app.
*Resuelto (lección 7):* solo los administradores editan «Destinatarios», con historial de cambios.

**Nota 4 · Horario del aviso (lección 9; no se activa hasta entonces y solo con instrucción explícita).** Un
temporizador de systemd, `deploy/systemd/sicop-cycle.timer`, ejecutará el ciclo completo
(`python -m app.cli run-cycle --origen real --dry-run`, lección 8; `--send` cuando se autorice) con
`OnCalendar=Mon..Fri *-*-* 08:00:00 America/Costa_Rica` y `Persistent=false` (si el servidor estaba apagado a
las 8:00, no se manda tarde). Pendiente para el encargo B: un cartel que cierra el sábado o domingo e importado
el viernes después de las 8:00 no se avisaría; revisarlo con Oscar. *Decidido 2026-10-16 (Ivania):* se trata
como cualquier otro cartel; aparece en el panel (`docs/OPERACION.md`, sección 3).

## 6. Dónde se guarda el código

Hoy el repositorio solo está en la computadora de Ivania (sin remoto). *Actualizado:* desde el 2026-10-16 está
en GitHub (`oscar041988/sicop-Connect`); se trabaja por ramas y Oscar une los pull request (nada directo a `main`).

| Pregunta | Respuesta | Estado |
|---|---|---|
| Servicio | GitHub, creado por Oscar; el código también queda en su Mac | confirmado (Oscar, 2026-10-12) |
| ¿Es privado? | Debe serlo (la guía pide un repositorio privado autorizado) | pendiente de confirmar |
| Quién tiene acceso | Oscar e Ivania (Ivania sube los commits revisados desde Windows) | supuesto |
| Cuándo se crea | **A más tardar el miércoles 14/10** (ver nota 5) | pendiente |

**Nota 5 · Cuándo crear el GitHub.** El primer paso del despliegue (jueves 15/10, lección 9) es subir el commit
revisado al repositorio; la guía pide repasarlo con Oscar el miércoles 14/10 (lección 8) porque «lo que falte
hoy, mañana bloquea». Lo ideal es crearlo el martes 13 o el miércoles 14 en la mañana, para probar con calma
que Ivania puede subir el código y Oscar descargarlo en su Mac. Le toma unos 30 minutos: crear la cuenta o la
organización de Hermatix, un repositorio **privado** e invitar a Ivania.

## 7. Bloqueos

| Bloqueo | Responsable | Fecha límite | Estado |
|---|---|---|---|
| Usuario SSH sin definir | Oscar | mié 14/10 | abierto (2026-10-13: sin confirmar; se ve mañana al empezar) |
| HTTPS: falta proxy con certificado y que el DNS de `sicop.hermatix.com` apunte a 2.25.81.33; sin HTTPS no se puede iniciar sesión (nota 2) | Oscar | mié 14/10 | abierto (2026-10-13: sin confirmar) |
| Repositorio privado en GitHub e invitación a Ivania (nota 5) | Oscar | mié 14/10 | resuelto según Oscar (2026-10-13); se comprueba con el `git push` de 9.1 |
| Python: comprobar la versión instalada antes de descargar otra (nota 1) | Oscar | mié 14/10 | resuelto según Oscar (2026-10-13: 3.12 o más); anotar la versión exacta en 9.3 |
| Acceso a la API de Google para enviar desde licitaciones@hermatix.com | Oscar | mar 13/10 (lección 7, paso 3) | resuelto (2026-10-13: primer envío real llegó a la bandeja) |
| Cómo pasar al servidor los JSON de Google (9.4) | Oscar | jue 15/10, antes de 9.6 | abierto (no se habló el 13/10) |
| Respaldos en el servidor: destino en otro disco, retención (D8) y si hay uno diario (9.7) | Oscar | jue 15/10 | abierto (no se habló el 13/10) |

## 8. Registro de la reunión

- Fecha: 2026-10-12
- Participantes: Ivania, Oscar
- Resumen: servidor Ubuntu 24.04 alquilado (Hostinger), sale a internet, IP 2.25.81.33, dirección
  https://sicop.hermatix.com. Sin proxy por ahora (DNS de pruebas). Usuario `sicop` sin privilegios y las 3
  rutas de la guía aceptadas. Correo con la API de Google desde licitaciones@hermatix.com, para Anabelle y Oscar, con
  destinatarios que se puedan cambiar desde el panel. Código en un GitHub que crea Oscar.
- Próximo paso: Oscar resuelve los bloqueos de la sección 7 antes del miércoles 14/10.

## 9. Pasos de instalación, por terminal (guía 17.2–17.7)

Preparado en la lección 8, encargo B (2026-10-13). Se ejecuta en la lección 9, **solo con Oscar presente**.

**Antes de cada comando, Ivania dice en voz alta en qué máquina está.** Después de `ssh`, la terminal de la Mac se
ve igual, pero lo que se escribe pasa en el servidor. Cada bloque dice dónde va:

- 🪟 **WINDOWS**: la computadora de Ivania (PowerShell).
- 🍎 **MAC**: la terminal local de la Mac de Oscar.
- 🐧 **SERVIDOR**: la terminal de la Mac **después** de `ssh`.

**Marcadores.** Lo que va en MAYÚSCULAS se reemplaza al momento por el dato real. Los datos que no son secretos
se anotan en el acta; los secretos (contraseñas, llaves, `SESSION_SECRET`, los JSON de Google) **nunca** se
escriben aquí, en el chat ni en el acta.

| Marcador | Qué es | Quién lo da |
|---|---|---|
| `URL_REPOSITORIO` | Dirección del repositorio privado de GitHub | Oscar (bloqueo, sección 7) |
| `NOMBRE_RAMA` | Rama que se sube (hoy se trabaja en `desarrollo`; al servidor va lo unido a `main`) | Ivania |
| `COMMIT_REVISADO` | Hash completo del commit revisado (`git rev-parse HEAD`) | Ivania |
| `USUARIO_SSH` | Usuario con el que Oscar entra al servidor | Oscar (bloqueo, sección 7) |
| `HOST_SERVIDOR` | IP o nombre del servidor (sección 1) | Oscar |
| `DOMINIO_DEL_PANEL` | Dirección HTTPS del panel, sin `https://` (sección 4) | Oscar |
| `RUTA_RESPALDO` | Carpeta de respaldos en **otro disco** u otro equipo | Oscar (pendiente, D8) |
| `CORREO_ADMIN` | Correo del primer usuario administrador del panel | Oscar |

### 9.1 🪟 WINDOWS — publicar el commit revisado (guía 17.2, paso 1)

```powershell
cd C:\Users\User\sicop-connect
git status                      # debe decir «nothing to commit, working tree clean»
git log -1 --oneline
git rev-parse HEAD              # anotar: es COMMIT_REVISADO
python -m pytest -q             # anotar el resultado («N passed»)
git remote add origin URL_REPOSITORIO   # solo la primera vez
git push -u origin NOMBRE_RAMA
```

Comprobar que **no** se suben `.env`, `.venv`, `data/`, bases, respaldos ni secretos: están en `.gitignore`
y `git status` no los muestra.

### 9.2 🍎 MAC — obtener, empaquetar y transferir (guía 17.2, pasos 2–4)

```bash
git --version && ssh -V
git clone URL_REPOSITORIO sicop-connect     # o, si ya existe: cd sicop-connect && git fetch origin
cd sicop-connect
git checkout COMMIT_REVISADO
git rev-parse HEAD                           # debe ser igual al de Windows
git archive --format=tar.gz --output=../sicop-connect-release.tar.gz COMMIT_REVISADO
shasum -a 256 ../sicop-connect-release.tar.gz    # anotar el hash del paquete
scp ../sicop-connect-release.tar.gz USUARIO_SSH@HOST_SERVIDOR:/tmp/sicop-connect-release.tar.gz
ssh USUARIO_SSH@HOST_SERVIDOR
```

`git archive` escribe el commit dentro de `app/COMMIT` (ver `.gitattributes`). Así el servidor sabe qué
versión tiene, aunque no tenga git, y cada respaldo lo anota en su manifiesto.

### 9.3 🐧 SERVIDOR — verificar e instalar (guía 17.2, paso 5)

```bash
hostname && whoami                                   # ¿es el servidor correcto?
sha256sum /tmp/sicop-connect-release.tar.gz          # debe ser igual al de la Mac
python3 --version                                    # se necesita 3.12 o más (nota 1)
sudo apt install python3.12-venv                     # solo si el paso siguiente dice que falta venv
```

El administrador crea el usuario de servicio sin privilegios y las carpetas (sección 3):

```bash
sudo useradd --system --home-dir /var/lib/sicop-connect --shell /usr/sbin/nologin sicop
sudo install -d -o sicop -g sicop -m 750 /opt/sicop-connect /var/lib/sicop-connect \
     /var/lib/sicop-connect/raw /var/lib/sicop-connect/incoming /var/lib/sicop-connect/exports
sudo install -d -o sicop -g sicop -m 700 /etc/sicop-connect
```

Primera instalación del código:

```bash
sudo tar -xzf /tmp/sicop-connect-release.tar.gz -C /opt/sicop-connect
sudo chown -R sicop:sicop /opt/sicop-connect
cd /opt/sicop-connect
cat app/COMMIT                                       # debe ser COMMIT_REVISADO
sudo -u sicop python3 -m venv .venv
sudo -u sicop .venv/bin/python -m pip install -r requirements.lock.txt
```

Nunca se ejecuta la app como root ni con `--reload` en el servidor.

**Solo si se va a activar la obtención automática** (`SOURCE_MODE=auto`): falta el navegador de Playwright. Se
instala para el usuario `sicop` (queda en su carpeta, `/var/lib/sicop-connect`):

```bash
sudo -u sicop .venv/bin/python -m playwright install chromium
sudo .venv/bin/python -m playwright install-deps chromium   # bibliotecas del sistema que pida Chromium
```

*Pendiente de verificar en el servidor:* no se ha probado en Ubuntu; la obtención automática solo se probó en
Windows. La activación completa (06:30 y 14:00, correo de avisos a las 8:00) está en 9.9.

### 9.4 🐧 SERVIDOR — configuración privada (guía 17.3)

El administrador crea `/etc/sicop-connect/app.env` (propietario `sicop`, permisos `600`). Lo escribe él, en el
servidor:

```bash
sudo -u sicop nano /etc/sicop-connect/app.env
sudo chmod 600 /etc/sicop-connect/app.env
```

Contenido. Al principio todo queda **sin envíos**:

```ini
APP_ENV=production
APP_TIMEZONE=America/Costa_Rica
DATABASE_PATH=/var/lib/sicop-connect/sicop.db
RAW_DATA_DIR=/var/lib/sicop-connect/raw
INCOMING_DIR=/var/lib/sicop-connect/incoming
EXPORTS_DIR=/var/lib/sicop-connect/exports
APP_BASE_URL=https://DOMINIO_DEL_PANEL
SOURCE_MODE=manual
AI_MODE=none
NOTIFICATIONS_ENABLED=false
NOTIFICATIONS_DRY_RUN=true
SCHEDULER_ENABLED=false
MAIL_PROVIDER=unconfigured
MAIL_FROM=
SESSION_SECRET=
GOOGLE_CLIENT_FILE=/etc/sicop-connect/google_cliente.json
GOOGLE_TOKEN_FILE=/etc/sicop-connect/google_token.json
```

- `SESSION_SECRET`: el administrador lo genera **en el servidor** y lo pega en el archivo, sin mostrarlo a nadie:
  `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `EXPORTS_DIR` y `APP_BASE_URL` no están en la lista de la guía. Hacen falta para que la vista previa no quede
  dentro del código y para que los enlaces de los correos apunten al panel real, no a `127.0.0.1`.
- No se rellenan valores ficticios para que `doctor` «salga bien» (guía 17.3).
- **Variables agregadas después de la instalación** (todas tienen un valor por defecto seguro; ver
  `.env.example`): `NOTIFY_LOOKBACK_DAYS=7`, `NOTIFY_CLOSING_DAYS=3` (A4), `SESSION_MAX_AGE_HOURS=8`,
  `UPLOAD_MAX_MB=25`. Solo para la obtención automática: `SICOP_REQUEST_EMAIL`, `GOOGLE_READ_TOKEN_FILE`,
  `OBTAIN_CODE_TIMEOUT_MIN`, `OBTAIN_LINK_MAX_HOURS`, `OBTAIN_POLL_MINUTES`, `OBTAIN_REQUEST_HOUR` y
  `OBTAIN_ALERT_TO`; mientras `SOURCE_MODE=manual`, no hacen falta.
- **Archivos de Google** (`docs/GOOGLE_API.md`). El servidor no tiene navegador, así que `google-auth` no se puede
  correr ahí: se copian el JSON del cliente y el token ya autorizado de licitaciones@, que hoy están en
  `C:\Users\User\secretos-sicop\`. Oscar decide cómo pasarlos (por ejemplo, `scp` directo); **nunca** por correo
  ni chat. En el servidor: propietario `sicop`, permisos `600`. El token debe poder escribirlo `sicop`, porque la
  app lo renueva.

**Base inicial: decidido con Oscar (2026-10-13): la de Windows**, con un respaldo nuevo hecho justo antes de
subir (el de prueba es `sicop_20261013-151951`). Las opciones eran:

- **Vacía:** se empieza de cero, con usuarios y destinatarios nuevos.
- **La de Windows:** conserva las revisiones, los usuarios, los destinatarios y lo ya avisado. Se lleva con un
  respaldo (9.7): en Windows, `python -m app.cli backup --output C:\Users\User\respaldos-sicop`; se copian el
  `.db` y su `.json`; en el servidor se compara `sha256sum` con el del manifiesto y se coloca como
  `/var/lib/sicop-connect/sicop.db` (propietario `sicop`, permisos `600`).

### 9.5 🐧 SERVIDOR — servicios, migración y arranque (guía 17.4–17.5)

Las cuatro unidades están en el paquete, en `deploy/systemd/`. Cambios respecto a la guía:

- El ciclo lleva `--origen real`.
- El horario es de lunes a viernes a las 8:00 de Costa Rica, con `Persistent=false` (decisión de Oscar, nota 4).
  La guía decía todos los días a las 07:00 con `Persistent=true`.

```bash
sudo cp /opt/sicop-connect/deploy/systemd/sicop-* /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/sicop-*.service /etc/systemd/system/sicop-cycle.timer
sudo systemctl daemon-reload
sudo systemctl start sicop-migrate.service && sudo systemctl status sicop-migrate.service
sudo journalctl -u sicop-migrate.service -n 20 --no-pager    # «inactive» al terminar es normal: mirar el resultado
sudo systemctl enable --now sicop-web.service
curl -f http://127.0.0.1:8000/health
```

Un comando de la CLI con **la misma configuración que el servicio**, sin imprimir secretos. Este es el patrón
para `doctor`, `create-user`, `import`, `backup`…:

```bash
sudo systemd-run --uid=sicop --pty --wait \
  -p EnvironmentFile=/etc/sicop-connect/app.env \
  -p WorkingDirectory=/opt/sicop-connect \
  /opt/sicop-connect/.venv/bin/python -m app.cli doctor
```

Primer administrador: el mismo patrón, con `-m app.cli create-user --email CORREO_ADMIN --rol admin`. La
contraseña la escribe esa persona; no se muestra.

El administrador configura en el proxy el dominio `DOMINIO_DEL_PANEL`, HTTPS y quién puede entrar (nota 2).
Desde otra computadora: iniciar sesión, ver la lista, guardar una revisión. Alguien sin sesión no ve datos.

### 9.6 🐧 SERVIDOR — activar el ciclo, en este orden (guía 17.5)

1. Ciclo en dry-run, a mano: `sudo systemctl start sicop-cycle.service`. Revisar
   `sudo journalctl -u sicop-cycle.service -n 50 --no-pager` y la vista previa en `/var/lib/sicop-connect/exports`.
   Si `INCOMING_DIR` está vacío, el ciclo termina en «fallo · no llegó ningún archivo nuevo». Es lo correcto.
2. **Con autorización de Oscar**, el administrador cambia en `app.env`:
   - `NOTIFICATIONS_ENABLED=true`
   - `NOTIFICATIONS_DRY_RUN=false`
   - `SCHEDULER_ENABLED=true`
   - `MAIL_PROVIDER=gmail_api`
   - `MAIL_FROM=` con el remitente (sección 5)
3. En `/etc/systemd/system/sicop-cycle.service`, cambiar `--dry-run` por `--send`.
4. `sudo systemctl daemon-reload` y un ciclo supervisado: `sudo systemctl start sicop-cycle.service`.
5. Verificar que el correo llegó a la bandeja (no solo «aceptado»).
6. Habilitar el horario:
   ```bash
   sudo systemctl enable --now sicop-cycle.timer
   sudo systemctl list-timers sicop-cycle.timer       # debe mostrar el próximo lunes a viernes 08:00
   ```

La obtención sigue siendo manual: alguien de Hermatix descarga de SICOP y deja los archivos en `INCOMING_DIR` o
los sube desde el panel, **antes de las 8:00**. El timer hace todo lo demás.

### 9.7 Respaldo y restauración (guía 17.6–17.7)

`backup --output CARPETA` usa la API de backup de SQLite (una foto coherente aunque la base esté en uso) y
deja dos archivos, que nunca se sobrescriben:

- `sicop_AAAAMMDD-HHMMSS.db`: la copia.
- `sicop_AAAAMMDD-HHMMSS.json`: el manifiesto, con la fecha, el commit, la versión del esquema, el SHA-256, la
  integridad y las filas por tabla.

🪟 **WINDOWS**, ensayo de la lección 8, paso 4:

```powershell
python -m app.cli backup --output C:\Users\User\respaldos-sicop
Get-FileHash C:\Users\User\respaldos-sicop\sicop_AAAAMMDD-HHMMSS.db    # igual al "sha256" del .json
```

🐧 **SERVIDOR**, mismo patrón de `systemd-run`, con `-m app.cli backup --output RUTA_RESPALDO`. Pendiente con
Oscar:

- El destino debe estar en **otro disco** u otro equipo.
- La retención (D8).
- Un respaldo diario automático.

**Restaurar:**

1. Detener el timer y el panel.
2. Comprobar el SHA-256 contra el manifiesto.
3. Copiar el `.db` como `DATABASE_PATH`, con propietario `sicop` y permisos `600`.
4. Arrancar `sicop-migrate.service` y luego `sicop-web.service`.
5. Abrir una revisión conocida.

Volver al código anterior **no** revierte una migración: si el esquema cambió, también se restaura la base.

### 9.8 Actualizar y revertir (guía 17.6)

1. Anotar el commit actual (`cat /opt/sicop-connect/app/COMMIT`) y la versión del esquema (`doctor`).
2. Hacer un respaldo (9.7).
3. `sudo systemctl stop sicop-cycle.timer`. El panel también, si la migración lo exige.
4. Instalar el paquete nuevo en `/opt/sicop-connect-NUEVA` (9.2 y 9.3) y apuntar los servicios a esa carpeta.
5. Correr `sicop-migrate`, revisar `/health` y una oportunidad conocida.
   - Si el lock cambió: `pip install -r requirements.lock.txt` en el entorno de la carpeta nueva.
   - Después de `migrate`, correr **`evaluate`** con el patrón de `systemd-run` (9.5): desde la migración 0008
     el panel pide una evaluación completa, y si las reglas cambiaron, la vigente es la de la última `evaluate`.
6. Reiniciar `sicop-web` y reactivar el timer.

**Si falla:** desactivar el timer, volver a la carpeta anterior y, si el esquema cambió, restaurar el respaldo
del paso 2.

**Registros:** `sudo journalctl -u sicop-web.service -n 100 --no-pager` y lo mismo con `sicop-cycle.service`.
Cada ciclo también queda en `source_runs` (número de ciclo, estado y cobertura).

### 9.9 🐧 SERVIDOR — activar la obtención (06:30 y 14:00) y el correo de avisos de las 8:00 (para Oscar)

Decidido (2026-10-26, Oscar por Ivania): dos solicitudes por día a las **06:30 y 14:00**, **descarga a mano** (SICOP
bloquea la descarga hecha por el programa) con un **recordatorio** por correo, **evaluación al subir** el ZIP en el
panel y **envío real** de los avisos **solo a las 8:00**. Lo hace el administrador del servidor, en este orden. Se
habilitan **los dos** timers: `sicop-obtain.timer` (pide el reporte) y `sicop-cycle.timer` (el correo de las 8:00).

**Cómo queda el día (lunes a viernes):** 06:30 la app pide el reporte y escribe el código sola → llega el correo
«Envío de reporte» (de 2 a 50 min) → la app manda el recordatorio a `OBTAIN_ALERT_TO` → una persona baja el ZIP y lo
sube en «Cargar archivo», que lo **importa y evalúa** al momento → **08:00** el ciclo manda el correo de avisos con
todo lo subido desde el anterior. A las 14:00 se pide otro reporte; lo que se suba entra en el correo del día
siguiente. Si algo falla, llega la alerta con el plan B.

1. **Respaldo** (9.7) y anotar el commit y el esquema actuales (9.8, paso 1).
2. **Código nuevo** (9.8, pasos 3–5) y `sicop-migrate`: aplica la **0016** (baja de usuarios) y la **0017** (dos
   turnos). `doctor` debe decir esquema 0017. Después, `evaluate` (9.8, paso 5).
3. **Navegador de Playwright** (si no se hizo en 9.3):
   ```bash
   sudo -u sicop /opt/sicop-connect/.venv/bin/python -m playwright install chromium
   sudo /opt/sicop-connect/.venv/bin/python -m playwright install-deps chromium
   ```
4. **Permiso de lectura de Gmail** (`docs/GOOGLE_API.md`): `obtain gmail-auth` necesita un navegador, así que se
   hace en una PC, entrando como el buzón de SICOP (licitaciones@), y el token se copia al servidor como el de
   enviar (9.4): `/etc/sicop-connect/google_read_token.json`, propietario `sicop`, permisos `600`. Es **otro**
   archivo que `google_token.json`.
5. **`app.env`** (`sudo -u sicop nano /etc/sicop-connect/app.env`), además de lo de 9.4:
   ```ini
   SOURCE_MODE=auto
   OBTAIN_REQUEST_HOUR=06:30,14:00
   OBTAIN_DOWNLOAD=manual
   SICOP_REQUEST_EMAIL=        # el buzón donde llegan los correos de SICOP
   GOOGLE_READ_TOKEN_FILE=/etc/sicop-connect/google_read_token.json
   OBTAIN_ALERT_TO=            # quién recibe el recordatorio y las alertas
   NOTIFICATIONS_ENABLED=true
   NOTIFICATIONS_DRY_RUN=false
   SCHEDULER_ENABLED=true
   MAIL_PROVIDER=gmail_api
   MAIL_FROM=                  # el remitente de los avisos (sección 5)
   ```
   Revisar con `doctor` (patrón de `systemd-run`, 9.5): no muestra los valores sensibles.
6. **Unidades** (`sicop-cycle.service` ya trae `--send`; `sicop-obtain.*` son nuevas):
   ```bash
   sudo cp /opt/sicop-connect/deploy/systemd/sicop-* /etc/systemd/system/
   sudo systemd-analyze verify /etc/systemd/system/sicop-*.service /etc/systemd/system/sicop-*.timer
   sudo systemctl daemon-reload
   ```
7. **Una vuelta supervisada**, a la hora que sea (antes de las 06:30 no pide nada; después, pide el turno vigente):
   ```bash
   sudo systemctl start sicop-obtain.service
   sudo journalctl -u sicop-obtain.service -n 50 --no-pager
   ```
   Lo esperado: «Solicitud #N (turno de las …) hecha» y, en otra vuelta, «Llegó el correo «Envío de reporte»» y
   «Recordatorio … enviado». Una vuelta sin nada que hacer termina con código 0. Si dice FALLO, leer el motivo
   antes de seguir: no habilitar el timer con un FALLO sin entender.
8. **Subir el ZIP en el panel** y ver que la página muestra «Evaluación» y los carteles en el panel. Después, **un
   ciclo supervisado** (manda el correo de avisos de verdad):
   ```bash
   sudo systemctl start sicop-cycle.service
   sudo journalctl -u sicop-cycle.service -n 50 --no-pager
   ```
   Verificar que el correo llegó a la bandeja (no solo «aceptado»).
9. **Habilitar los dos horarios:**
   ```bash
   sudo systemctl enable --now sicop-obtain.timer sicop-cycle.timer
   sudo systemctl list-timers 'sicop-*'   # obtain: cada 15 min de 06:00 a 19:45 · cycle: 08:00, lunes a viernes
   ```

**Pausar la obtención:** `sudo systemctl disable --now sicop-obtain.timer` (o `SOURCE_MODE=manual` en `app.env`: la
vuelta no hace nada). **Pausar los avisos:** `sudo systemctl disable --now sicop-cycle.timer`. **Seguir en vista
previa:** cambiar `--send` por `--dry-run` en `sicop-cycle.service` y `daemon-reload`.
