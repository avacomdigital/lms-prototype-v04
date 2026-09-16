"""
Módulo de acceso y usuarios de AVACOM LMS.

Arquitectura hexagonal dentro del monolito modular:

    interfaces/      adaptador HTTP (DRF): vistas, serializers, autenticación
    aplicacion/      casos de uso y puertos (sin Django)
    dominio/         entidades, value objects, políticas y plantillas (sin Django)
    infraestructura/ adaptadores: Django ORM, Argon2id, AES-GCM, HMAC, JWT, reloj, azar
    models.py        el esquema (adaptador de persistencia; Django lo exige aquí)
"""
