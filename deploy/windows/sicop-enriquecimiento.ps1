# SICOP CONNECT - enriquecimiento automatico en Windows (guia de enriquecimiento, leccion 4): "enrich run".
# Lo ejecuta la tarea programada "SICOP CONNECT - enriquecimiento" a las 10:00, lunes a viernes, CON la ventana del
# navegador visible: la tarea debe estar en "Ejecutar solo cuando el usuario haya iniciado sesion" (ver README.md).
# Con ENRICH_ENABLED=false no hace nada. La alerta y el resumen siguen las reglas de los avisos (dry-run: vista previa).
# Despues corre "ia cola" (Reporte con IA, leccion 5; decision de Ivania, 2026-10-30): resumenes de los carteles Alta
# y Media ya enriquecidos, con el presupuesto diario. Corre aunque el enriquecimiento falle (resume lo ya guardado).
# Con AI_MODE=none no hace nada.
# Cada corrida se agrega a data\logs\enriquecimiento-AAAA-MM.log con su fecha, la salida y el codigo de salida.
# Codigo de salida: el de enrich run si no es 0 (1 = algun FALLO, 2 = CAPTCHA o bloqueo u otra corrida); si no, el
# de ia cola (1 = algun resumen fallido o cola detenida por la clave o el saldo).
# (Sin tildes a proposito: Windows PowerShell 5.1 lee mal los .ps1 en UTF-8 sin BOM.)

$ErrorActionPreference = 'Stop'
$proyecto = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $proyecto

$python = Join-Path $proyecto '.venv\Scripts\python.exe'
$logs = Join-Path $proyecto 'data\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$log = Join-Path $logs ('enriquecimiento-{0:yyyy-MM}.log' -f (Get-Date))

# Sin esto, Windows escribe la salida en cp1252 y Python falla con caracteres como la flecha.
$env:PYTHONUTF8 = '1'

function Ejecutar([string[]] $argumentos) {
    $ahora = Get-Date
    $nombre = $argumentos -join ' '
    $salida = Join-Path $env:TEMP "sicop-enriquecimiento-$PID-salida.txt"
    $errores = Join-Path $env:TEMP "sicop-enriquecimiento-$PID-errores.txt"
    # Start-Process con archivos de salida: en PowerShell 5.1, redirigir 2>&1 de un programa externo marca falsos errores.
    try {
        $p = Start-Process -FilePath $python -ArgumentList (@('-m', 'app.cli') + $argumentos) `
            -WorkingDirectory $proyecto -NoNewWindow -Wait -PassThru `
            -RedirectStandardOutput $salida -RedirectStandardError $errores
        $codigo = $p.ExitCode
    } catch {
        $codigo = 1
        Set-Content -Path $errores -Value "No se pudo ejecutar ${nombre}: $($_.Exception.Message)" -Encoding UTF8
    }
    $bloque = @(('=' * 70), ('{0:yyyy-MM-dd HH:mm:ss} - {1}' -f $ahora, $nombre))
    if (Test-Path $salida) { $bloque += Get-Content -Path $salida -Encoding UTF8 }
    if ((Test-Path $errores) -and (Get-Item $errores).Length -gt 0) {
        $bloque += '--- errores ---'
        $bloque += Get-Content -Path $errores -Encoding UTF8
    }
    $bloque += "Codigo de salida: $codigo"
    Add-Content -Path $log -Value $bloque -Encoding UTF8
    Remove-Item -Path $salida, $errores -ErrorAction SilentlyContinue
    return $codigo
}

$codigoEnriquecimiento = Ejecutar @('enrich', 'run')
$codigoIa = Ejecutar @('ia', 'cola')
if ($codigoEnriquecimiento -ne 0) { exit $codigoEnriquecimiento }
exit $codigoIa
