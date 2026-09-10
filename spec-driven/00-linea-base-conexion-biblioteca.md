# 00 · Línea base · Cómo está conectado hoy AVACOM OPS con AVACOM Biblioteca

| Campo | Valor |
|---|---|
| Objetivo | Documentar la conexión existente con precisión suficiente para reimplementarla en otro prototipo |
| Alcance leído | `backend/exams`, `src/Avacom.OPS.Core`, `src/Avacom.OPS.Master` |
| Fecha de corte | 2026-09-09 |
| Nombre del componente en el código | `AVACOM-Contenido` (es el mismo producto que en el negocio se llama **AVACOM Biblioteca**) |

Este documento describe **lo que existe**, no lo que se propone. La propuesta está en [04-plan.md](04-plan.md).

---

## 1 · La topología, en una frase

AVACOM Biblioteca escucha **sólo en loopback**, en un **puerto que cambia en cada arranque**, y exige una **ficha**. El backend de OPS es su **único cliente**; las tabletas nunca la alcanzan, piden al backend y el backend decide.

```
Tableta (Avacom.Student)  ─┐
                           │ HTTP LAN  :8000
OPS Master (MAUI)  ────────┼──────────────►  Backend OPS (Django/DRF)
   BibliotecaDeContenido   │                      │
                           ┘                      │ HTTP loopback, puerto efímero
                                                  │ X-Avacom-Ficha
                                                  ▼
                                        AVACOM Biblioteca  127.0.0.1:{efímero}
                                        (otro producto, otra base, cifrada)
```

Tres consecuencias de diseño que hay que replicar tal cual:

1. El puerto **no se fija nunca**. Un puerto conocido es un punto que sondear y choca cuando dos procesos quieren el mismo número.
2. La nota de enlace **no se cachea**. Guardarla en memoria es la forma segura de seguir hablando con un puerto que ya murió.
3. La ausencia de la biblioteca **no es un error**: es un estado normal del aula y produce degradación, no un 500.

---

## 2 · Descubrimiento: la nota de enlace

Al encender su API, la biblioteca escribe y, al cerrarse bien, borra:

```
%ProgramData%\AVACOM\contenido\enlace.json
{"Contrato": 1, "Puerto": 51234, "Ficha": "…64 hex…", "Proceso": 8123}
```

| Campo | Para qué |
|---|---|
| `Contrato` | Versión del contrato. Se compara y se rechaza hablar si es mayor que el soportado |
| `Puerto` | A dónde llamar. Siempre `127.0.0.1` |
| `Ficha` | Va en `X-Avacom-Ficha` en cada petición. Sin ella, 401 |
| `Proceso` | PID, para comprobar que sigue vivo |

Implementación de referencia: [`backend/exams/contenido.py`](../../backend/exams/contenido.py) — `ruta_enlace()` y `leer_enlace()`.

Reglas que la implementación respeta y que deben replicarse:

- La ruta se puede forzar con `AVACOM_CONTENIDO_ENLACE` (setting de Django o variable de entorno). **Es lo que permite probar la integración sin instalar la biblioteca.**
- Se aceptan las claves en PascalCase y en minúsculas: `Contrato`/`contrato`, `Puerto`/`puerto`, `Ficha`/`ficha`, `Proceso`/`proceso`. No se ata el LMS a un detalle de serialización del otro lado.
- Nota ausente, ilegible o incompleta → `ContenidoNoDisponible`, que es una situación normal.
- `Contrato` mayor que `CONTRATO_SOPORTADO` (hoy `1`) → `ContenidoNoDisponible` con el mensaje de que hay que actualizar el LMS. El número sube **sólo** cuando cambia la forma de una respuesta de manera que rompa a quien ya la lee; añadir campos o rutas no lo sube.
- La nota se relee en **cada** petición.

### 2.1 · Comprobar que el proceso sigue vivo

`proceso_vivo(pid)` existe por dos motivos: la nota es un archivo y sobrevive al proceso que la escribió, y puede haber dos componentes en la misma máquina —la aplicación real y un host de pruebas— peleándose ese archivo.

> **Trampa que hay que replicar con cuidado.** En Windows **no** se usa `os.kill(pid, 0)`: CPython lo traduce a `TerminateProcess`, así que preguntar «¿estás vivo?» mataría la biblioteca en mitad de una clase.

La implementación abre un handle de sólo consulta:

| Situación | Retorno |
|---|---|
| `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION=0x1000)` correcto y `GetExitCodeProcess` = `STILL_ACTIVE` (259) | `True` |
| Error 87 `ERROR_INVALID_PARAMETER` (pid inexistente) | `False` |
| Error 5 `ACCESO_DENEGADO` (existe, de otro usuario o mayor integridad) | `True` |
| Cualquier otro caso | `None` — **no se sabe**, que no es lo mismo que «no está» |

En POSIX sí se usa `os.kill(pid, 0)`, que allí es una consulta real.

---

## 3 · El transporte

`_pedir(metodo, camino, consulta=None, cuerpo=None)` es la única función que abre un socket hacia la biblioteca.

- URL: `http://127.0.0.1:{puerto}{camino}` con query filtrada de vacíos.
- Cabeceras: `X-Avacom-Ficha: {ficha}`, `Accept: application/json`, y `Content-Type: application/json` cuando hay cuerpo.
- Cuerpo: JSON con `ensure_ascii=False`, UTF-8.
- Tiempo de espera: **3 s** (`TIEMPO_ESPERA_SEG`). Es loopback: si no contesta en un segundo, no va a contestar, y un timeout largo congela la pantalla del profesor delante de la clase.

Traducción de fallos:

| Fallo del transporte | Excepción del LMS | Significado |
|---|---|---|
| `HTTPError` | `ContenidoError(estado, detalle)` | Contestó, pero con error. Lleva código y motivo (400 primeros caracteres) |
| `URLError` | `ContenidoNoDisponible` | El puerto está en la nota pero nadie escucha: se cerró |
| `TimeoutError`, JSON inválido | `ContenidoNoDisponible` | No contestó a tiempo |

> **Regla estructural.** Si aparece otro `HttpClient`/`urlopen` en el LMS apuntando a `127.0.0.1`, está mal: la política de reintentos, la revalidación de la ficha y el manejo de «no hay contenido» se escriben una sola vez.

---

## 4 · El contrato consumido

### 4.1 · Rutas que la biblioteca ya publica

| Función | Ruta | Notas |
|---|---|---|
| `salud()` | `GET /v1/salud` | Componente, contrato, capacidades, contadores, y opcionalmente `generacion` o `huella_catalogo` |
| `catalogo(**filtros)` | `GET /v1/catalogo?nivel=&grado=&asignatura=&tipo=` | **Con la política del administrador ya aplicada**: lo desactivado por la escuela no llega atenuado ni con una marca, no llega |
| `taxonomia(padre)` | `GET /v1/taxonomia?padre=` | Árbol de profundidad libre |
| `elemento(ref)` | `GET /v1/elemento/{ref}` | Un elemento suelto |
| `mostrar(ref, persona_id)` | `POST /v1/mostrar` | Proyecta un material en la pantalla del aula |

Forma de un elemento del catálogo, tal como lo consume el LMS: `ref`, `tipo`, `titulo`, `nivel`, `grado`, `asignatura`, `version`, `duracion_seg`, `paquete`.

La respuesta llega a veces como lista y a veces como objeto envolvente; `_lista(respuesta, "elementos", "items")` en [`views_contenido.py`](../../backend/exams/views_contenido.py) lo normaliza para que ninguna vista tenga que adivinarlo.

### 4.2 · Rutas previstas y condicionadas por capacidad

Están escritas en el cliente para que el LMS no tenga que cambiar cuando aparezcan, y cada una se protege con `_exigir(capacidad, capacidades)`, que lanza `ContenidoError(501, …)` con un mensaje claro en vez de dejar salir un 404 sin explicación:

| Capacidad | Ruta | Uso en el LMS |
|---|---|---|
| `leccion` | `GET /v1/leccion/{ref}` | — |
| `evaluacion` | `GET /v1/evaluacion/{ref}` | `POST /api/contenido/examen/montar/` |
| `banco` | `POST /v1/banco/{ref}/extraer` | — |
| `comprobar` | `POST /v1/comprobar` | `POST /api/contenido/examen/comprobar/` |
| `medio` | `GET /v1/medio/{ref}` | Sesión de bytes de un solo uso, por loopback |
| `repaso` | `POST /v1/repaso` | Apunta que alguien abrió algo por su cuenta; **no** genera intento ni nota |

Un componente que no declare `capacidades` equivale a la lista vacía: se muestra el catálogo y se esconden las evaluaciones. **Degrada, no se rompe.**

### 4.3 · La corrección nunca trae la clave

`comprobar(pregunta_ref, respuesta, capacidades)` envía la respuesta del alumno y devuelve `{acierta: bool}` más la retroalimentación que la pregunta ya trae. La clave se compara donde vive. Es el único punto del LMS que la toca, y la toca sin verla.

---

## 5 · El estado degradado

`estado()` es «el artículo 9 hecho función»: **nunca lanza**. Devuelve siempre un diccionario y, si no hay componente, `disponible=False` con el motivo.

```python
{
  "disponible": bool,
  "motivo": str,              # vacío cuando disponible
  "puerto": int | None,
  "proceso": int | None,
  "proceso_vivo": True | False | None,
  "componente": str,
  "contrato": int | None,
  "generacion": int | None,
  "generacion_derivada": bool,
  "huella_catalogo": str,
  "capacidades": [str],
  "conteos": {"elementos": int, "paquetes": int, "politicas": int},
}
```

### 5.1 · Detección de cambio del catálogo

`_huella_catalogo(datos)` elige, en orden de preferencia:

1. `g{generacion}` — el contador monótono, lo más fiable.
2. `h{huella_catalogo}` — cambia cuando cambia el catálogo, aunque no diga en qué dirección.
3. `c{elementos}-{paquetes}-{politicas}` — último recurso; no detecta un cambio que deje los totales iguales, pero es mejor que sondear el disco y desaparece solo en cuanto llegue la señal de verdad.

Esta huella es la respuesta a «¿puedo preguntar a menudo?»: sí, porque es diminuta. Traer el catálogo entero para comparar sería caro y haría parpadear las listas.

---

## 6 · Lo que el LMS guarda de la biblioteca (y lo que no)

**No guarda catálogo. Guarda referencias.** En particular **no guarda el título**: cuando una pantalla muestra «Lámina del bosque», ese texto se acaba de pedir. Un título copiado empieza a mentir en cuanto el paquete se actualice, y el LMS pasa a ser un segundo catálogo que alguien tiene que sincronizar a mano.

Tres tablas y una bandera sostienen la integración ([`backend/exams/models.py`](../../backend/exams/models.py)):

| Tabla | Qué es | Columnas de referencia |
|---|---|---|
| `m05_unidad_material` | Qué material de la biblioteca cuelga de qué lección | `elemento_ref`, `version_elemento`, `taxonomia_ref`, `tipo`, `orden` |
| `m05_examen_pregunta` | Qué preguntas le tocaron a qué persona y en qué orden | `pregunta_ref`, `elemento_ref`, `version_elemento`, `orden` — **no hay columna para la clave, y no es un olvido** |
| `m05_reparto_activo` | Qué material está repartido a la clase ahora mismo | `elemento_ref`, `version_elemento`, `tipo`, `host_id`, `sesion_clase_id` |
| `m05_curso_host.formato_contenido` | De dónde vino el contenido del curso | `avacom_contenido` marca los cursos cuyo contenido vive en la biblioteca |

`m05_unidad_material` tiene además tres columnas que **no son una caché del catálogo** sino la **memoria de la última revisión**: `disponible_ultima_revision`, `revisado_en`, `desaparecido_en`. Existen por dos motivos que la consulta en vivo no cubre:

- poder responderle a una tableta «esto ya no está» aunque en ese momento la biblioteca esté cerrada;
- poder decir **desde cuándo** — «no disponible» es un estado, «no disponible desde el martes» es una explicación.

Un `CheckConstraint` impide marcar algo como no disponible sin fecha (`ck_m05_um_ausencia_con_fecha`).

---

## 7 · Reconciliación

[`backend/exams/reconciliacion.py`](../../backend/exams/reconciliacion.py) · `reconciliar(actor, host_id)`, transaccional e idempotente.

**Precondición absoluta:** `_refs_del_catalogo()` **lanza** si la biblioteca no está. Reconciliar contra un catálogo que no se pudo leer marcaría todo como desaparecido, que es exactamente el error que arruinaría una clase con la biblioteca cerrada.

| Se hace | No se hace |
|---|---|
| Actualizar disponibilidad de cada referencia, con fecha de desaparición y de reaparición | Borrar la referencia |
| Cerrar el reparto de lo que ya no está | Borrar la matrícula, el progreso, la nota o el examen |
| Sanear `m05_curso_host` de los cursos cuyo contenido vive en la biblioteca | Reescribir la versión guardada de una referencia: eso lo decide el docente; el LMS sólo lo señala en `cambio_version` |

Devuelve `revisado_en`, `catalogo`, `referencias`, `disponibles`, `no_disponibles`, `desaparecidos`, `reaparecidos`, `cambio_version`, `repartos_cerrados`, `presencia_saneada` y `hubo_cambios`.

### 7.1 · `sanear_presencia(fila, presente, actor)`

Sólo se aplica a filas con `formato_contenido == avacom_contenido`. Para un curso SCORM o cmi5 la bandera `presente_local` **es** la fuente de verdad —los archivos son del LMS— y tocarla aquí sobrescribiría una decisión del docente.

Cuando sí se aplica, `disponible_estudiante` sigue a `presente_local`: el componente ya aplicó la política de la escuela antes de responder, así que un elemento que aparece en el catálogo es uno que la escuela quiere ofrecer. Dejarlo presente pero no disponible obligaría al docente a habilitar a mano algo que él nunca deshabilitó.

Todo cambio deja auditoría en `m19_auditoria` (`curso.host.saneado` / `curso.host.ausente`, `material.desaparecio` / `material.reaparecio`).

---

## 8 · Las rutas que el backend expone hacia arriba

De [`backend/exams/urls.py`](../../backend/exams/urls.py) y [`views_contenido.py`](../../backend/exams/views_contenido.py):

| Ruta | Verbo | Qué hace |
|---|---|---|
| `/api/contenido/estado/` | GET | `estado()` tal cual |
| `/api/contenido/catalogo/` | GET | Oferta vigente con filtros |
| `/api/contenido/reconciliar/` | GET | Informe **sin escribir** (`componente` + `por_curso`) |
| `/api/contenido/reconciliar/` | POST | Reconcilia y deja constancia |
| `/api/contenido/taxonomia/` | GET | Árbol |
| `/api/contenido/elemento/{ref}/` | GET | Un elemento |
| `/api/contenido/mostrar/` | POST | Proyecta en el aula |
| `/api/contenido/reparto/` | GET, POST | Qué está repartido / repartir |
| `/api/contenido/reparto/{id}/cerrar/` | POST | Retirar de la clase |
| `/api/contenido/examen/montar/` | POST | Monta un examen desde una evaluación o banco |
| `/api/contenido/examen/comprobar/` | POST | Delega la corrección de una respuesta |
| `/api/courses/{id}/contenido/` | GET | Veredicto de disponibilidad del curso (`?sanear=1`) |
| `/api/lecciones/{id}/materiales/` | GET, POST | Material colgado de una lección |
| `/api/materiales/{id}/` | DELETE | Quita la asociación; **no** desinstala el paquete |
| `/api/students/{persona}/contenido/` | GET | Sólo los repartos abiertos aplicables |

Códigos de error del contrato hacia arriba:

| Situación | Respuesta |
|---|---|
| `ContenidoNoDisponible` | **503** con `{disponible: false, detail, sugerencia}` (`_sin_componente`) |
| `ContenidoError` con estado 501 | **501** con el detalle y las `capacidades` publicadas |
| `ContenidoError` con otro estado | **502** con el detalle |

### 8.1 · El veredicto de `GET /api/courses/{id}/contenido/`

Es la pieza con más lógica de la integración y la que más conviene replicar entera. Combina **tres fuentes**, porque un curso puede haber llegado por caminos distintos:

1. `m05_curso_host.presente_local` — lo desinstalaron desde esta OPS.
2. El **paquete de origen**, cuando el curso vino de la biblioteca: si `/v1/catalogo` ya no ofrece nada de ese `package_identifier`, su contenido salió del equipo aunque el curso siga aquí.
3. Las **referencias colgadas** en las lecciones: si están todas ausentes, no hay nada que abrir.

Y el **orden importa**: cuando el contenido vive en la biblioteca, el catálogo manda sobre lo que el LMS tenga guardado. `presente_local` es una bandera del LMS que cachea un hecho que no le pertenece; si el paquete volvió y esa bandera sigue en `false`, la que se equivoca es la bandera. Consultarla primero era lo que dejaba el cartel de «desinstalado» pegado tras reinstalar.

Dos distinciones que no se pueden perder al replicar:

- Un curso **SCORM o cmi5 no depende de la biblioteca**. Juzgarlo contra `/v1/catalogo` lo marcaría como retirado sin serlo, porque su paquete nunca estuvo en ese catálogo.
- Sin componente, `paquete_presente` es `None`, no `False`: **no se pudo comprobar** ≠ **no está**.

`?sanear=1` es la única forma de que este GET escriba. El panel lo pide porque le conviene arreglarlo al pasar; **una tableta no lo pide**, y así una tableta nunca puede tocar las banderas de presencia aunque conozca la ruta.

---

## 9 · El lado del cliente (OPS Master)

| Pieza | Archivo | Papel |
|---|---|---|
| `BibliotecaDeContenido` | [`src/Avacom.OPS.Core/Services/BibliotecaDeContenido.cs`](../../src/Avacom.OPS.Core/Services/BibliotecaDeContenido.cs) | Fachada única del Master hacia la biblioteca. **Habla con el backend, no con la biblioteca** |
| `ILmsApiClient` / `ExamApiClient` | [`src/Avacom.OPS.Core/Services/ExamApiClient.cs`](../../src/Avacom.OPS.Core/Services/ExamApiClient.cs) | Cliente HTTP del backend |
| Contratos | [`src/Avacom.OPS.Core/Models/Contracts.cs`](../../src/Avacom.OPS.Core/Models/Contracts.cs) | `ContenidoEstado`, `ContenidoElemento`, `ContenidoCatalogo`, `ReconciliacionResultado`, `CursoContenido`, `RepartoEntrada`, `InformeDeContenido` |
| Consumo | [`src/Avacom.OPS.Master/DashboardViewModel.cs`](../../src/Avacom.OPS.Master/DashboardViewModel.cs) | Reconcilia al abrir el resumen y en el botón «Actualizar» |

Comportamiento de la fachada que hay que replicar:

- Guarda una `_huella` local y `ConsultarEstadoAsync` devuelve `(estado, cambio)` comparando `Available:CatalogFingerprint`. `OlvidarHuella()` fuerza que la próxima consulta cuente como cambio, para recargar al entrar en una pantalla.
- **Un 503 del backend no es una excepción de negocio**: `CatalogoAsync` devuelve lista vacía, `ReconciliarAsync` devuelve `null`, `ContenidoDelCursoAsync` devuelve `null`. Una pantalla del panel no puede quedarse en blanco porque el docente cerró la aplicación de contenido; el motivo queda en `Estado`.
- `null` de `ContenidoDelCursoAsync` significa **«no se pudo comprobar»**, y la pantalla debe decir eso: afirmar que el contenido desapareció cuando sólo está cerrada la biblioteca es peor que no decir nada.
- El Master pide `GET /api/courses/{id}/contenido/?sanear=1`; el informe del panel sale de `GET /api/contenido/reconciliar/`, que no escribe.

---

## 10 · Checklist para replicar la conexión en otro prototipo

Orden recomendado. Cada punto es verificable por separado.

1. **Descubrimiento** — leer la nota en cada llamada, aceptar ambas convenciones de claves, validar el contrato, no cachear nunca.
2. **Vivacidad** — comprobación de PID que no pueda terminar el proceso; tres resultados posibles, incluido «no se sabe».
3. **Transporte único** — una sola función/clase con la ficha, el timeout corto y la traducción de errores a dos excepciones: *no disponible* y *error del componente con código*.
4. **Estado que no lanza** — `estado()` siempre devuelve, con `disponible`, `motivo`, `capacidades` y huella de catálogo.
5. **Huella de cambio** — preferencia `generacion` → `huella_catalogo` → contadores, para poder sondear barato.
6. **Capacidades** — cada ruta opcional exige la suya y responde 501 explicativo; nunca se simula un resultado.
7. **Persistencia mínima** — sólo `ref` + `version` (+ tipo y orden). Ningún título, ninguna estructura, ninguna clave.
8. **Memoria de la última revisión** — tres columnas con fecha, y la restricción que obliga a fechar toda ausencia.
9. **Reconciliación que se niega a ciegas** — si no hubo catálogo válido, no escribe nada.
10. **Degradación hacia arriba** — 503 con motivo y sugerencia; 501/502 para el componente; el cliente lo traduce a lista vacía o `null`, nunca a pantalla en blanco.
11. **Frontera de escritura** — el GET de diagnóstico sólo escribe con `?sanear=1`, que pide el panel y no la tableta.
12. **Pruebas** — la suite de referencia está en [`backend/exams/tests/test_contenido.py`](../../backend/exams/tests/test_contenido.py); se apoya en `AVACOM_CONTENIDO_ENLACE` y en un host de pruebas para no necesitar la biblioteca real.

## 11 · Deudas de la línea base que el nuevo prototipo no debe heredar

- El backend **administra cursos**: los crea, versiona, importa desde paquetes y guarda su árbol completo. Eso contradice la frontera acordada y es el objeto del cambio descrito en [01-constitucion.md](01-constitucion.md) y [04-plan.md](04-plan.md).
- `m05_unidad_material` obliga a que un material cuelgue de una `m05_leccion` **física del LMS**: la composición del curso se decide aquí y no en la biblioteca.
- `CursoContenidoView` tiene que reconciliar dos verdades —la bandera del LMS y el catálogo— justamente porque el LMS mantiene una bandera sobre un hecho ajeno.
- El montaje de exámenes escribe `m05_examen_pregunta` desde el LMS a partir de una evaluación de la biblioteca, mezclando la composición (de la biblioteca) con el reparto por persona (del LMS).
- No hay autenticación: la separación entre docente y estudiante es hoy una convención del cliente, y `?sanear=1` es la única frontera real de escritura.


## 12. Los cursos que se muestran en el LMS son los que están en AVACOM Biblioteca

- AVACOM Biblioteca tiene unos cursos (Ejemplo: "Matemáticas" y "Exploración en el Medio")
- Por ende entonces los únicos cursos que se muestran disponibles son "Matemáticas" y "Exploración en el Medio"
- La pantalla de cursos disponibles también se muestran cómo una lista de cursos 
- Al hacer clic sobre los cursos debería verse todo el contenido del curso

