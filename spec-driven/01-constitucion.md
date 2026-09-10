# 01 · Constitución del nuevo prototipo

| Campo | Valor |
|---|---|
| Ámbito | Backend de AVACOM OPS (el LMS) y su frontera con AVACOM Biblioteca |
| Estado | Propuesta para ratificar |
| Origen | Fase 1 del prompt [`docs/prompts/prompt-backend-spec-driven.md`](../prompts/prompt-backend-spec-driven.md) |

Los artículos 1 a 12 se conservan de la constitución vigente. Este documento desarrolla los **dos artículos que definen el nuevo prototipo** y sus consecuencias verificables. El texto normativo completo, en el formato que consume `/speckit.constitution`, está en la Fase 1 del prompt.

---

## Artículo 13 · El expediente del estudiante es lo único que el LMS posee

**Principio.** Todo lo que el estudiante hace se registra en AVACOM OPS: inscripción, apertura de una lección, avance, intento, respuesta, veredicto, nota, finalización y tiempos. El LMS es la fuente autoritativa del expediente y de su auditoría, y ningún otro producto lo reescribe.

**Justificación.** El expediente es el único dato del sistema que **no se puede volver a generar**. Un paquete de contenido se reinstala; una nota perdida no se recupera. Por eso vive donde ocurre, se escribe una sola vez y no depende de que el contenido siga presente.

**Reglas verificables.**

| # | Regla | Cómo se comprueba |
|---|---|---|
| 13.1 | El expediente se escribe contra identidad lógica: referencia de curso, código lógico de lección, referencia de evaluación y referencia de pregunta | Ninguna columna de expediente es clave foránea a una estructura de contenido |
| 13.2 | El expediente sobrevive a cambio de versión, retiro y desaparición del catálogo | Escenario retirar → consultar → reponer conserva recuentos exactos |
| 13.3 | Cada fila conserva el rótulo con el que se registró, sólo como evidencia histórica | El rótulo nunca se actualiza tras la escritura inicial; no participa en ninguna decisión de disponibilidad |
| 13.4 | La auditoría es de sólo escritura y lectura | No hay ruta ni operación que edite o borre auditoría |

**Consecuencia para el desarrollo.** Cualquier función que necesite «buscar la lección» para escribir progreso está mal orientada: el progreso se escribe con el código lógico que trajo el cliente, y la estructura sólo se usa para *mostrar*.

---

## Artículo 14 · La administración del curso pertenece a AVACOM Biblioteca

**Principio.** Crear, editar, estructurar, versionar, publicar, revertir, importar y retirar un curso o su contenido ocurre exclusivamente en AVACOM Biblioteca. **Ninguna tabla de cursos queda en el backend de AVACOM OPS.**

**Justificación.** Dos productos que pueden editar el mismo curso producen dos verdades y un trabajo permanente de sincronización. La línea base ya paga ese coste: mantiene una bandera de presencia sobre un hecho que no le pertenece, y por eso necesita reconciliarla y sanearla. Con un solo dueño, ese código desaparece en lugar de mejorarse.

**Reglas verificables.**

| # | Regla | Cómo se comprueba |
|---|---|---|
| 14.1 | No existe tabla de curso, marco curricular, versión de curso, sección, lección, ítem, recurso, actividad, pregunta ni opción | Prueba de esquema que falla si aparece cualquiera |
| 14.2 | No existe operación de escritura de curso o estructura | Prueba por verbo y ruta retirados: responden rechazo explicativo que nombra al dueño |
| 14.3 | La estructura y los rótulos se resuelven en vivo por referencia | Cambiar la estructura en la biblioteca cambia lo que ve el estudiante sin ninguna operación en OPS |
| 14.4 | Lo único conservado sobre el contenido es la memoria de la última revisión de disponibilidad | Esa tabla no tiene columnas de título, estructura, enunciado ni clave |
| 14.5 | La corrección ocurre donde vive la clave | Ninguna columna del esquema puede contener una clave; el LMS guarda el veredicto |
| 14.6 | Retirar contenido no borra ni modifica expediente | Su única consecuencia visible es que no se puede abrir, con estado y fecha |

**Consecuencia para la revisión.** Una propuesta que añada una tabla «para no llamar tanto a la biblioteca» es una violación del artículo, no una optimización. La excepción única y acotada es 14.4, cuya razón de ser es poder **explicar una ausencia con la biblioteca cerrada** —y por eso guarda fechas, no contenido.

**Consecuencia para las pruebas.** Toda prueba que exija administración de curso en OPS se retira documentando que su requisito se trasladó, en lugar de adaptarse el código para satisfacerla.

---

## Relación con los artículos vigentes

| Artículo vigente | Efecto del cambio |
|---|---|
| 1 · Separación entre contenido físico y expediente | Se refuerza: ahora la separación es también física, entre dos productos |
| 2 · Curso permanente y contenido versionado | Se **traslada** a AVACOM Biblioteca; OPS sólo observa la versión vigente |
| 3 · Identidad lógica y física | Se conserva y pasa a ser la base del contrato: los códigos lógicos los emite la biblioteca |
| 4 · Neutralidad del formato de entrada | Se **traslada**: los formatos se analizan en la biblioteca |
| 5 · Operaciones transaccionales e idempotentes | Se conserva, aplicado a intento, respuesta, finalización, reparto y revisión de disponibilidad |
| 6 · Custodia de respuestas y privacidad | Se endurece: el LMS no puede filtrar una clave porque no la tiene |
| 7 · AVACOM-Contenido es otro producto | Se conserva íntegro y se amplía: también es dueño del curso |
| 8 · Topología local y operación de aula | Sin cambios |
| 9 · Integridad impuesta en profundidad | Se conserva; el conjunto de invariantes se reduce con las tablas que se van |
| 10 · Auditoría confiable | Se conserva y gana el evento de rechazo de administración |
| 11 · Simplicidad del prototipo | Cambia de signo: el objetivo ya no es mantener 19 entidades, es tener menos |
| 12 · Contrato verificable | Sin cambios |

## Proceso de enmienda

Toda excepción a los artículos 13 y 14 debe indicar: qué principio cambia, por qué, qué contratos afecta, qué migración requiere y qué pruebas la hacen segura. Una excepción que consista en volver a guardar estructura de curso en OPS exige además explicar cómo se evitará la doble verdad que este cambio existe para eliminar.
