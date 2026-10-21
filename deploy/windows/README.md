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
