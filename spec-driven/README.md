# Spec-Driven Development · Frontera AVACOM OPS ↔ AVACOM Biblioteca

Documentación para el **nuevo prototipo**, en el que la administración del curso vive únicamente en AVACOM Biblioteca y el backend de AVACOM OPS registra únicamente el progreso del estudiante.

| Documento | Para qué sirve | Léelo si… |
|---|---|---|
| [00 · Línea base de la conexión](00-linea-base-conexion-biblioteca.md) | Cómo está conectado hoy OPS con la biblioteca, con el detalle necesario para **reimplementarlo** en otro prototipo | Vas a replicar la integración |
| [01 · Constitución](01-constitucion.md) | Los artículos 13 y 14, sus reglas verificables y su efecto sobre los artículos vigentes | Necesitas decidir si algo está permitido |
| [02 · Especificación · delta](02-especificacion-delta.md) | Qué se queda, qué se va y qué se resuelve en vivo, con trazabilidad de los requisitos anteriores | Quieres saber dónde acabó un requisito |
| [03 · Clarificación](03-clarificacion.md) | Tabla de decisiones y los cinco bloqueos del plan | Vas a empezar a construir |
| [04 · Plan técnico](04-plan.md) | Modelo de datos objetivo, contratos, degradación, migración en tres pasos y pruebas | Vas a escribir código |
| [05 · Tareas](05-tareas.md) | Los nueve bloques, su grafo, la ruta crítica y los bloqueos | Vas a planificar el trabajo |
| [06 · Contrato exigido a la biblioteca](06-contrato-biblioteca.md) | Lo que el otro producto tiene que publicar para que esto sea posible | Hablas con el equipo de AVACOM Biblioteca |
| [07 · Comunicación OPS ↔ Student en la LAN](07-comunicacion-ops-student.md) | Backend y OPS en el equipo maestro, Student en otra máquina de la misma red: red, cortafuegos, Android en texto claro, pantalla «Tus cursos», sesión en vivo con Channels y la lista de comprobación de la prueba | Vas a probar Student desde una tableta o un portátil |

El prompt normativo, con los bloques `/speckit.*` listos para ejecutar, está en [`docs/prompts/prompt-backend-spec-driven.md`](../prompts/prompt-backend-spec-driven.md).

---

## El cambio, en una frase

> El LMS deja de tener cursos y pasa a tener sólo el expediente de lo que hicieron las personas con ellos.

Antes: 19 entidades, de las cuales 12 describen contenido que el LMS no posee.
Después: 8 entidades de expediente, y la estructura del curso resuelta en vivo por referencia.

## Antes de escribir una línea de código

1. **Q-19 y Q-20 tienen que estar respondidas.** Sin el contrato de curso y estructura de la biblioteca, y sin la referencia estable de curso, retirar las tablas de OPS deja al estudiante sin nada que recorrer.
2. **Q-21 tiene que estar respondida.** Hay expediente que apunta a filas físicas que van a desaparecer.
3. **El paso 3 de la migración no se ejecuta** hasta que la verificación de cobertura del paso 2 esté en verde y con informe.

## La regla que más fácil se rompe

Cachear. Guardar el catálogo, el título de un curso o la bandera de presencia «para que vaya rápido» produce dos verdades, y el trabajo de sincronizarlas no termina nunca. La línea base ya lo demuestra: mantiene una bandera de presencia sobre un hecho ajeno y necesita reconciliarla, sanearla y explicar por qué a veces se queda pegada.

La única memoria permitida sobre el contenido son fechas: si estaba, cuándo se revisó y desde cuándo falta. Sirve para poder decir «no disponible desde el martes» con la biblioteca cerrada, y no para decidir nada.
