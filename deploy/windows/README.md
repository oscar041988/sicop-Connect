# Ciclo diario en Windows (local)

Equivalente local de `deploy/systemd/sicop-cycle.timer` + `sicop-cycle.service`: una tarea del Programador de
tareas de Windows que corre el ciclo **de lunes a viernes a las 8:00**, **siempre en dry-run** (prepara los
avisos y la vista previa, no envía nada). Se usa mientras todo se desarrolla en local (decisión de Oscar,
2026-10-21). La tarea la crea la persona que usa la computadora; el script no la activa solo.

- `sicop-ciclo.ps1`: lo que corre la tarea. Ejecuta `run-cycle --origen real --dry-run` y agrega la salida,
  con fecha y código de salida, a `data\logs\ciclo-AAAA-MM.log`.
- Códigos de salida: `0` = ok · `1` = fallo (queda en `source_runs`) · `2` = ya había otro ciclo en curso.

## Antes de crearla

1. Respaldo de la base: `.venv\Scripts\python.exe -m app.cli backup --output C:\Users\User\sicop-respaldos`.
2. Un ciclo a mano que salga bien: `.venv\Scripts\python.exe -m app.cli run-cycle --origen real --dry-run`.
3. Zona horaria de Windows en hora de Costa Rica (la tarea usa la hora de la computadora):
   ```powershell
   Get-TimeZone    # debe decir (UTC-06:00) América Central
   ```

## Crearla (PowerShell, una sola vez)

```powershell
$proyecto = "C:\Users\User\sicop-connect"
$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$proyecto\deploy\windows\sicop-ciclo.ps1`"" `
    -WorkingDirectory $proyecto
$horario = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 8:00
$ajustes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "SICOP CONNECT - ciclo diario" -Action $accion -Trigger $horario -Settings $ajustes `
    -Description "run-cycle --origen real --dry-run, lunes a viernes 8:00. Registro en data\logs."
```

- Corre con tu usuario y **solo con la sesión abierta**: la computadora tiene que estar encendida y con tu
  sesión iniciada a las 8:00.
- Si a las 8:00 estaba apagada, ese día no corre y no se ejecuta tarde (igual que `Persistent=false` en el
  servidor: `-StartWhenAvailable` no se usa a propósito).
- `-MultipleInstances IgnoreNew`: si un ciclo sigue corriendo, no arranca otro (el ciclo además tiene su propio
  bloqueo y saldría con código `2`).

## Comprobarla

```powershell
Get-ScheduledTaskInfo -TaskName "SICOP CONNECT - ciclo diario" | Select-Object NextRunTime, LastRunTime, LastTaskResult
```

`NextRunTime` debe ser el próximo día hábil a las 8:00. `LastTaskResult` es el código de salida del último
ciclo (`0`, `1` o `2`).

**Probarla ahora mismo**, sin esperar a las 8:00:

```powershell
Start-ScheduledTask -TaskName "SICOP CONNECT - ciclo diario"
Get-Content "C:\Users\User\sicop-connect\data\logs\ciclo-$(Get-Date -Format yyyy-MM).log" -Tail 20 -Encoding UTF8
```

Sin un archivo nuevo en `data\incoming`, lo normal es «FALLO · no se importó ningún archivo nuevo» y código
`1`: ese día no hubo datos (ver `docs/OPERACION.md`, sección 3). No es un error de la tarea.

## Cada día hábil

- Dejar el ZIP de SICOP en `data\incoming\` **antes de las 8:00**, sin abrirlo en Excel. Si se copia justo a
  las 8:00, puede salir «EN ESPERA» (modificado hace menos de 60 s): correr el ciclo a mano un minuto después.
- Revisar el registro del día en `data\logs\` y la vista previa en `data\exports\`.

## Pausarla o borrarla

```powershell
Disable-ScheduledTask -TaskName "SICOP CONNECT - ciclo diario"     # pausar
Enable-ScheduledTask -TaskName "SICOP CONNECT - ciclo diario"      # reanudar
Unregister-ScheduledTask -TaskName "SICOP CONNECT - ciclo diario" -Confirm:$false   # borrar
```

`SCHEDULER_ENABLED` en `.env` es solo informativo (lo muestra `doctor`); ponerlo en `true` al crear la tarea y
en `false` al borrarla.

## Obtención automática (lección 4): tarea «SICOP CONNECT - obtencion»

Va **junto con** la tarea de las 8:00 cuando se pase a `SOURCE_MODE=auto` (desde 2026-10-26 la vuelta ya no corre
el ciclo: los avisos salen con la tarea de las 8:00). **No se
crea sola ni se activa con este documento:** se crea cuando Oscar y Ivania lo decidan.

> **Desde 2026-10-26 la obtención se activa en el servidor** (`docs/DESPLIEGUE.md` 9.9). No crear también esta
> tarea en Windows con `SOURCE_MODE=auto`: dos lugares pidiendo el reporte gastarían los turnos y duplicarían los
> correos.

- `sicop-obtencion.ps1`: una vuelta de `obtain auto` cada 15 min, de 07:00 a 20:00, de lunes a viernes. Registro
  en `data\logs\obtencion-AAAA-MM.log`.
- Cada vuelta, con `SOURCE_MODE=auto`: en cada turno de `OBTAIN_REQUEST_HOUR` pide el reporte (uno por turno),
  revisa el buzón y manda el recordatorio o la alerta (a `OBTAIN_ALERT_TO`; en dry-run solo la vista previa). No
  corre el ciclo: eso lo hace la tarea de las 8:00. Con `SOURCE_MODE=manual` no hace nada.
- Códigos de salida: `0` = ok · `1` = algo falló (ver el registro y la alerta) · `2` = otra vuelta seguía en curso.

### Antes de crearla

1. En `.env`: `SOURCE_MODE=auto`, `OBTAIN_REQUEST_HOUR=07:00`, `OBTAIN_ALERT_TO=licitaciones@hermatix.com`.
2. `.venv\Scripts\python.exe -m app.cli migrate` (aplica la 0011).
3. Una vuelta a mano: `.venv\Scripts\python.exe -m app.cli obtain auto`.
4. **No** pausar la tarea de las 8:00: es la que importa lo que quede en `data\incoming` y prepara los avisos.

### Crearla (PowerShell, una sola vez)

```powershell
$proyecto = "C:\Users\User\sicop-connect"
$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$proyecto\deploy\windows\sicop-obtencion.ps1`"" `
    -WorkingDirectory $proyecto
$horario = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 7:00
$horario.Repetition = (New-ScheduledTaskTrigger -Once -At 7:00 -RepetitionInterval (New-TimeSpan -Minutes 15) `
    -RepetitionDuration (New-TimeSpan -Hours 13)).Repetition
$ajustes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "SICOP CONNECT - obtencion" -Action $accion -Trigger $horario -Settings $ajustes `
    -Description "obtain auto cada 15 min, 07:00-20:00, lunes a viernes. Registro en data\logs."
```

- Si la computadora se enciende a las 8:01, la vuelta de las 8:15 hace lo que faltaba: pide el reporte si no se
  pidió y sigue desde donde quedó (el estado vive en la base).
- Volver a manual sin borrar nada: `SOURCE_MODE=manual` en `.env`. La tarea sigue corriendo, pero no hace nada.

### Pausarla o borrarla

```powershell
Disable-ScheduledTask -TaskName "SICOP CONNECT - obtencion"
Unregister-ScheduledTask -TaskName "SICOP CONNECT - obtencion" -Confirm:$false
Enable-ScheduledTask -TaskName "SICOP CONNECT - ciclo diario"    # si se vuelve al ciclo de las 8:00
```

## Enriquecimiento (guía de enriquecimiento, lección 4): tarea «SICOP CONNECT - enriquecimiento»

`sicop-enriquecimiento.ps1` corre `enrich run` **a las 10:00, lunes a viernes** (decisión del 2026-10-27): consulta
en SICOP la cola del día (fichas y documentos), con la **ventana del navegador visible**, y deja el registro en
`data\logs\enriquecimiento-AAAA-MM.log`. Códigos: `0` = ok · `1` = algún FALLO · `2` = CAPTCHA o bloqueo (se detuvo)
u otra corrida en curso. Con `ENRICH_ENABLED=false` (por defecto) no consulta nada.

**Modo interactivo:** para que se vea la ventana, la tarea tiene que ser «**Ejecutar solo cuando el usuario haya
iniciado sesión**». Si se elige «Ejecutar tanto si el usuario inició sesión como si no», el navegador corre
escondido y no se puede supervisar. Además, en ese horario la computadora tiene que estar encendida, con la sesión
iniciada y **sin bloqueo de pantalla ni suspensión** (Configuración › Sistema › Inicio/apagado y suspensión).

### Antes de crearla

1. `migrate` (0020) y una prueba a mano mirando la ventana: `.venv\Scripts\python.exe -m app.cli enrich run --max 3`.
2. Revisar la cola: `.venv\Scripts\python.exe -m app.cli enrich cola`.
3. `ENRICH_ENABLED=true` en `.env` (sin eso, la tarea no consulta nada).

### Crearla (PowerShell, una sola vez)

```powershell
$proyecto = "C:\Users\User\sicop-connect"
$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$proyecto\deploy\windows\sicop-enriquecimiento.ps1`"" `
    -WorkingDirectory $proyecto
$horario = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 10:00
$ajustes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$usuario = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento" -Action $accion -Trigger $horario `
    -Settings $ajustes -Principal $usuario `
    -Description "enrich run, lunes a viernes 10:00, con ventana. Registro en data\logs."
```

- `-LogonType Interactive` es «Ejecutar solo cuando el usuario haya iniciado sesión»: así se ve la ventana.
- 3 horas de límite: 20 carteles con sus documentos y las pausas de 8 s pueden tardar más de una hora.
- Si a las 10:00 la computadora estaba apagada, ese día no corre: la cola espera en la base y el resumen del día
  siguiente avisa cuántos días hábiles no hubo corrida.

### Probarla y revisarla

```powershell
Start-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento"
Get-Content "C:\Users\User\sicop-connect\data\logs\enriquecimiento-$(Get-Date -Format yyyy-MM).log" -Tail 30 -Encoding UTF8
.venv\Scripts\python.exe -m app.cli enrich status
```

El resumen queda en `data\exports\resumen-enriquecimiento-<n>.txt` mientras los avisos estén en dry-run.

### Pausarla

`ENRICH_ENABLED=false` en `.env` (la tarea sigue corriendo pero no consulta) o
`Disable-ScheduledTask -TaskName "SICOP CONNECT - enriquecimiento"`.
