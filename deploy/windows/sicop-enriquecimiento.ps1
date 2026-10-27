# SICOP CONNECT - enriquecimiento automatico en Windows (guia de enriquecimiento, leccion 4): "enrich run".
# Lo ejecuta la tarea programada "SICOP CONNECT - enriquecimiento" a las 10:00, lunes a viernes, CON la ventana del
# navegador visible: la tarea debe estar en "Ejecutar solo cuando el usuario haya iniciado sesion" (ver README.md).
# Con ENRICH_ENABLED=false no hace nada. La alerta y el resumen siguen las reglas de los avisos (dry-run: vista previa).
# Cada corrida se agrega a data\logs\enriquecimiento-AAAA-MM.log con su fecha, la salida y el codigo de salida.
# Codigo de salida: 0 = ok - 1 = algun FALLO (ver el resumen) - 2 = CAPTCHA o bloqueo (detenido), u otra corrida.
# (Sin tildes a proposito: Windows PowerShell 5.1 lee mal los .ps1 en UTF-8 sin BOM.)

$ErrorActionPreference = 'Stop'
$proyecto = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $proyecto

$python = Join-Path $proyecto '.venv\Scripts\python.exe'
$logs = Join-Path $proyecto 'data\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$ahora = Get-Date
$log = Join-Path $logs ('enriquecimiento-{0:yyyy-MM}.log' -f $ahora)
$salida = Join-Path $env:TEMP "sicop-enriquecimiento-$PID-salida.txt"
$errores = Join-Path $env:TEMP "sicop-enriquecimiento-$PID-errores.txt"

# Sin esto, Windows escribe la salida en cp1252 y Python falla con caracteres como la flecha.
$env:PYTHONUTF8 = '1'
# Start-Process con archivos de salida: en PowerShell 5.1, redirigir 2>&1 de un programa externo marca falsos errores.
try {
    $p = Start-Process -FilePath $python -ArgumentList '-m', 'app.cli', 'enrich', 'run' `
        -WorkingDirectory $proyecto -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $salida -RedirectStandardError $errores
    $codigo = $p.ExitCode
} catch {
    $codigo = 1
    Set-Content -Path $errores -Value "No se pudo ejecutar enrich run: $($_.Exception.Message)" -Encoding UTF8
}

$bloque = @(('=' * 70), ('{0:yyyy-MM-dd HH:mm:ss} - enrich run' -f $ahora))
if (Test-Path $salida) { $bloque += Get-Content -Path $salida -Encoding UTF8 }
if ((Test-Path $errores) -and (Get-Item $errores).Length -gt 0) {
    $bloque += '--- errores ---'
    $bloque += Get-Content -Path $errores -Encoding UTF8
}
$bloque += "Codigo de salida: $codigo"
Add-Content -Path $log -Value $bloque -Encoding UTF8
Remove-Item -Path $salida, $errores -ErrorAction SilentlyContinue
exit $codigo
