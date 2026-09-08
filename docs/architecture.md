# Arquitectura de los clientes

Las dependencias apuntan hacia el núcleo:

```text
AVACOM LMS OPS ─────┐
                    ├── AVACOM LMS UI ── AVACOM LMS Core
AVACOM LMS Student ─┘                 └── HTTP / WebSocket ── DRF :8000
```

`Avacom.Lms.Core` no conoce MAUI: define modelos, datos demo y contratos de comunicación. `Avacom.Lms.Ui` aporta componentes reutilizables (`HexagonButton` y `LearningResourceView`). Cada ejecutable conserva sus pantallas y navegación porque sus responsabilidades y plataformas son distintas.

La interfaz funciona primero con datos locales para que la pantalla OPS sea diagnosticable incluso cuando la red falla. Al conectar un backend, `LmsApiClient` cubre salud, catálogo y respuestas, mientras `ActivitySocketClient` recibe eventos del aula. La URL se configura en la primera pantalla y nunca queda codificada en la lógica de dominio.
