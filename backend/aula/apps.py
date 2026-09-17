from django.apps import AppConfig


class AulaConfig(AppConfig):
    """MOD-007 · Classroom Engine. Sesiones de clase, participantes, foco y distribución.

    No guarda ningún curso: lo lee en vivo (AVACOM Biblioteca o el manifiesto de
    ejemplo) y sólo escribe lo que ocurre en el aula (tablas m07_*)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "aula"
    verbose_name = "Aula · Classroom Engine (MOD-007)"
