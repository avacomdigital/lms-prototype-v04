<#
.SYNOPSIS
    Genera el probador de un solo archivo: AVACOM-Probar-Comunicacion.bat

.DESCRIPTION
    El nodo principal del aula es táctil y no tiene teclado, así que el
    diagnóstico tiene que poder lanzarse con un toque y sin escribir nada. Eso
    descarta un .ps1 suelto por dos motivos:

      · Windows no lo ejecuta con un doble toque, lo abre en el Bloc de notas;
      · al descargarlo de la release queda marcado como venido de internet, y
        la directiva RemoteSigned lo bloquea por no estar firmado.

    Un .bat no tiene ninguno de los dos problemas. Este script mete el
    PowerShell DENTRO del .bat, detrás de un marcador: al ejecutarlo, la parte
    de lotes se lee a sí misma, extrae el PowerShell a un archivo temporal y lo
    corre con la directiva en Bypass. Un archivo, un toque, nada que escribir.

    Se genera en lugar de mantenerse a mano para que el .bat no se quede atrás
    cuando cambie el diagnóstico: la única fuente es Probar-Comunicacion.ps1.

.NOTES
    El .bat se escribe en UTF-8 SIN BOM: cmd.exe se atraganta con el BOM en la
    primera línea. Por eso la parte de lotes es ASCII puro y el PowerShell, que
    sí lleva acentos, se lee explícitamente como UTF-8 desde .NET.
#>
[CmdletBinding()]
param(
    [string] $Origen = '',
    [string] $Destino = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $Origen)  { $Origen  = Join-Path $raiz 'installer\tools\Probar-Comunicacion.ps1' }
if (-not $Destino) { $Destino = Join-Path $raiz 'installer\tools\AVACOM-Probar-Comunicacion.bat' }

if (-not (Test-Path $Origen)) { throw "No se encontro el diagnostico en $Origen." }

# Lo que se incrusta es el texto, no los bytes del archivo.
#
# El recorte del BOM se hace comparando el carácter, no con StartsWith: esa
# comparación es sensible a la cultura y U+FEFF es un carácter ignorable, de
# modo que StartsWith([char]0xFEFF) devuelve True sobre CUALQUIER cadena y se
# lleva por delante el primer carácter bueno. Aquí se comió el '<' de '<#' y el
# resultado fue un .bat que extraía PowerShell con un comentario sin abrir.
$powershell = [System.IO.File]::ReadAllText($Origen, [System.Text.UTF8Encoding]::new($false))
while ($powershell.Length -gt 0 -and [int]$powershell[0] -eq 0xFEFF) {
    $powershell = $powershell.Substring(1)
}

# El marcador se parte en dos en la línea que lo busca para que la única
# aparición literal en el archivo sea la que separa las dos mitades.
$cabecera = @'
@echo off
rem ===========================================================================
rem  AVACOM OPS Master - Diagnostico de comunicacion con AVACOM Biblioteca
rem
rem  UN SOLO ARCHIVO. No necesita nada mas: el diagnostico va dentro de este
rem  mismo .bat, detras del marcador de abajo.
rem
rem  Uso: toca este archivo. Al terminar deja en el escritorio un informe y un
rem  .zip con las evidencias, y los abre.
rem
rem  No modifica nada: solo lee y consulta. No reinicia servicios, no cambia
rem  configuracion y no escribe en el expediente de los estudiantes.
rem
rem  Generado por installer\build\New-ProbadorBat.ps1 desde
rem  installer\tools\Probar-Comunicacion.ps1. No editar a mano.
rem ===========================================================================
setlocal
title AVACOM OPS Master - Diagnostico

echo.
echo   AVACOM OPS Master
echo   Diagnostico de comunicacion con AVACOM Biblioteca
echo.
echo   Revisando... esto tarda entre 10 y 60 segundos.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $t=[IO.File]::ReadAllText('%~f0',[Text.Encoding]::UTF8); $m='#@AVACOM'+'-DIAGNOSTICO@'; $i=$t.IndexOf($m); if($i -lt 0){ Write-Host '  El archivo esta incompleto: vuelve a descargarlo.' -ForegroundColor Red; exit 9 }; $f=Join-Path $env:TEMP ('avacom-diagnostico-'+[guid]::NewGuid().ToString('N')+'.ps1'); [IO.File]::WriteAllText($f,$t.Substring($i+$m.Length),(New-Object Text.UTF8Encoding($true))); $r=9; try { & $f -Abrir -Paquete; $r=$LASTEXITCODE } finally { Remove-Item $f -Force -ErrorAction SilentlyContinue }; exit $r"

set CODIGO=%ERRORLEVEL%
echo.
if "%CODIGO%"=="0" echo   Resultado: la comunicacion funciona.
if "%CODIGO%"=="1" echo   Resultado: hay algo que impide la comunicacion. Mira el informe.
if "%CODIGO%"=="2" echo   Resultado: funciona, con avisos. Mira el informe.
echo.
exit /b %CODIGO%

rem #@AVACOM-DIAGNOSTICO@
'@

# CRLF en todo el archivo: cmd.exe lo exige en la parte de lotes. El salto
# entre el marcador y el PowerShell es explícito porque un here-string no
# conserva su última línea en blanco.
$contenido = ($cabecera -replace "`r?`n", "`r`n") + "`r`n" + ($powershell -replace "`r?`n", "`r`n")

[System.IO.File]::WriteAllText($Destino, $contenido, [System.Text.UTF8Encoding]::new($false))

# Comprobaciones de lo que hace que esto funcione o no.
$bytes = [System.IO.File]::ReadAllBytes($Destino)
if ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    throw 'El .bat quedo con BOM: cmd.exe no ejecutaria la primera linea.'
}
$texto = [System.IO.File]::ReadAllText($Destino, [System.Text.Encoding]::UTF8)
$marcador = '#@AVACOM' + '-DIAGNOSTICO@'
$apariciones = ([regex]::Matches($texto, [regex]::Escape($marcador))).Count
if ($apariciones -ne 1) {
    throw "El marcador aparece $apariciones veces y debe aparecer exactamente una."
}

<#
    Prueba de la extracción, hecha igual que la hace el .bat.

    Generar un .bat sintácticamente válido no sirve de nada si lo que extrae no
    es PowerShell válido, y eso no se ve hasta ejecutarlo en el equipo del aula.
    Aquí se extrae y se analiza con el propio analizador de PowerShell: si no
    parsea, no hay archivo.
#>
$extraido = $texto.Substring($texto.IndexOf($marcador) + $marcador.Length)
if (-not $extraido.TrimStart("`r", "`n").StartsWith('<#')) {
    throw 'Lo extraido no empieza donde debe: el .bat no produciria PowerShell valido.'
}

$erroresDeAnalisis = $null
[void][System.Management.Automation.Language.Parser]::ParseInput(
    $extraido, [ref]$null, [ref]$erroresDeAnalisis)
if ($erroresDeAnalisis -and $erroresDeAnalisis.Count -gt 0) {
    $erroresDeAnalisis | Select-Object -First 5 | ForEach-Object {
        Write-Host "  linea $($_.Extent.StartLineNumber): $($_.Message)" -ForegroundColor Red
    }
    throw "El PowerShell incrustado tiene $($erroresDeAnalisis.Count) error(es) de sintaxis."
}

$kb = [math]::Round((Get-Item $Destino).Length / 1KB, 1)
Write-Host "  $Destino  ($kb KB, un solo archivo)"
