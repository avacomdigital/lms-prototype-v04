"""
Marcadores de posición para los medios del curso de EJEMPLO.

El manifiesto de ejemplo (`spec-driven/02-classroom-engine/example.json`) describe
imágenes, videos, audios, PDF y simulaciones cuyos archivos no existen en este
repositorio: los servirá AVACOM Biblioteca. Para que el cliente MAUI pueda
construir y probar sus componentes (Image, MediaElement, WebView, visor PDF) sin
la biblioteca, la fuente de ejemplo genera aquí bytes válidos de cada tipo.
Ninguno se guarda: se generan en cada petición. El video no se simula (se
responde 404 explicativo): un MP4 válido no se fabrica en tres líneas.
"""
from __future__ import annotations

import math
import struct
import zlib

ROJO = (0xE5, 0x26, 0x2B)
GRIS = (0xF1, 0xF1, 0xF1)
TINTA = (0x18, 0x18, 0x1B)


# ------------------------------------------------------------------------ PNG

def _trozo(tipo: bytes, datos: bytes) -> bytes:
    return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)


def png_marcador(ancho: int = 640, alto: int = 360) -> bytes:
    """Un PNG RGB válido: banda roja de marca arriba, área gris y un recuadro que sugiere la lámina."""
    ancho = max(16, min(int(ancho or 640), 1280))
    alto = max(16, min(int(alto or 360), 720))
    banda = max(8, alto // 6)
    margen = max(8, min(ancho, alto) // 12)
    filas = bytearray()
    for y in range(alto):
        filas.append(0)  # filtro «none»
        for x in range(ancho):
            if y < banda:
                color = ROJO
            elif margen <= y < alto - margen and margen <= x < ancho - margen:
                color = TINTA if (y - margen) % 40 < 2 or (x - margen) % 40 < 2 else (0xFF, 0xFF, 0xFF)
            else:
                color = GRIS
            filas.extend(color)
    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _trozo(b"IHDR", ihdr) + _trozo(b"IDAT", zlib.compress(bytes(filas), 6)) + _trozo(b"IEND", b"")


# ------------------------------------------------------------------------ WAV

def wav_tono(segundos: float = 1.0, frecuencia: float = 440.0, tasa: int = 16000) -> bytes:
    """Un tono suave en WAV PCM 16 bits mono, para probar el reproductor de audio."""
    segundos = max(0.2, min(float(segundos or 1.0), 5.0))
    muestras = int(tasa * segundos)
    datos = bytearray()
    for i in range(muestras):
        envolvente = min(1.0, i / (tasa * 0.05), (muestras - i) / (tasa * 0.05))
        valor = int(0.2 * 32767 * envolvente * math.sin(2 * math.pi * frecuencia * i / tasa))
        datos += struct.pack("<h", valor)
    cabecera = b"RIFF" + struct.pack("<I", 36 + len(datos)) + b"WAVE"
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, tasa, tasa * 2, 2, 16)
    return cabecera + fmt + b"data" + struct.pack("<I", len(datos)) + bytes(datos)


# ------------------------------------------------------------------------ PDF

def _texto_pdf(texto: str) -> bytes:
    return texto.encode("cp1252", errors="replace").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def pdf_minimo(titulo: str, paginas: int = 1, lineas: list[str] | None = None) -> bytes:
    """Un PDF válido de `paginas` páginas con Helvetica (sin incrustar fuentes), para probar rangos de páginas."""
    paginas = max(1, min(int(paginas or 1), 50))
    objetos: list[bytes] = []
    # 1 catálogo, 2 páginas, 3 fuente; luego por página: contenido y página.
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(b"")  # se rellena después con los Kids
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    kids = []
    for n in range(1, paginas + 1):
        cuerpo = b"BT /F1 20 Tf 60 780 Td (" + _texto_pdf(titulo) + b") Tj ET\n"
        cuerpo += b"BT /F1 12 Tf 60 750 Td (P\xe1gina " + str(n).encode() + b" de " + str(paginas).encode() + b" \xb7 marcador de posici\xf3n del LMS) Tj ET\n"
        y = 710
        for linea in (lineas or []):
            cuerpo += b"BT /F1 11 Tf 60 " + str(y).encode() + b" Td (" + _texto_pdf(linea) + b") Tj ET\n"
            y -= 18
        objetos.append(b"<< /Length " + str(len(cuerpo)).encode() + b" >>\nstream\n" + cuerpo + b"endstream")
        indice_contenido = len(objetos)
        objetos.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents " + str(indice_contenido).encode()
                       + b" 0 R /Resources << /Font << /F1 3 0 R >> >> >>")
        kids.append(f"{len(objetos)} 0 R".encode())
    objetos[1] = b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count " + str(paginas).encode() + b" >>"

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    desplazamientos = []
    for numero, cuerpo in enumerate(objetos, start=1):
        desplazamientos.append(len(salida))
        salida += f"{numero} 0 obj\n".encode() + cuerpo + b"\nendobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n".encode() + b"0000000000 65535 f \n"
    for d in desplazamientos:
        salida += f"{d:010d} 00000 n \n".encode()
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(salida)


# ----------------------------------------------------------------- VTT / texto

def vtt_minimo(titulo: str, duracion_seg: float | None) -> bytes:
    fin = max(2.0, float(duracion_seg or 4.0))
    mitad = fin / 2
    return (
        "WEBVTT\n\n"
        f"00:00:00.000 --> 00:00:{mitad:06.3f}\n{titulo}\n\n"
        f"00:00:{mitad:06.3f} --> 00:00:{fin:06.3f}\nSubtítulos de ejemplo generados por el LMS.\n"
    ).encode("utf-8")


def transcripcion_minima(titulo: str) -> bytes:
    return f"{titulo}\n\nTranscripción de ejemplo. El texto real viaja en el paquete de AVACOM Biblioteca.\n".encode("utf-8")


# ---------------------------------------------------------------------- HTML

def html_simulacion(titulo: str, proveedor: str | None, parametros: dict, ancho: int | None, alto: int | None,
                    ajustes: list[str]) -> bytes:
    """Una simulación HTML5 mínima (partículas en un lienzo) que respeta los ajustes del manifiesto:
    `scale_to_fit` escala el diseño al viewport y `block_network` no pide nada fuera de la página.
    Lee los parámetros de lanzamiento del query string (p. ej. startTemp) y los muestra."""
    ancho = int(ancho or 1280)
    alto = int(alto or 720)
    escalar = "scale_to_fit" in (ajustes or [])
    lista_ajustes = ", ".join(ajustes or []) or "ninguno"
    parametros_html = ", ".join(f"{k}={v}" for k, v in (parametros or {}).items()) or "ninguno"
    html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{titulo}</title>
<style>
html,body{{margin:0;height:100%;background:#101014;color:#fff;font-family:Segoe UI,Arial,sans-serif;overflow:hidden}}
#marco{{position:absolute;left:50%;top:50%;width:{ancho}px;height:{alto}px;transform-origin:center;background:#18181B;border:2px solid #E5262B;border-radius:16px}}
#cab{{position:absolute;left:0;right:0;top:0;padding:14px 20px;background:#E5262B;font-weight:700;font-size:20px;border-radius:14px 14px 0 0}}
#cab small{{display:block;font-weight:400;opacity:.9;font-size:13px;margin-top:4px}}
canvas{{position:absolute;left:0;top:70px;width:100%;height:calc(100% - 70px)}}
#pie{{position:absolute;left:20px;bottom:12px;font-size:13px;opacity:.85}}
</style></head><body><div id="marco">
<div id="cab">{titulo}<small>Simulación de ejemplo · proveedor: {proveedor or 'avacom'} · ajustes: {lista_ajustes} · parámetros: <span id="p">{parametros_html}</span></small></div>
<canvas id="c"></canvas><div id="pie">Marcador de posición del LMS. La simulación real la sirve AVACOM Biblioteca.</div></div>
<script>
(function(){{
  var q=new URLSearchParams(location.search), t=parseFloat(q.get('startTemp')); if(isNaN(t)) t=20;
  var vistos=[]; q.forEach(function(v,k){{ if(k!=='fuente') vistos.push(k+'='+v); }}); if(vistos.length) document.getElementById('p').textContent=vistos.join(', ');
  var marco=document.getElementById('marco'), W={ancho}, H={alto};
  function ajustar(){{ var s={'Math.min(innerWidth/W, innerHeight/H)' if escalar else '1'}; marco.style.transform='translate(-50%,-50%) scale('+s+')'; }}
  ajustar(); addEventListener('resize', ajustar);
  var c=document.getElementById('c'), ctx=c.getContext('2d'); c.width=W; c.height=H-70;
  var n=60, p=[]; for(var i=0;i<n;i++) p.push({{x:Math.random()*c.width,y:Math.random()*c.height,vx:(Math.random()-.5),vy:(Math.random()-.5)}});
  var energia=Math.max(0.2,(t+20)/40);
  function paso(){{ ctx.fillStyle='#18181B'; ctx.fillRect(0,0,c.width,c.height); ctx.fillStyle='#01A4E1';
    for(var i=0;i<n;i++){{ var a=p[i]; a.x+=a.vx*energia*4; a.y+=a.vy*energia*4; if(a.x<8||a.x>c.width-8)a.vx*=-1; if(a.y<8||a.y>c.height-8)a.vy*=-1;
      ctx.beginPath(); ctx.arc(a.x,a.y,8,0,6.283); ctx.fill(); }}
    ctx.fillStyle='#fff'; ctx.font='16px Segoe UI'; ctx.fillText('Temperatura inicial: '+t+' °C · energía '+energia.toFixed(2), 20, 30);
    requestAnimationFrame(paso); }}
  paso();
}})();
</script></body></html>"""
    return html.encode("utf-8")
