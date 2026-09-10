"""
Backend de AVACOM LMS (AVACOM OPS Master + AVACOM Student).

Este backend NO administra cursos. Los cursos viven en AVACOM Biblioteca y se
consultan en vivo por loopback. Aquí sólo se guarda el expediente del estudiante:
inscripción, aperturas del visor, progreso por sección, intentos y notas.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("AVACOM_LMS_SECRET", "prototipo-aula-sin-internet-no-es-secreto")
DEBUG = os.environ.get("AVACOM_LMS_DEBUG", "1") == "1"

# El aula es una LAN cerrada: las tabletas llegan por la IP del equipo maestro.
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "biblioteca",
    "expediente",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "avacom_lms.urls"
WSGI_APPLICATION = "avacom_lms.wsgi.application"
ASGI_APPLICATION = "avacom_lms.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("AVACOM_LMS_DB", str(BASE_DIR / "db.sqlite3")),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

REST_FRAMEWORK = {
    # Prototipo de aula: sin autenticación (Q-04). La separación docente/estudiante
    # es una convención del cliente y de la frontera de escritura del backend.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
}

# ---------------------------------------------------------------- Biblioteca
# Ruta forzada de la nota de enlace. Permite probar la integración con un host
# de pruebas sin instalar la biblioteca (ver tools/host_biblioteca_pruebas.py).
AVACOM_CONTENIDO_ENLACE = os.environ.get("AVACOM_CONTENIDO_ENLACE") or None
# Tiempo de espera hacia la biblioteca. Es loopback: si no contesta en tres
# segundos, no va a contestar, y esperar más congela la pantalla del profesor.
AVACOM_CONTENIDO_TIEMPO_ESPERA_SEG = float(os.environ.get("AVACOM_CONTENIDO_TIEMPO_ESPERA_SEG", "3"))
