# Pasar el enriquecimiento a otra computadora

Guía paso a paso para que otra persona de Hermatix (por ejemplo, Anabelle u Oscar) corra el enriquecimiento desde
su computadora cuando Ivania ya no esté. Escrita por Ivania con Claude el 2026-11-11. Diseño de fondo:
`docs/ENVIO_ENRIQUECIMIENTO.md` (Fase 2). Detalle de las tareas de Windows: `deploy/windows/README.md`.

**Requisito previo:** el servidor ya está actualizado y recibe las fichas (`docs/ACTUALIZACION_SERVIDOR.md` §11).
Mientras eso no esté, el enriquecimiento sigue en la PC de Ivania.

## Qué hace la computadora y qué hace el servidor

- **La computadora**, lunes a viernes a las 10:00, le pide al servidor la lista de carteles, abre SICOP con el
  navegador **visible** y le manda al servidor la ficha y los documentos de cada uno.
- **El servidor** guarda todo, lee el texto de los PDF, reevalúa los carteles y a las 10:45 hace los resúmenes con
  IA.
- En la computadora solo quedan los videos y las capturas de cada consulta. No hay base que copiar.

## Antes de empezar

- Windows 10 u 11, con una cuenta de usuario que se use a diario.
- Una computadora que esté **encendida y con la sesión abierta a las 10:00** de lunes a viernes, con la pantalla
  sin bloquear. Mejor una que se quede en la oficina que una laptop que sale mucho.
- Zona horaria de Costa Rica: en PowerShell, `Get-TimeZone` debe decir `(UTC-06:00) América Central`.
- Acceso al repositorio de GitHub de Oscar (`oscar041988/sicop-Connect`).
- **Oscar presente** para el paso 4: él escribe el token.

## Paso 1. Instalar Python 3.12 y Git

1. Instalar Git para Windows (git-scm.com) y el Python Install Manager (python.org).
2. En PowerShell: `py install 3.12` y comprobar con `py list`.
   El comando es `py`, no `python`: si se escribe `python`, Windows ofrece la Microsoft Store.

## Paso 2. Copiar el proyecto

```powershell
cd $env:USERPROFILE
git clone git@github.com:oscar041988/sicop-Connect.git sicop-connect
cd sicop-connect
git checkout main
```

Se usa `main`, la versión que está en el servidor. Si GitHub rechaza la llave SSH, se puede clonar por HTTPS
(`https://github.com/oscar041988/sicop-Connect.git`) con la cuenta que tenga acceso.

## Paso 3. Entorno e instalación

```powershell
py -V:3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m playwright install chromium
```

- Si PowerShell bloquea el `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Con el entorno activo, la línea empieza con `(.venv)`.
- No actualizar pip ni ningún paquete aunque lo sugiera: se usan las versiones fijas del servidor.

## Paso 4. Configuración (`.env`), con Oscar

```powershell
Copy-Item .env.example .env
notepad .env
```

Cambiar solo estas líneas:

```ini
ENRICH_ENABLED=true
ENRICH_SERVER_URL=https://sicop.hermatix.com
ENRICH_TOKEN=          # lo escribe Oscar: el mismo de /etc/sicop-connect/app.env del servidor
```

- El token **nunca** se manda por correo, chat ni WhatsApp, ni va a Git. Oscar lo escribe en persona.
- El resto del `.env` se deja como viene. Esta computadora no manda avisos ni usa la IA: eso lo hace el servidor.
- Con `ENRICH_SERVER_URL` lleno, `enrich run` se niega a correr: nada se escribe en una base local.

## Paso 5. Prueba con un solo cartel (mirando la ventana)

```powershell
python -m app.cli enrich remoto --max 1
```

Lo esperado: «Corrida #N en el servidor…», se abre el navegador con SICOP y al final «Enviado al servidor: nueva ·
K documento(s) guardado(s)». En el panel del servidor, «Bitácora» muestra la corrida.
Si dice 401, el token no coincide con el del servidor: Oscar lo revisa.

## Paso 6. Apagar la tarea en la computadora anterior

**Solo una computadora a la vez.** Cuando una empieza su corrida, el servidor cierra como «detenida» la que esté
abierta: si dos tienen la tarea a las 10:00, se cortan entre sí. En la computadora anterior (por ejemplo, la de
Ivania):

```powershell
Disable-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento"
```

Si esa computadora deja de usarse, también vaciar `ENRICH_TOKEN` en su `.env`.

## Paso 7. Crear la tarea de las 10:00 en la computadora nueva

Con la sesión de la persona que va a usar la computadora (la tarea corre con su usuario):

```powershell
cd $env:USERPROFILE\sicop-connect
powershell -ExecutionPolicy Bypass -File deploy\windows\crear-tarea-enriquecimiento.ps1
```

Ese script la crea sin `-Remoto`; se le agrega así:

```powershell
$proyecto = "$env:USERPROFILE\sicop-connect"
$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$proyecto\deploy\windows\sicop-enriquecimiento.ps1`" -Remoto" `
    -WorkingDirectory $proyecto
Set-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento" -Action $accion
```

Comprobar:

```powershell
Get-ScheduledTaskInfo -TaskName "SICOP CONNECT - enriquecimiento" | Select-Object NextRunTime, LastRunTime, LastTaskResult
```

`NextRunTime` debe ser el próximo día hábil a las 10:00.

## Paso 8. El primer día

- A las 10:00 se abre la ventana del navegador sola: **no cerrarla** ni usar el mouse encima mientras consulta.
  Puede tardar más de una hora con 20 carteles.
- Después, en el panel del servidor, «Bitácora» muestra la corrida «ok» o «con_fallos».
- Registro en la computadora: `data\logs\enriquecimiento-AAAA-MM.log`.

## Si algo sale mal

| Qué pasa | Qué hacer |
|---|---|
| La computadora estaba apagada a las 10:00 | Ese día no se consulta; la lista espera al día siguiente. Se puede correr a mano: `Start-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento"` |
| SICOP pide CAPTCHA o bloquea | La app espera 15 min y reintenta **una** vez; si vuelve, se detiene. **Nunca** resolver el CAPTCHA a mano. Avisar a Oscar |
| 401 en la prueba o en el registro | El token no coincide con el del servidor: Oscar lo revisa |
| El servidor no responde | La app reintenta 3 veces cada envío. Lo ya enviado queda guardado; una corrida que no se pudo cerrar el servidor la marca «detenida» al abrir la siguiente |

**Importante sobre los correos:** hoy `ENRICH_EMAILS=false` (decisión de Ivania, 2026-11-09). Con eso, ni el resumen
del día ni la alerta de CAPTCHA llegan por correo: hay que mirar la «Bitácora» del panel. Si se quiere recibirlos,
lo decide Oscar.

## Volver atrás

Para que la computadora anterior vuelva a encargarse: `Disable-ScheduledTask` en la nueva y
`Enable-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento"` en la anterior. Nunca las dos activas.
