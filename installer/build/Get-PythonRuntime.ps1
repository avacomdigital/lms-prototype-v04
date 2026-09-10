<#
.SYNOPSIS
    Ensambla el runtime de Python que AVACOM OPS Master distribuye con su backend.

.DESCRIPTION
    El equipo del aula no tiene que instalar Python, ni tener internet, ni
    ejecutar pip. Este script prepara -en el equipo de compilacion- una carpeta
    autocontenida con:

        Python embeddable (python.org, sin instalador ni registro)
        + Django + Django REST Framework + Waitress + dependencias

    El resultado se copia tal cual dentro del paquete de distribucion. En el
    equipo destino solo se descomprime: no se ejecuta pip ni winget.

    Los paquetes son todos "py3-none-any" (Python puro), asi que se resuelven
    con --only-binary y --platform win_amd64 para que el resultado no dependa
    del Python que tenga el equipo de compilacion.

.NOTES
    Requiere internet SOLO en el equipo de compilacion.
#>
[CmdletBinding()]
param(
    # Debe coincidir en major.minor con el Python con el que se prueba el
    # backend: los paquetes se instalan para esta version.
    [string] $PythonVersion = '3.12.10',
    [Parameter(Mandatory)] [string] $Destination,
    [Parameter(Mandatory)] [string] $RequirementsFile,
    [string] $CacheDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $CacheDirectory) {
    $CacheDirectory = Join-Path $env:LOCALAPPDATA 'AVACOM\build-cache\python'
}
New-Item -ItemType Directory -Force -Path $CacheDirectory | Out-Null

$corto = ($PythonVersion -split '\.')[0..1] -join ''   # 3.12.10 -> 312
$zipNombre = "python-$PythonVersion-embed-amd64.zip"
$zipRuta = Join-Path $CacheDirectory $zipNombre
$url = "https://www.python.org/ftp/python/$PythonVersion/$zipNombre"

if (-not (Test-Path $zipRuta)) {
    Write-Host "  Descargando $zipNombre ..."
    $anterior = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    try {
        Invoke-WebRequest -Uri $url -OutFile $zipRuta -UseBasicParsing
    } finally {
        $ProgressPreference = $anterior
    }
} else {
    Write-Host "  $zipNombre ya estaba en la cache de compilacion."
}

if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

Write-Host '  Descomprimiendo el runtime ...'
Expand-Archive -Path $zipRuta -DestinationPath $Destination -Force

$pythonExe = Join-Path $Destination 'python.exe'
if (-not (Test-Path $pythonExe)) {
    throw "El paquete embeddable no trajo python.exe en $Destination."
}

# El paquete embeddable ignora site-packages salvo que se declare en el ._pth.
# Sin esto, Django no se importa.
$pth = Join-Path $Destination "python$corto._pth"
if (-not (Test-Path $pth)) { throw "No se encontro $pth." }
@(
    "python$corto.zip"
    '.'
    'Lib\site-packages'
    ''
    '# AVACOM OPS Master: site.main() habilita site-packages en el runtime embebido.'
    'import site'
) | Set-Content -Path $pth -Encoding ascii

$sitePackages = Join-Path $Destination 'Lib\site-packages'
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null

Write-Host '  Instalando dependencias del backend en el runtime ...'
$pipPython = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pipPython) { throw 'Se necesita Python en el PATH del equipo de compilacion para resolver las dependencias.' }

$destinoTfm = ($PythonVersion -split '\.')[0..1] -join '.'
& $pipPython.Source -m pip install `
    --requirement $RequirementsFile `
    --target $sitePackages `
    --only-binary :all: `
    --platform win_amd64 `
    --python-version $destinoTfm `
    --implementation cp `
    --no-compile `
    --disable-pip-version-check `
    --no-warn-script-location
if ($LASTEXITCODE -ne 0) { throw 'pip no pudo preparar el runtime del backend.' }

# Los .exe de consola (django-admin, waitress-serve) apuntan al Python del
# equipo de compilacion: no sirven en el destino y confunden. El backend se
# ejecuta con `python.exe -m`, nunca con estos lanzadores.
$bin = Join-Path $sitePackages 'bin'
if (Test-Path $bin) { Remove-Item -Recurse -Force $bin }
Get-ChildItem -Path $sitePackages -Filter '*.exe' -File -ErrorAction SilentlyContinue | Remove-Item -Force

# Comprobacion real: el runtime que se va a distribuir debe poder importar lo
# que el backend necesita. Si esto falla, el paquete no sale.
$verificacion = & $pythonExe -c "import django, rest_framework, waitress, zoneinfo, sqlite3; print(django.get_version())" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "El runtime ensamblado no pudo importar el backend: $verificacion"
}
Write-Host "  Runtime listo: Python $PythonVersion con Django $verificacion"

$paquetes = Get-ChildItem -Path $sitePackages -Directory -Filter '*.dist-info' |
    ForEach-Object { $_.Name -replace '\.dist-info$', '' } | Sort-Object
[pscustomobject]@{
    python   = $PythonVersion
    paquetes = $paquetes
} | ConvertTo-Json -Depth 3
