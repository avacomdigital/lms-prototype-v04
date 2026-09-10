# 03 · Clarificación · tabla de decisiones

| Campo | Valor |
|---|---|
| Bloqueo del plan | Q-19, Q-20, Q-21, Q-22 y Q-23 |
| Preguntas normativas completas | Fase 3 del prompt [`docs/prompts/prompt-backend-spec-driven.md`](../prompts/prompt-backend-spec-driven.md) |

Esta tabla es el registro que la Fase 4 consume. Ninguna pregunta abierta se responde por inferencia del código actual.

## Estado

| ID | Pregunta | Estado | Decisión registrada |
|---|---|---|---|
| Q-01 | ¿Existe borrado de curso en OPS? | **Resuelta** | No. Ninguna operación de curso pertenece a OPS. El progreso del estudiante —todo lo que el estudiante realiza— se registra en el LMS |
| Q-02 | ¿Qué significa versión inmutable? | **Resuelta** | Es responsabilidad de AVACOM Biblioteca. OPS observa la versión vigente y anota contra qué versión ocurrió cada hecho |
| Q-03 | ¿Auditoría append-only? | **Resuelta** | Sí. Existe para reportar actividad del estudiante y uso de la plataforma por ambas partes |
| Q-04 | Autenticación mínima | **Resuelta** | No hay autenticación en el prototipo. Se deja preparado el modelo de datos; su tabla se aprueba en Q-24 |
| Q-05 | Quién ve soluciones y resultados | **Resuelta** | Todos, por ahora. No relaja la regla de la clave: el LMS no la almacena |
| Q-06 | ¿La instalación administra archivos? | **Resuelta** | Ni archivos ni estructura. Ambos son de la biblioteca |
| Q-07 | ¿Preservar el contrato actual? | **Resuelta** | El contrato con la biblioteca se define en su primera edición. El de OPS se recorta a expediente con rechazo explicativo |
| Q-08 | Garantía de `client_event_id` | Abierta | — |
| Q-09 | Validación de la conexión en vivo | Abierta | — |
| Q-10 | ¿El progreso puede disminuir? | Abierta | — |
| Q-11 | Ponderación del curso | Abierta | Cambia de dueño: ahora la estructura vigente la declara la biblioteca |
| Q-12 | Cambio de código lógico entre versiones | Abierta | — |
| Q-13 | Contrato definitivo del componente en el equipo | Abierta | — |
| Q-14 | Límites de paquetes | **Trasladada** | Pasa a la especificación de AVACOM Biblioteca |
| Q-15 | Qué significa offline para Student | Abierta | — |
| Q-16 | Fin del supuesto de un solo proceso | Abierta | — |
| Q-17 | Retención de datos | Abierta | — |
| Q-18 | Unificación del contrato de errores | Abierta | — |
| Q-19 | **Contrato de curso y estructura de la biblioteca** | El contrato del curso es que AVACOM Biblioteca es el que tiene todo el contenido, acá el LMS registra el progreso |
| Q-20 | **Referencia estable de curso** | **Cerrada** | Los ids de los cursos quedan en AVACOM Biblioteca, AVACOM LMS hace tablas transitivas para guardar la referencia de las notas, actividades realizadas por el estudiante y toda la información asociada al progreso en general |
| Q-21 | **Destino de los cursos y el expediente existentes** | **Cerrada** | Los cursos quedan en AVACOM Biblioteca y los expedientes de su manejo en LMS |
| Q-22 | **Cálculo de nota sin claves en el LMS** | **Cerrada** | El LMS guarda las notas, AVACOM Biblioteca no guarda nada de eso |
| Q-23 | **Impacto en OPS Master** | **Abierta · bloqueante** | — |
| Q-24 | Conjunto exacto de tablas que quedan | Abierta | Propuesta en [04-plan.md](04-plan.md) §2 |
| Q-25 | Frecuencia de revisión de disponibilidad | Abierta | Hoy: al abrir el panel y en «Actualizar» |
| Q-26 | Qué ve el estudiante con la biblioteca cerrada | Abierta | — |

## Por qué Q-19 bloquea todo lo demás

El contrato local que la biblioteca publica hoy —`/v1/salud`, `/v1/catalogo`, `/v1/taxonomia`, `/v1/elemento/{ref}`, `/v1/mostrar`— devuelve un **catálogo plano de elementos**. Ninguna de esas rutas entrega un curso con secciones, lecciones e ítems, ni declara una versión vigente, ni emite los códigos lógicos sobre los que el expediente se escribe.

Mientras eso no exista, retirar las tablas de estructura de OPS deja al estudiante sin nada que recorrer. El orden de trabajo, por tanto, es: **primero el contrato del otro lado, después la eliminación de este**. La propuesta de contrato mínimo está en [06-contrato-biblioteca.md](06-contrato-biblioteca.md) y es una entrada para responder Q-19, no una decisión tomada.

## Riesgo principal

Si el contrato de estructura no llega a tiempo, la tentación será conservar «temporalmente» las tablas de curso en OPS. Eso reintroduce la doble verdad que este cambio existe para eliminar, y el trabajo de retirarlas se pagará dos veces. La mitigación aceptable es la contraria: mantener el prototipo actual intacto en su rama y no empezar la eliminación hasta que la biblioteca publique su contrato.


# Contrato del curso en Biblioteca  

escucharlo. Cada voz lleva: a qué material o pregunta acompaña, idioma, el texto
que dice y el archivo. La duración se lee del propio audio.

Hoy solo se puede registrar en la especificación técnica. La voz sintética sin
conexión no existe: los audios se graban o se traen hechos.

## 10. Requisitos de los medios

| Medio | Requisito |
|---|---|
| Imágenes | 1920×1080 (16:9). Figuras grandes, poco texto y fondo gris papel, no blanco: en 86 pulgadas el blanco deslumbra. Una idea por lámina |
| Video | `.mp4` o `.webm`, máximo 300 MB, a 1280×720 o 1920×1080 |
| Audio | `.mp3`, `.wav` o `.m4a`. Voz grabada |
| PDF | Exportado desde el original. Poco texto por página: se lee a cuatro metros |
| Interactivos | Entrada `index.html`. Sin internet, sin almacenamiento del navegador. Texto de 20 px o más, botones de 64 px o más, funciona a 1920×1080 y encogido. Ningún archivo interno pasa de 40 MB |
| Derechos | Resueltos antes. El sistema cifra y firma, no comprueba licencias de uso |

## 11. Reglas que se pagan caro si se rompen

1. **Los títulos son referencias.** Cambiar un título convierte el material en
   uno nuevo, y el examen que apuntaba al viejo deja de poder explicarse.
   Corregir una errata: sí, avisando al equipo técnico.
2. **Dos materiales no pueden llamarse igual**, ni siquiera en temas distintos.
   Mayúsculas, tildes y signos no cuentan: «Lámina» y «lamina» chocan. «Lámina»
   no es un título; «Lámina de la célula animal» sí.
3. **La clave del paquete no cambia.** Lo que sube es la versión.
4. **Nada de internet en los interactivos.** El aula no tiene conexión; una
   dirección externa deja la pantalla en blanco delante de treinta alumnos.
5. **Los códigos del índice son los oficiales** y los tipos, los del marco.
6. **Pregunta abierta, rúbrica obligatoria.**
7. **Se escribe para leerse a cuatro metros.** Una idea por lámina.

## 12. Pasos para registrar un curso nuevo

1. Copiar `contenido\PLANTILLA` a la ruta que toque (sección 3).
2. Rellenar `curso.txt` e `indice.txt`. Los dos traen las instrucciones dentro.
3. Crear una carpeta por tema, con su código delante, y meter el material numerado.
4. Revisar tantas veces como haga falta. No toca el material; solo regenera la
   página de las lecciones completas y avisa de lo que falta:

       py -3 paquetes\avacom_recolector.py revisar "contenido\CO\secundaria\08\matematicas"

5. Cuando salga limpio, armar. Genera la especificación y copia los medios:

       py -3 paquetes\avacom_recolector.py armar "contenido\CO\secundaria\08\matematicas"

6. Entregar al equipo técnico, que construye, verifica, cifra, firma y emite la
   licencia del aula. El paquete resultante se llama
   `avacom-<clave>-v<versión>`. La verificación es el **último momento** en que
   se puede leer el contenido en claro: ahí se hace la revisión pedagógica final.

Los dos comandos se ejecutan desde la carpeta raíz del proyecto, la que contiene
`contenido` y `paquetes`.

## 13. Lista de comprobación antes de entregar

- [ ] La ruta tiene la forma país, nivel, grado, materia.
- [ ] `curso.txt` con título, materia y descripción.
- [ ] `indice.txt` con los tipos reales del marco y los códigos oficiales.
- [ ] Cada carpeta de tema empieza por un código que está en `indice.txt`.
- [ ] Materiales numerados, títulos únicos y extensiones de la tabla.
- [ ] Cada pregunta tiene `R:` o `abierta`; hay `RUBRICA` si hay abiertas.
- [ ] Cada banco dice `extraer:` y tiene al menos el doble de preguntas.
- [ ] Interactivos con `index.html`, sin direcciones externas ni almacenamiento del navegador.
- [ ] Videos de menos de 300 MB. Derechos resueltos.
- [ ] `revisar` termina sin errores ni avisos.

## 14. Límites actuales y hallazgos

- **Las carpetas no expresan todo.** Voz, actividades por imagen, descripción
  por material, duración y páginas, objetivo por nodo y notas por paso de la
  lección solo se registran en la especificación técnica. Es lo que impide hoy
  hacer el curso de preescolar solo con carpetas.
- **Las evaluaciones no guardan opciones**, solo la respuesta. El visor pide
  respuesta escrita. Las actividades de preescolar necesitan que el formato
  defina las tres imágenes entre las que se elige.
- **Los nombres de tipo de pregunta difieren entre las dos vías** (por ejemplo
  «opción única» y «abierta» desde carpetas frente a «opción múltiple» y
  «respuesta abierta» en la técnica). Hoy el aula trata todas igual, pero
  conviene unificar el vocabulario antes de que el LMS dependa de él.
- **La duración de un video se declara, no se mide.** Nada la comprueba.
- **SCORM** no tiene visor; **banco** no lo tiene a propósito.
- **No hay editor visual** ni estados de borrador y aprobado. La revisión ocurre
  con `revisar` y con la verificación en claro, y depende de que alguien la haga.
- **Nadie valida que un código curricular exista.** Un código inventado se
  empaqueta igual de bien que uno correcto.

  