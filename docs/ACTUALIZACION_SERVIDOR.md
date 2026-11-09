# Actualización del servidor: de `02b569b` a `desarrollo` (preparada el 2026-11-09)

Preparada por Ivania con Claude. **Se hace con Oscar presente**, un día hábil **después de las 8:00** (el correo
del día ya salió) y con tiempo para revertir. Nada de esto se ha ejecutado todavía.

## Qué cambia

| | Hoy en el servidor | Después |
|---|---|---|
| Código | `02b569b` (15/10) | lo unido a `main` desde `desarrollo` (219 commits) |
| Esquema de la base | 0007 | **0040** |
| Base de datos | la del servidor (vieja) | **la base local de Ivania** (decisión de Ivania, 2026-11-09): trae todo lo hecho desde el 21/10 |
| Ciclo de las 8:00 (avisos) | — | **en el servidor** (`sicop-cycle.timer`); se apaga la tarea de Windows |
| Enriquecimiento de las 10:00 (navegador) | tarea de Windows | **en pausa** hasta la fase 2 (`docs/ENVIO_ENRIQUECIMIENTO.md`) |
| Cola de resúmenes con IA | tarea de Windows, después del enriquecimiento | **en el servidor** (`sicop-ia-cola.timer`, 10:45) |
| Paquetes nuevos | — | `playwright`, `openpyxl`, `pdfplumber`, `openai` (en `requirements.lock.txt`) |

**Por qué se pausa el enriquecimiento:** corre en la PC de Ivania (necesita un navegador con ventana) y guarda en
su base. Con la base en el servidor, lo que guarde ya no llegaría al panel. El envío PC → servidor con token es la
**fase 2** (`docs/ENVIO_ENRIQUECIMIENTO.md`), en construcción. Mientras tanto, los carteles nuevos se ven en el
panel, se evalúan y se avisan, pero sin ficha de SICOP ni documentos. La **cola de IA** no usa navegador: pasa al
servidor desde el primer día y resume lo que ya tiene documentos.

**Revisado (2026-11-09):** la base local guarda todas las rutas de archivos como relativas a su carpeta y con `/`
(documentos, expedientes, perfil, asistente, reportes): funciona igual en el servidor. Suite completa con
**Python 3.12** (el del servidor es 3.12.3) en un entorno limpio con `requirements-dev.txt`: el resultado está en
`ESTADO_PROYECTO.md`.

## Marcadores

Los de `docs/DESPLIEGUE.md` §9 (`USUARIO_SSH`, `HOST_SERVIDOR`, `URL_REPOSITORIO`, `RUTA_RESPALDO`…), más:

| Marcador | Qué es |
|---|---|
| `COMMIT_REVISADO` | el commit de `main` después de unir el PR (`git rev-parse HEAD`) |
| `RESPALDO_LOCAL` | el nombre que da `backup` en Windows, `sicop_AAAAMMDD-HHMMSS` |

Los secretos (clave de OpenAI, `SESSION_SECRET`, JSON de Google) **nunca** se escriben aquí, en un chat ni en el
acta.

## 0. Antes del día

- [ ] **Oscar une el PR** `desarrollo → main` (texto en `docs/PR_DESARROLLO.md`). Anotar `COMMIT_REVISADO`.
- [ ] **Decidir con Oscar** los valores que no son secretos de la sección 5: `IA_PROMPT_VERSION` (v8 si aprobó el
      reporte con la explicación; si no, la que use hoy el `.env` de Ivania), `OPENAI_MODEL` y los precios,
      `OBTAIN_ALERT_TO`, y si ese día se activa también la obtención automática (`docs/DESPLIEGUE.md` §9.9; hoy no).
- [ ] Confirmar que en el servidor ya están `/etc/sicop-connect/google_cliente.json` y `google_token.json`
      (§9.4). Sin ellos no salen los correos.

## 1. 🪟 WINDOWS — congelar la PC (el día del cambio)

Desde aquí, nada escribe en la base local: es la que se va a llevar.

```powershell
Disable-ScheduledTask -TaskName "SICOP CONNECT - ciclo diario"      # si no, los avisos saldrían dos veces
Disable-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento"
Get-ScheduledTask -TaskName "SICOP CONNECT*" | Select-Object TaskName, State    # los dos: Disabled
```

- Cerrar el panel local (Ctrl+C en la ventana de `uvicorn`).
- En el `.env` local, `ENRICH_ENABLED=false` (lo cambia Ivania).

## 2. 🪟 WINDOWS — respaldo final y paquete de datos

```powershell
cd C:\Users\User\sicop-connect
.\.venv\Scripts\Activate.ps1
python -m app.cli backup --output C:\Users\User\respaldos-sicop
# Deja RESPALDO_LOCAL.db, .json (manifiesto con SHA-256 y esquema 0039) y los ZIP _documentos, _expedientes,
# _perfil, _asistente y _reportes.
Compress-Archive -Path data\raw\* -DestinationPath C:\Users\User\respaldos-sicop\RESPALDO_LOCAL_raw.zip
Compress-Archive -Path app\web\static\ayuda\* -DestinationPath C:\Users\User\respaldos-sicop\RESPALDO_LOCAL_ayuda.zip
```

- `_raw.zip`: las copias originales de cada archivo importado (para auditoría).
- `_ayuda.zip`: las capturas de las misiones de ayuda. No están en Git; sin ellas, la ayuda del servidor sale sin
  imágenes. (Otra opción: generarlas en el servidor con `ayuda capturas`, paso 9.)
- **No** se llevan `data\grabaciones` (1,7 GB, solo del enriquecimiento) ni `data\incoming`.
- `_perfil.zip` y `_asistente.zip` son **confidenciales**. Oscar decide cómo pasan al servidor (por ejemplo `scp`
  desde la Mac); nunca por correo, chat ni una carpeta compartida pública.

## 3. 🍎 MAC — paquete de código y transferencia

Igual que `docs/DESPLIEGUE.md` §9.2, con `COMMIT_REVISADO`: `git archive` → `shasum -a 256` (anotar) → `scp` a
`/tmp/sicop-connect-release.tar.gz`. Los archivos del paso 2 van a `/tmp/sicop-datos/` en el servidor, junto con
el `.json` del manifiesto.

## 4. 🐧 SERVIDOR — anotar y respaldar lo de hoy

```bash
hostname && whoami
cat /opt/sicop-connect/app/COMMIT                    # debe ser 02b569b…: anotarlo
sha256sum /tmp/sicop-connect-release.tar.gz          # igual al de la Mac
sha256sum /tmp/sicop-datos/RESPALDO_LOCAL.db         # igual al "sha256" del .json
```

Respaldo de la base vieja con el patrón de `systemd-run` (§9.5), `-m app.cli backup --output RUTA_RESPALDO`.
Guardar también las unidades de hoy:

```bash
sudo install -d -m 700 /root/sicop-antes
sudo cp -a /etc/systemd/system/sicop-* /root/sicop-antes/
```

## 5. 🐧 SERVIDOR — parar, instalar el código nuevo y las carpetas

```bash
sudo systemctl stop sicop-web.service
sudo systemctl stop sicop-cycle.timer sicop-obtain.timer     # si alguno no existe, el aviso no importa
sudo mv /opt/sicop-connect /opt/sicop-connect-02b569b         # la versión de hoy queda entera, para revertir
sudo install -d -o sicop -g sicop -m 750 /opt/sicop-connect
sudo tar -xzf /tmp/sicop-connect-release.tar.gz -C /opt/sicop-connect
sudo chown -R sicop:sicop /opt/sicop-connect
cd /opt/sicop-connect && cat app/COMMIT                      # debe ser COMMIT_REVISADO
sudo -u sicop python3 -m venv .venv
sudo -u sicop .venv/bin/python -m pip install -r requirements.lock.txt
sudo -u sicop .venv/bin/python -m playwright install chromium            # la obtención y las capturas de la ayuda
sudo .venv/bin/python -m playwright install-deps chromium
```

El `.venv` se crea en la carpeta final: un entorno virtual no se puede mover de carpeta.

Carpetas nuevas (las de los documentos de Hermatix, solo para `sicop`):

```bash
sudo install -d -o sicop -g sicop -m 750 /var/lib/sicop-connect/documentos /var/lib/sicop-connect/expedientes \
     /var/lib/sicop-connect/reportes /var/lib/sicop-connect/grabaciones
sudo install -d -o sicop -g sicop -m 700 /var/lib/sicop-connect/perfil /var/lib/sicop-connect/asistente
```

## 6. 🐧 SERVIDOR — la base y los datos de Ivania

```bash
cd /tmp/sicop-datos
sudo mv /var/lib/sicop-connect/sicop.db /var/lib/sicop-connect/sicop-02b569b.db    # la vieja, para revertir
sudo install -o sicop -g sicop -m 600 RESPALDO_LOCAL.db /var/lib/sicop-connect/sicop.db
for c in documentos expedientes perfil asistente reportes raw; do
  sudo python3 -m zipfile -e RESPALDO_LOCAL_$c.zip /var/lib/sicop-connect/$c
done
sudo python3 -m zipfile -e RESPALDO_LOCAL_ayuda.zip /opt/sicop-connect/app/web/static/ayuda
sudo chown -R sicop:sicop /var/lib/sicop-connect /opt/sicop-connect/app/web/static/ayuda
```

Se descomprime como `root` (los archivos llegaron con el usuario de `scp`) y el `chown` los deja de `sicop`. Si un
ZIP no existe (la carpeta estaba vacía), ese paso da error y se sigue. Al terminar, borrar `/tmp/sicop-datos`
(`sudo rm -r /tmp/sicop-datos`): tiene documentos confidenciales.

## 7. 🐧 SERVIDOR — `app.env`

`sudo -u sicop nano /etc/sicop-connect/app.env`. Se **agrega** lo que falta; lo de §9.4 (base, `raw`, `incoming`,
`exports`, `SESSION_SECRET`, Google) se queda. Valores para el servidor:

```ini
# Carpetas de datos
DOCUMENTS_DIR=/var/lib/sicop-connect/documentos
EXPEDIENTES_DIR=/var/lib/sicop-connect/expedientes
PROFILE_DOCS_DIR=/var/lib/sicop-connect/perfil
ASSISTANT_DOCS_DIR=/var/lib/sicop-connect/asistente
REPORTS_DIR=/var/lib/sicop-connect/reportes
RECORDINGS_DIR=/var/lib/sicop-connect/grabaciones
APP_BASE_URL=https://sicop.hermatix.com
# Navegador: el servidor no tiene pantalla
BROWSER_HEADLESS=true
# Enriquecimiento: en pausa hasta la fase 2
ENRICH_ENABLED=false
ENRICH_EMAILS=false
# Asistente de elegibilidad (encendido en local desde el 4/11); los documentos de Hermatix no van a la IA
ASSISTANT_ENABLED=true
ASSISTANT_SEND_DOCUMENTS=false
# IA (DECISION_IA.md). La clave la escribe Oscar, en persona.
AI_MODE=openai
OPENAI_API_KEY=
OPENAI_MODEL=
IA_PRECIO_ENTRADA_USD=
IA_PRECIO_SALIDA_USD=
IA_PROMPT_VERSION=
IA_MAX_DAILY_COST=1.00
# Avisos de las 8:00 desde el servidor (la tarea de Windows ya está apagada)
NOTIFICATIONS_ENABLED=true
NOTIFICATIONS_DRY_RUN=false
SCHEDULER_ENABLED=true
MAIL_PROVIDER=gmail_api
MAIL_FROM=
OBTAIN_ALERT_TO=
```

- Lo que falte toma el valor por defecto de `.env.example` (tamaños máximos, días, topes de la cola).
- `MAIL_FROM`, `OPENAI_MODEL`, precios, `IA_PROMPT_VERSION` y `OBTAIN_ALERT_TO`: los de la sección 0.
- `BROWSER_HEADLESS=true` cambia la regla «con ventana» del 27/10, que era para la PC de Ivania; en el servidor no
  hay pantalla. Solo lo usan la obtención (si se activa) y las capturas de la ayuda.
- **Nota:** las unidades (`sicop-cycle.service`) mandan con `--send`. Si se quiere un primer día en vista previa,
  `NOTIFICATIONS_DRY_RUN=true` y el ciclo no envía nada.

## 8. 🐧 SERVIDOR — unidades, migración y arranque

```bash
sudo cp /opt/sicop-connect/deploy/systemd/sicop-* /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/sicop-*.service /etc/systemd/system/sicop-*.timer
sudo systemctl daemon-reload
sudo systemctl start sicop-migrate.service
sudo journalctl -u sicop-migrate.service -n 20 --no-pager    # la base local llega en 0039: aplica la 0040
```

Con el patrón de `systemd-run` (§9.5):

- `-m app.cli doctor` → «Base de datos: ok», avisos habilitados, Gmail con el cliente y el token, programador
  habilitado y «Pendientes: ninguno». No muestra secretos.
- `-m app.cli evaluate` → evalúa todos los carteles con las reglas del paquete (las mismas de la base: no debería
  cambiar nada).

```bash
sudo systemctl start sicop-web.service
curl -f http://127.0.0.1:8000/health
```

## 9. Verificar en el navegador (https://sicop.hermatix.com)

- [ ] Entrar con un usuario de los de la base local (los mismos de Ivania; las contraseñas viajan en la base).
- [ ] El panel muestra los carteles de hoy; abrir uno conocido (por ejemplo `20261100575`, paradas de Siquirres):
      franja, pestañas, «Condiciones» y «Documentos» con sus archivos.
- [ ] «Reporte PDF» de un cartel con resumen: se descarga.
- [ ] «Perfil»: los documentos se ven y se descargan (y queda el registro).
- [ ] «Seguimiento», un expediente con sus archivos.
- [ ] «Ayuda»: las misiones con sus capturas. Si salen sin imágenes, generarlas en el servidor con el patrón de
      `systemd-run`, `-m app.cli ayuda capturas` (usa una base de EJEMPLO en `/opt/sicop-connect/data/ayuda_ejemplo`).
- [ ] «Avisos» y «Destinatarios»: los mismos que en local.

## 10. 🐧 SERVIDOR — el ciclo de las 8:00

Un ciclo supervisado **en vista previa**, sin enviar (patrón de `systemd-run`):
`-m app.cli run-cycle --origen real --dry-run`. Revisar la salida: destinatarios activos y lo que se habría
avisado. Después:

```bash
sudo systemctl enable --now sicop-cycle.timer sicop-ia-cola.timer
sudo systemctl list-timers 'sicop-*'                 # cycle: lunes a viernes 08:00 · ia-cola: 10:45
```

**Al día siguiente:** comprobar que el correo de las 8:00 llegó **una sola vez** (si llega doble, la tarea de
Windows sigue encendida).

## Si algo falla: revertir

```bash
sudo systemctl stop sicop-web.service sicop-cycle.timer
sudo mv /opt/sicop-connect /opt/sicop-connect-fallida && sudo mv /opt/sicop-connect-02b569b /opt/sicop-connect
sudo mv /var/lib/sicop-connect/sicop.db /var/lib/sicop-connect/sicop-fallida.db
sudo mv /var/lib/sicop-connect/sicop-02b569b.db /var/lib/sicop-connect/sicop.db
sudo cp -a /root/sicop-antes/sicop-* /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl start sicop-web.service
```

Y en Windows, `Enable-ScheduledTask` para las dos tareas: la PC vuelve a ser la principal, con su base intacta.

## 11. Enriquecimiento desde la PC (fase 2, `docs/ENVIO_ENRIQUECIMIENTO.md`)

Construido el 2026-11-09. Se puede hacer el mismo día, después del paso 10, o días después. Hasta entonces el
enriquecimiento queda en pausa (pasos 1 y 7).

1. 🐧 **El token.** El administrador lo genera en el servidor, sin mostrarlo:
   `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`, y lo agrega a `app.env` como
   `ENRICH_TOKEN=…`. Después, `sudo systemctl restart sicop-web.service`. Sin token, las direcciones
   `/api/enriquecimiento/…` no existen.
2. 🐧 **Comprobar** desde el servidor que pide el token (sin token: 401):
   `curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/api/enriquecimiento/corridas` → `401`.
3. 🪟 **La PC:** el `.env`, una corrida supervisada con `--max 1` y la tarea con `-Remoto`, como dice
   `deploy/windows/README.md`, sección «Fase 2». El token pasa del servidor a la PC **en persona** (nunca por correo,
   chat ni Claude).
4. **Verificar** en el panel: «Bitácora» con la corrida (origen remoto; el video está en la PC) y el cartel con su
   ficha y sus documentos. A las 10:45, la cola de IA lo resume.

## Pendiente

- La fase 2 se probó con la app de la PC haciendo de servidor; contra el servidor real se prueba en el paso 11.
- Activar la obtención automática (§9.9), si Oscar lo decide.
- Después de unos días bien, borrar `/opt/sicop-connect-02b569b` y `sicop-02b569b.db` (con un respaldo guardado).
