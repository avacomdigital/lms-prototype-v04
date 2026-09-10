# 06 · Contrato mínimo exigido a AVACOM Biblioteca

| Campo | Valor |
|---|---|
| Estado | **Propuesta.** Es una entrada para responder Q-19 y Q-20, no una decisión tomada |
| Consumidor | El backend de AVACOM OPS, único cliente |
| Transporte | Igual al vigente: loopback, puerto efímero de la nota de enlace, `X-Avacom-Ficha`, contrato declarado |

Sin este contrato, el backend de OPS no puede dejar de guardar la estructura del curso. Lo que hoy existe —catálogo plano de elementos— **no basta**: no entrega un curso, no declara una versión vigente y no emite códigos lógicos.

---

## 1 · Lo que ya existe y se conserva

| Ruta | Papel en el nuevo prototipo |
|---|---|
| `GET /v1/salud` | Estado, contrato, capacidades, contadores y señal de cambio |
| `GET /v1/catalogo` | Oferta de elementos con la política de la escuela ya aplicada |
| `GET /v1/taxonomia` | Árbol de clasificación |
| `GET /v1/elemento/{ref}` | Un elemento suelto |
| `POST /v1/mostrar` | Proyección de un material en el aula |

Reglas del transporte que no cambian: nota de enlace releída en cada llamada, claves en PascalCase o minúsculas, sólo `127.0.0.1`, tiempo de espera corto, comprobación de PID que no pueda terminar el proceso, y ausencia tratada como estado normal. Están descritas con detalle en [00-linea-base-conexion-biblioteca.md](00-linea-base-conexion-biblioteca.md).

---

## 2 · Lo que hay que añadir

### 2.1 · `GET /v1/cursos`

Los cursos publicados y ofrecidos a este equipo, con la política ya aplicada.

```json
{
  "generacion": 41,
  "cursos": [
    {
      "curso_ref": "cu-sec-mat-8-algebra",
      "titulo": "Álgebra Octavo B",
      "version_vigente": "2.1.0",
      "nivel": "secundaria",
      "grado": "8",
      "asignatura": "Matemáticas",
      "marco": "SEP México",
      "lecciones": 3,
      "actualizado_en": 1757000000000
    }
  ]
}
```

`curso_ref` es la referencia estable de Q-20: la emite la biblioteca, no cambia entre versiones y es lo que OPS escribe en cada fila de expediente.

### 2.2 · `GET /v1/curso/{curso_ref}`

El árbol completo de la versión vigente. Es lo que OPS proyecta al estudiante sin guardar nada.

```json
{
  "curso_ref": "cu-sec-mat-8-algebra",
  "titulo": "Álgebra Octavo B",
  "version": "2.1.0",
  "huella": "9f1c…",
  "secciones": [
    {
      "codigo": "sec.funciones",
      "titulo": "Funciones",
      "orden": 1,
      "lecciones": [
        {
          "codigo": "lec.funcion-lineal",
          "titulo": "Función lineal y razón de cambio",
          "orden": 1,
          "calificable": true,
          "items": [
            {"orden": 1, "tipo": "leccion",    "elemento_ref": "co-sec-mat-lec-funcion"},
            {"orden": 2, "tipo": "video",      "elemento_ref": "co-sec-mat-video-pendiente"},
            {"orden": 3, "tipo": "evaluacion", "evaluacion_ref": "co-sec-mat-eval-funcion", "puntaje_maximo": 100}
          ]
        }
      ]
    }
  ]
}
```

Exigencias sobre `codigo`:

- Es la **identidad lógica** de la sección y de la lección, y es lo único que hace que el progreso sobreviva a un cambio de versión.
- Es estable entre versiones para la misma unidad conceptual.
- Si una versión nueva renombra o divide una unidad, la biblioteca debe publicar la equivalencia o declarar que el código anterior desaparece (Q-12). No se puede dejar que OPS lo adivine.

### 2.3 · `GET /v1/curso/{curso_ref}/manifiesto`

Respuesta diminuta para poder preguntar a menudo: `curso_ref`, `version`, `huella`, `actualizado_en`. Es el equivalente por curso de la huella de catálogo que ya se usa para el conjunto.

### 2.4 · `GET /v1/evaluacion/{evaluacion_ref}` · capacidad `evaluacion`

Enunciados y opciones **sin ningún indicador de corrección**. Ya está previsto en el contrato vigente y hoy no se publica; deja de ser opcional en el nuevo prototipo, porque sin él no hay evaluaciones.

```json
{
  "evaluacion_ref": "co-sec-mat-eval-funcion",
  "version": "2.1.0",
  "titulo": "Evaluación · Función lineal",
  "puntaje_maximo": 100,
  "preguntas": [
    {"ref": "pr-001", "orden": 1, "enunciado": "…",
     "opciones": [{"ref": "op-a", "texto": "…"}, {"ref": "op-b", "texto": "…"}]}
  ]
}
```

Una prueba de OPS debe recorrer recursivamente esta respuesta buscando `es_correcta`, `correcta`, `clave` y variantes, y fallar si aparecen.

### 2.5 · `POST /v1/comprobar` · capacidad `comprobar`

```json
→ {"pregunta_ref": "pr-001", "respuesta": {"opcion_ref": "op-b"}}
← {"acierta": true, "retroalimentacion": "…"}
```

La clave se compara donde vive. OPS guarda el veredicto y la retroalimentación, nunca la clave.

### 2.6 · Cálculo de la nota (Q-22)

Dos alternativas, y hay que elegir una:

| Alternativa | Quién calcula | Consecuencia |
|---|---|---|
| **A** · veredicto por pregunta | OPS suma los veredictos y aplica `puntaje_maximo` | OPS conserva la regla de ponderación; la biblioteca sólo corrige |
| **B** · `POST /v1/calificar` | La biblioteca devuelve la nota del intento completo | OPS no calcula nada; la regla vive con el contenido |

La línea base implementa el equivalente de A (`aciertos × puntaje_máximo ÷ total`). A es el camino de menor cambio y no debilita ninguna regla, porque el veredicto ya viene de la biblioteca.

---

## 3 · Señal de cambio

Se conserva la preferencia vigente, y conviene que la biblioteca publique el primer nivel para retirar los otros dos:

1. `generacion` — contador monótono, lo más fiable.
2. `huella_catalogo` — cambia cuando cambia el catálogo.
3. Contadores (`elementos`, `paquetes`, `politicas`) — último recurso; no detecta un cambio que deje los totales iguales.

---

## 4 · Capacidades

`GET /v1/salud` declara `capacidades`. Un componente que no las declare equivale a la lista vacía. OPS **no simula** ninguna: sin `evaluacion` no entrega preguntas, y sin `comprobar` no produce nota, lo que deja el intento en `pendiente_correccion` en lugar de calificarlo por suposición.

| Capacidad | Efecto de su ausencia en OPS |
|---|---|
| `curso` (nueva) | No se puede abrir ningún curso; el expediente sigue consultable |
| `evaluacion` | No hay preguntas que entregar; 501 explicativo |
| `comprobar` | No hay veredicto ni nota; intento pendiente |
| `medio` | El material no se puede proyectar |
| `repaso` | No se apunta la consulta libre. **No** genera intento ni nota en ningún caso |
| `banco` | No hay extracción por persona |

---

## 5 · Errores

| Situación | Estado | OPS responde |
|---|---|---|
| Ficha ausente o inválida | 401 | 502 con el detalle |
| Referencia inexistente | 404 | 404 con la referencia, sin inventar un título |
| Capacidad no publicada | 501 | 501 con la lista de capacidades |
| Componente cerrado o nota ausente | — | 503 con motivo y sugerencia |

## 6 · Lo que el contrato NO debe ofrecer

- Ninguna ruta que permita a OPS **crear o modificar** un curso, una sección, una lección, un ítem o una pregunta. Si existiera, la frontera dependería otra vez de la disciplina del cliente.
- Ninguna respuesta que incluya una clave de corrección.
- Ningún acceso a la base de la biblioteca ni a sus paquetes cifrados: OPS habla sólo con su API.
