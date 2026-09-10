"""
Arranque del backend de AVACOM OPS Master con Waitress.

Sustituye a `manage.py runserver`, que es un servidor de desarrollo: recarga
codigo, es de un solo hilo por peticion y Django advierte explicitamente de no
usarlo en produccion. En un aula donde varias tabletas piden material a la vez,
eso se nota.

Lo que NO cambia respecto a `runserver`:
  * la misma aplicacion WSGI (`avacom_lms.wsgi.application`),
  * la misma configuracion (`avacom_lms.settings`, leida de variables de entorno),
  * la misma escucha: 0.0.0.0:8000.

Este archivo pertenece al instalador, no al backend: vive en Runtime\ y no
toca nada de Backend\.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
RAIZ_INSTALACION = RUNTIME.parent
BACKEND = RAIZ_INSTALACION / "Backend"


def main() -> int:
    if not (BACKEND / "manage.py").exists():
        print(f"No se encontro el backend en {BACKEND}", file=sys.stderr)
        return 2

    # El backend se importa como esta instalado, sin copiarlo ni empaquetarlo.
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "avacom_lms.settings")

    host = os.environ.get("AVACOM_OPS_BACKEND_HOST", "0.0.0.0")
    puerto = int(os.environ.get("AVACOM_OPS_BACKEND_PORT", "8000"))
    hilos = int(os.environ.get("AVACOM_OPS_BACKEND_THREADS", "8"))

    from waitress import serve

    from avacom_lms.wsgi import application

    print(
        f"AVACOM OPS Backend escuchando en {host}:{puerto} "
        f"(waitress, {hilos} hilos, expediente en "
        f"{os.environ.get('AVACOM_LMS_DB', 'ruta por defecto del backend')})",
        flush=True,
    )
    # ident: lo que el servidor anuncia en la cabecera Server.
    serve(application, host=host, port=puerto, threads=hilos, ident="AVACOM OPS Backend")
    return 0


if __name__ == "__main__":
    sys.exit(main())
