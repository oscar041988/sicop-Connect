# SICOP CONNECT - ciclo diario en Windows (equivalente local de deploy/systemd/sicop-cycle.service).
# Lo ejecuta la tarea programada "SICOP CONNECT - ciclo diario" (ver deploy/windows/README.md).
# Siempre en DRY-RUN: prepara los avisos y la vista previa, no envia nada. El envio real seria un cambio aparte.
# Cada ejecucion se agrega a data\logs\ciclo-AAAA-MM.log con su fecha, la salida y el codigo de salida.
# Codigo de salida: 0 = ok - 1 = fallo (queda en source_runs) - 2 = ya habia otro ciclo en curso.
# (Sin tildes a proposito: Windows PowerShell 5.1 lee mal los .ps1 en UTF-8 sin BOM.)

$ErrorActionPreference = 'Stop'
$proyecto = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $proyecto

$python = Join-Path $proyecto '.venv\Scripts\python.exe'
$logs = Join-Path $proyecto 'data\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$ahora = Get-Date
$log = Join-Path $logs ('ciclo-{0:yyyy-MM}.log' -f $ahora)
$salida = Join-Path $env:TEMP "sicop-ciclo-$PID-salida.txt"
$errores = Join-Path $env:TEMP "sicop-ciclo-$PID-errores.txt"

# Sin esto, Windows escribe la salida en cp1252 y Python falla con caracteres como la flecha.
$env:PYTHONUTF8 = '1'
# Start-Process con archivos de salida: en PowerShell 5.1, redirigir 2>&1 de un programa externo marca falsos errores.
try {
    $p = Start-Process -FilePath $python -ArgumentList '-m', 'app.cli', 'run-cycle', '--origen', 'real', '--dry-run' `
        -WorkingDirectory $proyecto -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $salida -RedirectStandardError $errores
    $codigo = $p.ExitCode
} catch {
    $codigo = 1
    Set-Content -Path $errores -Value "No se pudo ejecutar el ciclo: $($_.Exception.Message)" -Encoding UTF8
}

$bloque = @('=' * 70, ('{0:yyyy-MM-dd HH:mm:ss} - run-cycle --origen real --dry-run' -f $ahora))
if (Test-Path $salida) { $bloque += Get-Content -Path $salida -Encoding UTF8 }
if ((Test-Path $errores) -and (Get-Item $errores).Length -gt 0) {
    $bloque += '--- errores ---'
    $bloque += Get-Content -Path $errores -Encoding UTF8
}
$bloque += "Codigo de salida: $codigo"
Add-Content -Path $log -Value $bloque -Encoding UTF8
Remove-Item -Path $salida, $errores -ErrorAction SilentlyContinue
exit $codigo
