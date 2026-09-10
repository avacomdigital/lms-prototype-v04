<#
.SYNOPSIS
    Genera las imágenes de marca que muestra el asistente en sus pantallas.

.DESCRIPTION
    Sin esto, Inno Setup pone sus propias ilustraciones genéricas: una grande en
    Bienvenido y en Instalación completada, y una pequeña arriba a la derecha en
    todas las demás. Es decir, un logo que no es de AVACOM, repetido en cada
    pantalla del instalador.

    La fuente es el símbolo de AVACOM ya rasterizado por la propia compilación
    de la aplicación (`avacom_mark.scale-400.png`, que sale de
    assets/avacom-symbol.svg). Así el asistente y la aplicación muestran
    exactamente la misma marca, y no hay una segunda copia que se pueda
    desviar de la primera.

    De cada imagen se generan dos tamaños; Inno elige según el DPI de la
    pantalla, que en un equipo táctil de aula no suele ser 96.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $SimboloPng,
    [Parameter(Mandatory)] [string] $Destino
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Add-Type -AssemblyName System.Drawing

if (-not (Test-Path $SimboloPng)) {
    throw "No se encontro el simbolo rasterizado en $SimboloPng."
}
New-Item -ItemType Directory -Force $Destino | Out-Null

$simbolo = [System.Drawing.Image]::FromFile((Resolve-Path $SimboloPng).Path)
try {
    <#
        Dibuja el símbolo sobre un lienzo blanco.

        $ocupacion  fracción del lienzo que ocupa el símbolo (por su lado limitante)
        $centroY    dónde queda su centro vertical, en fracción de la altura
    #>
    function Componer {
        param(
            [string] $Archivo,
            [int]    $Ancho,
            [int]    $Alto,
            [double] $Ocupacion,
            [double] $CentroY
        )

        $lienzo = New-Object System.Drawing.Bitmap($Ancho, $Alto,
            [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
        $g = [System.Drawing.Graphics]::FromImage($lienzo)
        try {
            $g.Clear([System.Drawing.Color]::White)
            $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality

            # Se respeta la proporción del símbolo: nunca se deforma la marca.
            $escala = [Math]::Min($Ancho / $simbolo.Width, $Alto / $simbolo.Height) * $Ocupacion
            $w = [int][Math]::Round($simbolo.Width * $escala)
            $h = [int][Math]::Round($simbolo.Height * $escala)
            $x = [int][Math]::Round(($Ancho - $w) / 2)
            $y = [int][Math]::Round($Alto * $CentroY - $h / 2)

            $g.DrawImage($simbolo, $x, $y, $w, $h)
        } finally {
            $g.Dispose()
        }

        $ruta = Join-Path $Destino $Archivo
        $lienzo.Save($ruta, [System.Drawing.Imaging.ImageFormat]::Png)
        $lienzo.Dispose()
        Write-Host "  $Archivo  ${Ancho}x${Alto}"
    }

    # Imagen grande: el panel izquierdo de Bienvenido y de Instalación
    # completada. Alto y estrecho; el símbolo va en el tercio superior para no
    # competir con el texto de la derecha.
    Componer -Archivo 'banner.png'    -Ancho 410 -Alto 797  -Ocupacion 0.62 -CentroY 0.34
    Componer -Archivo 'banner-2x.png' -Ancho 820 -Alto 1594 -Ocupacion 0.62 -CentroY 0.34

    # Imagen pequeña: esquina superior derecha del resto de pantallas.
    Componer -Archivo 'simbolo.png'    -Ancho 138 -Alto 140 -Ocupacion 0.82 -CentroY 0.5
    Componer -Archivo 'simbolo-2x.png' -Ancho 276 -Alto 280 -Ocupacion 0.82 -CentroY 0.5

    <#
        Icono del propio archivo del instalador.

        El appicon.ico que genera MAUI trae un solo tamaño de 64 px, y Windows
        lo escala borroso justo en el archivo que el usuario va a tocar para
        instalar. Aquí se compone un .ico con todos los tamaños que Windows
        pide, cada uno dibujado a su resolución en lugar de estirado.
    #>
    $tamanos = @(16, 20, 24, 32, 40, 48, 64, 128, 256)
    $imagenes = New-Object System.Collections.Generic.List[byte[]]

    foreach ($lado in $tamanos) {
        $lienzo = New-Object System.Drawing.Bitmap($lado, $lado,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $g = [System.Drawing.Graphics]::FromImage($lienzo)
        try {
            $g.Clear([System.Drawing.Color]::White)
            $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

            # En 16 px el símbolo necesita casi todo el cuadro para reconocerse;
            # en los grandes, un margen lo hace respirar.
            $ocupacion = if ($lado -le 24) { 0.94 } elseif ($lado -le 48) { 0.88 } else { 0.80 }
            $escala = [Math]::Min($lado / $simbolo.Width, $lado / $simbolo.Height) * $ocupacion
            $w = [int][Math]::Round($simbolo.Width * $escala)
            $h = [int][Math]::Round($simbolo.Height * $escala)
            $g.DrawImage($simbolo, [int](($lado - $w) / 2), [int](($lado - $h) / 2), $w, $h)
        } finally {
            $g.Dispose()
        }

        $memoria = New-Object System.IO.MemoryStream
        $lienzo.Save($memoria, [System.Drawing.Imaging.ImageFormat]::Png)
        $imagenes.Add($memoria.ToArray())
        $memoria.Dispose()
        $lienzo.Dispose()
    }

    # ICONDIR (6 bytes) + una ICONDIRENTRY de 16 bytes por imagen + los PNG.
    $rutaIco = Join-Path $Destino 'instalador.ico'
    $flujo = [System.IO.File]::Create($rutaIco)
    $escritor = New-Object System.IO.BinaryWriter($flujo)
    try {
        $escritor.Write([uint16]0)                      # reservado
        $escritor.Write([uint16]1)                      # tipo: icono
        $escritor.Write([uint16]$tamanos.Count)

        $desplazamiento = 6 + 16 * $tamanos.Count
        for ($i = 0; $i -lt $tamanos.Count; $i++) {
            $lado = $tamanos[$i]
            # En el formato, 256 se codifica como 0.
            $escritor.Write([byte]($lado % 256))
            $escritor.Write([byte]($lado % 256))
            $escritor.Write([byte]0)                    # colores de paleta
            $escritor.Write([byte]0)                    # reservado
            $escritor.Write([uint16]1)                  # planos
            $escritor.Write([uint16]32)                 # bits por pixel
            $escritor.Write([uint32]$imagenes[$i].Length)
            $escritor.Write([uint32]$desplazamiento)
            $desplazamiento += $imagenes[$i].Length
        }
        foreach ($imagen in $imagenes) { $escritor.Write($imagen) }
    } finally {
        $escritor.Dispose()
        $flujo.Dispose()
    }
    Write-Host "  instalador.ico  $($tamanos -join '/') px"
} finally {
    $simbolo.Dispose()
}
