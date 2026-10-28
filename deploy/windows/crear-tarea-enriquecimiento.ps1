# SICOP CONNECT - crea la tarea programada "SICOP CONNECT - enriquecimiento" (ver README.md, seccion Enriquecimiento).
# Lunes a viernes a las 10:00, con la ventana visible ("Ejecutar solo cuando el usuario haya iniciado sesion").
# Se corre una sola vez, a mano: powershell -ExecutionPolicy Bypass -File deploy\windows\crear-tarea-enriquecimiento.ps1
# (Sin tildes a proposito: Windows PowerShell 5.1 lee mal los .ps1 en UTF-8 sin BOM.)

$ErrorActionPreference = 'Stop'
$proyecto = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $proyecto 'deploy\windows\sicop-enriquecimiento.ps1'

$accion = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" -WorkingDirectory $proyecto
$horario = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 10:00
$ajustes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun
$usuario = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName 'SICOP CONNECT - enriquecimiento' -Action $accion -Trigger $horario `
    -Settings $ajustes -Principal $usuario `
    -Description 'enrich run, lunes a viernes 10:00, con ventana. Registro en data\logs.'
