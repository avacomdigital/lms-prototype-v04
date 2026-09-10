# 05 · Tareas

| Campo | Valor |
|---|---|
| Estado | Propuesta. Ninguna tarea se ejecuta con Q-19..Q-23 abiertas |
| Bloque normativo | Fase 5 del prompt [`docs/prompts/prompt-backend-spec-driven.md`](../prompts/prompt-backend-spec-driven.md) |

Cada tarea indica si **conserva**, **prueba**, **corrige**, **traslada** o **elimina** comportamiento. `[P]` marca las que pueden ir en paralelo sin escribir los mismos archivos.

---

## Bloque A · Congelar la línea base

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T001 | Pruebas de caracterización del expediente actual: inscripción, progreso, intento, respuesta y nota | prueba | `backend/exams/tests/test_expediente_base.py` | La suite pasa contra el código actual sin modificarlo |
| T002 | Registrar las decisiones Q-01..Q-26 en [03-clarificacion.md](03-clarificacion.md) | conserva | `docs/spec-driven/03-clarificacion.md` | Ninguna pregunta bloqueante sin respuesta |
| T003 `[P]` | Exportar un volcado de la base actual como base de prueba de migración | prueba | `backend/tests/fixtures/base_v03.sqlite3` | Se abre y se cuentan sus filas de expediente |

## Bloque B · El otro lado del contrato

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T010 | Acordar y publicar el contrato de curso y estructura con AVACOM Biblioteca (Q-19, Q-20) | traslada | [`06-contrato-biblioteca.md`](06-contrato-biblioteca.md) | Documento firmado por ambos productos |
| T011 | Host de pruebas que implemente ese contrato en loopback con nota de enlace | prueba | `backend/tools/host_biblioteca_pruebas.py` | Responde salud, oferta, curso y estructura con `AVACOM_CONTENIDO_ENLACE` |
| T012 | Ampliar el cliente único con las rutas de curso y estructura | conserva | `backend/exams/biblioteca.py` | Prueba contra el host de T011, incluida la degradación |

## Bloque C · Resolver en vivo, sin tocar el modelo

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T020 | `exams.estructura`: resolver y proyectar el árbol por `curso_ref` | corrige | `backend/exams/estructura.py` | Devuelve el mismo árbol que hoy sale de la base, contra el host de pruebas |
| T021 | Reapuntar la consulta de estructura del estudiante a `exams.estructura` | corrige | `backend/exams/views.py` | Las pruebas de T001 siguen pasando; la pantalla no cambia |
| T022 | Degradación sin biblioteca: expediente con rótulos y aviso | corrige | `backend/exams/views.py` | Prueba con biblioteca apagada devuelve 200 con progreso y notas |

## Bloque D · Referencias en el expediente

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T030 | Añadir columnas de referencia y rótulo, nulables | corrige | `backend/exams/models.py`, migración | `makemigrations --check` limpio; nada más cambia |
| T031 | Migración de datos que las pobla desde las tablas actuales | corrige | migración de datos | Recuentos iguales antes y después |
| T032 | Verificación de cobertura con informe de filas irresolubles | prueba | `backend/exams/management/commands/verificar_referencias.py` | Sobre la base de T003, informe completo y sin pérdida |
| T033 | Reescribir `progress` e `intentos` para leer y escribir por referencia | corrige | `backend/exams/progress.py`, `backend/exams/intentos.py` | Pruebas de T001 adaptadas al nuevo contrato interno, mismos resultados |

**T032 bloquea el bloque F.** Sin cobertura verificada no se elimina nada.

## Bloque E · Cerrar la frontera

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T040 | `exams.rechazos` con el error explicativo de RF-003 | corrige | `backend/exams/rechazos.py`, `backend/exams/urls.py` | Una prueba por verbo y ruta retirados |
| T041 `[P]` | Auditar el intento de administración rechazado si Q-03 lo pide | corrige | `backend/exams/rechazos.py` | La fila de auditoría aparece con actor y operación |
| T042 | Retirar del contrato las rutas de paquetes y de host | elimina | `backend/exams/urls.py` | Responden rechazo, no 404 |

## Bloque F · Eliminar lo que ya no es nuestro

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T050 | Eliminar modelos y migración de las doce tablas de curso y estructura | elimina | `backend/exams/models.py`, migración | Migra desde base limpia y desde la base de T003 |
| T051 | Prueba de esquema que falla si vuelve cualquiera de ellas | prueba | `backend/exams/tests/test_frontera.py` | Falla al añadir a mano un modelo de curso |
| T052 | Prueba de que ningún módulo importa un modelo de curso o estructura | prueba | `backend/exams/tests/test_frontera.py` | Recorre los módulos del backend |
| T053 | Eliminar `exams.catalog`, `exams.package_install`, `exams.packages`, `exams.hosts` y sus pruebas | traslada | esos archivos | El proyecto arranca y la suite pasa sin ellos |
| T054 | Trasladar sus requisitos a la especificación de AVACOM Biblioteca | traslada | especificación del otro producto | Tabla de requisitos trasladados con destino y responsable |

## Bloque G · Expediente sobre referencias

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T060 | `m10_intento_pregunta` y el reparto de preguntas por persona | corrige | `backend/exams/models.py`, `intentos.py` | Reconstruye el examen de una persona sin contenido disponible |
| T061 | Respuesta idempotente con veredicto delegado | corrige | `backend/exams/intentos.py` | Reenviar la misma pregunta no duplica filas |
| T062 | Corrección delegada, y estado `pendiente_correccion` sin capacidad (Q-22) | corrige | `backend/exams/intentos.py` | Sin capacidad no se produce ninguna nota |
| T063 | Finalización idempotente que calcula la nota y alimenta el progreso | conserva | `backend/exams/intentos.py`, `progress.py` | Finalizar dos veces conserva una sola nota |
| T064 | Progreso monotónico y promedio sobre la estructura vigente | conserva | `backend/exams/progress.py` | Un progreso atrasado no reduce; 100% sella |
| T065 | Progreso histórico cuando el código lógico ya no está en la versión vigente | conserva | `backend/exams/progress.py` | Aparece marcado como histórico, no se borra |

## Bloque H · Disponibilidad y aula

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T070 | `m05_disponibilidad_observada` y su restricción de ausencia con fecha | corrige | `backend/exams/models.py`, migración | No se puede marcar ausente sin fecha |
| T071 | `exams.disponibilidad`: revisar, marcar, cerrar repartos imposibles y auditar | corrige | `backend/exams/disponibilidad.py` | Idempotente; sin oferta válida no escribe |
| T072 | Distinguir «no disponible» de «no se pudo comprobar» en cada respuesta | corrige | `backend/exams/views.py` | Prueba con biblioteca apagada nunca marca ausente |
| T073 `[P]` | Reparto de aula sobre `curso_ref` | corrige | `backend/exams/models.py`, vistas de aula | Un solo reparto abierto; cierre por retiro |

## Bloque I · Cierre

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T080 | Seed de expediente idempotente que no crea ningún curso | corrige | `backend/exams/management/commands/seed_exam.py` | Ejecutarlo dos veces no duplica; funciona con la biblioteca apagada |
| T081 `[P]` | Actualizar `docs/API.md` y `docs/ARCHITECTURE.md` al conjunto reducido | conserva | esos archivos | Coinciden con el esquema real |
| T082 | Tareas de frontend que Q-23 decida, una por pantalla afectada | corrige | `src/Avacom.OPS.Master/**` | La aplicación instalada no queda con pantallas que llamen a rutas retiradas |
| T083 | Escenario integral: inscribir → estructura vigente → avanzar → evaluar → retirar → consultar → reponer → continuar | prueba | `backend/exams/tests/test_escenario_integral.py` | Pasa sin Internet |
| T084 | Comprobación de proyecto, migraciones desde base limpia y desde T003, y suite completa | prueba | `scripts/Invoke-Tests.ps1` | Todo verde con informe |

---

## Grafo de dependencias

```
T001,T002,T003 ─► T010 ─► T011 ─► T012 ─► T020 ─► T021 ─► T022
                                                    │
                                                    ▼
                                   T030 ─► T031 ─► T032 ─┬─► T033
                                                          │
                          T040 ─► T041,T042               │
                                     │                    │
                                     └────────────┬───────┘
                                                  ▼
                                     T050 ─► T051,T052 ─► T053 ─► T054
                                                  │
                                                  ▼
                              T060..T065     T070..T073
                                     └──────┬──────┘
                                            ▼
                              T080,T081 ─► T082 ─► T083 ─► T084
```

**Ruta crítica:** T010 → T012 → T020 → T031 → T032 → T050 → T063 → T083 → T084.

**Paralelismo real:** T003 con T001/T002; T041 con T042; T073 con T060..T065; T081 con T080.

## Bloqueos

| Bloqueo | Tareas detenidas |
|---|---|
| Q-19, Q-20 sin respuesta | Todo el bloque B y, por dependencia, C a I |
| Q-21 sin respuesta | T050 y siguientes |
| Q-22 sin respuesta | T062 |
| Q-23 sin respuesta | T082 |
| Q-24 sin respuesta | T070 y la tabla condicionada de identidad |
