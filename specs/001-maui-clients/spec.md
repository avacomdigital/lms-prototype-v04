# Spec 001 · Clientes MAUI AVACOM LMS

## Alcance

Crear dos clientes nativos que funcionen dentro de la LAN del aula y que puedan recorrerse también como prototipo autónomo.

## Requisitos verificables

- OPS se distribuye para Windows y muestra de forma permanente el estado de la conexión.
- Student se distribuye para Windows y Android y solicita nombre y dirección del aula.
- El núcleo normaliza direcciones HTTP y deriva la dirección WebSocket sin usar servicios externos.
- El demo contiene `Álgebra Octavo B`, tres unidades/lecciones, dos ítems por lección y un quiz final de cinco preguntas sobre México.
- OPS permite explorar la creación de un curso y muestra el consolidado de actividad por estudiante.
- El menú principal docente presenta once hexágonos: Reportes, Asignaturas, Comunicación, Asistencia, Enciclopedia, Perfil, Progreso, Historial, Calendario, Clase de hoy y Estudiantes.
- Los once hexágonos conservan la retícula del HTML de referencia, sus iconos vectoriales, las etiquetas nativas y la paleta AVACOM.
- Student permite abrir el curso, ver toda su jerarquía, responder el quiz y obtener una nota.
- La interfaz usa la paleta AVACOM, fondo pastel del acceso, tarjetas con sombra y navegación hexagonal.
- Los recursos WebView sólo pueden navegar al host configurado por el consumidor del control.

## Fronteras

Los clientes no contienen persistencia académica ni claves de respuestas recibidas desde el servidor. Los datos demo viven en memoria. La API DRF y su instalador no forman parte de esta entrega.

## Criterios de aceptación

1. Los proyectos OPS y Student compilan para Windows.
2. Student también compila para Android con la carga MAUI instalada.
3. Las pruebas del núcleo validan dirección, curso demo y calificación.
4. Un fallo de `/health/` produce un estado legible y no impide usar el demo.
5. Cada app puede navegar de entrada a su flujo principal sin teclado físico.
