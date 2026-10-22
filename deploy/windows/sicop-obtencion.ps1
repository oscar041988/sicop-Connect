# SICOP CONNECT - obtencion automatica en Windows (leccion 4): una vuelta de "obtain auto".
# Lo ejecuta la tarea programada "SICOP CONNECT - obtencion" cada 15 min, 07:00-20:00, lunes a viernes
# (ver deploy/windows/README.md). Con SOURCE_MODE=manual no hace nada. Los avisos siempre en DRY-RUN.
# Cada vuelta se agrega a data\logs\obtencion-AAAA-MM.log con su fecha, la salida y el codigo de salida.
# Codigo de salida: 0 = ok - 1 = algo fallo (ver el registro y la alerta) - 2 = otra vuelta seguia en curso.
# (Sin tildes a proposito: Windows PowerShell 5.1 lee mal los .ps1 en UTF-8 sin BOM.)

$ErrorActionPreference = 'Stop'
$proyecto = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $proyecto

$python = Join-Path $proyecto '.venv\Scripts\python.exe'
$logs = Join-Path $proyecto 'data\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$ahora = Get-Date
$log = Join-Path $logs ('obtencion-{0:yyyy-MM}.log' -f $ahora)
$salida = Join-Path $env:TEMP "sicop-obtencion-$PID-salida.txt"
$errores = Join-Path $env:TEMP "sicop-obtencion-$PID-errores.txt"

# Sin esto, Windows escribe la salida en cp1252 y Python falla con caracteres como la flecha.
$env:PYTHONUTF8 = '1'
# Start-Process con archivos de salida: en PowerShell 5.1, redirigir 2>&1 de un programa externo marca falsos errores.
try {
    $p = Start-Process -FilePath $python -ArgumentList '-m', 'app.cli', 'obtain', 'auto' `
        -WorkingDirectory $proyecto -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $salida -RedirectStandardError $errores
    $codigo = $p.ExitCode
} catch {
    $codigo = 1
    Set-Content -Path $errores -Value "No se pudo ejecutar obtain auto: $($_.Exception.Message)" -Encoding UTF8
}

$bloque = @(('=' * 70), ('{0:yyyy-MM-dd HH:mm:ss} - obtain auto' -f $ahora))
if (Test-Path $salida) { $bloque += Get-Content -Path $salida -Encoding UTF8 }
if ((Test-Path $errores) -and (Get-Item $errores).Length -gt 0) {
    $bloque += '--- errores ---'
    $bloque += Get-Content -Path $errores -Encoding UTF8
}
$bloque += "Codigo de salida: $codigo"
Add-Content -Path $log -Value $bloque -Encoding UTF8
Remove-Item -Path $salida, $errores -ErrorAction SilentlyContinue
exit $codigo
