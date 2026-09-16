# 03 · Módulo de acceso · Casos de uso del backend

| Campo | Valor |
|---|---|
| Para qué sirve | Entender el código ya escrito en `backend/acceso/`: qué hace cada operación, por dónde viaja la información y qué pantalla del frontend la va a usar |
| Para quién | Programadores que van a tocar el módulo **y** personas no técnicas que necesitan saber qué hace el sistema |
| Alcance | 35 casos de uso · 27 rutas HTTP · 22 serializers · 17 tablas · 2 migraciones · 1 comando de consola |
| Documentos hermanos | [01 · Modelado de datos](01-modelado-datos.md) · [02 · Endpoints](02-Endpoints.md) · [Presentación](../../specs/presentaciones/acceso.html) · [Pantallas MAUI](../../specs/presentaciones/acceso-sugerencias.html) |
| Estado del código | Implementado y probado: 97 pruebas en verde (65 de este módulo) |

> **Cómo leer este documento.** Las secciones 1 a 3 explican el mecanismo general con una sola analogía y un ejemplo completo. La sección 4 recorre los 35 casos de uso uno por uno. Si sólo va a leer una cosa, lea la sección 3: el viaje de una petición. Si no programa, puede saltarse los bloques de código; el texto se entiende sin ellos.

---

## 1 · La idea en una página

### 1.1 · Qué es un «caso de uso»

Un caso de uso es **una cosa completa que alguien quiere hacer**: «crear un estudiante», «entrar al sistema», «restablecer un PIN», «autorizar una tableta para el examen». No es un botón ni una pantalla ni una tabla: es la operación entera, con todas sus reglas y todas sus consecuencias.

En este módulo cada caso de uso es una clase de Python con un único método `ejecutar(...)`. Eso tiene una ventaja muy concreta: **para saber todo lo que pasa cuando el profesor restablece un PIN, sólo hay que leer una clase**, no perseguir el código por seis archivos.

### 1.2 · La analogía de la oficina

Piense en una oficina de secretaría académica:

| En la oficina | En el código | Dónde vive |
|---|---|---|
| La **ventanilla** donde el público entrega formularios y recibe respuestas | La capa HTTP: vistas (APIViews) y serializers | `acceso/interfaces/` |
| El **formulario en papel**, que se revisa antes de aceptarlo: ¿está firmado? ¿tiene todos los campos? | Los serializers | `acceso/interfaces/serializers.py` |
| El **funcionario** que tramita la gestión completa de principio a fin | El caso de uso | `acceso/aplicacion/casos_uso.py` |
| El **reglamento** de la institución que el funcionario debe respetar | El dominio: políticas, entidades y valores | `acceso/dominio/` |
| El **archivo** donde se guardan y se buscan los expedientes | Los repositorios | `acceso/infraestructura/repositorios.py` |
| La **carpeta** de una gestión, que se entrega completa o no se entrega | La Unidad de Trabajo | `acceso/infraestructura/unidad_trabajo.py` |
| La **caja fuerte** y la trituradora: lo que cifra, lo que sella | Argon2id, AES-GCM, HMAC, JWT | `acceso/infraestructura/seguridad.py` |
| Los **muebles y estanterías** del archivo | Las tablas de la base de datos | `acceso/models.py` |
| El día que se **montó la oficina** por primera vez | Las migraciones | `acceso/migrations/` |
| La **puerta de servicio** para el personal técnico, sin pasar por ventanilla | El comando de consola | `acceso/management/commands/` |

La regla que sostiene todo el diseño: **el funcionario no sabe cómo es el archivo por dentro**. Pide «tráeme el expediente de Juan» y alguien se lo trae. Hoy el archivo son carpetas de papel (SQLite con Django); mañana puede ser un sistema digital (PostgreSQL con SQLAlchemy) y el funcionario trabaja igual, sin reentrenarse.

### 1.3 · Las seis carpetas del módulo

```
backend/acceso/
├── dominio/              EL REGLAMENTO. No sabe que existe internet ni bases de datos.
│   ├── valores.py          Tipos con reglas propias: un país es "CO", no "Colombia"
│   ├── entidades.py        Las cosas del negocio: Usuario, Credencial, Sesión...
│   ├── politicas.py        Las tres decisiones difíciles: ¿puede? ¿es buena la clave? ¿está bloqueado?
│   ├── plantillas.py       Los roles y permisos de fábrica
│   └── errores.py          Los "no" posibles, cada uno con su motivo
│
├── aplicacion/           LOS FUNCIONARIOS.
│   ├── casos_uso.py        Las 35 operaciones. Este es el corazón del módulo
│   └── puertos.py          Lo que los funcionarios necesitan pedir (sin decir a quién)
│
├── infraestructura/      QUIEN HACE EL TRABAJO SUCIO.
│   ├── repositorios.py     Leer y escribir en la base, cifrando al pasar
│   ├── unidad_trabajo.py   La transacción: todo o nada
│   ├── seguridad.py        Argon2id, AES-256-GCM, HMAC-SHA-256, JWT
│   └── contenedor.py       El armador: junta cada pieza con la que le toca
│
├── interfaces/           LA VENTANILLA (Django REST Framework).
│   ├── views.py            Las APIViews: reciben HTTP, llaman al caso de uso, devuelven JSON
│   ├── serializers.py      Revisan la forma del formulario
│   ├── autenticacion.py    Lee el pase de entrada (JWT) en cada petición
│   ├── permisos.py         ¿Esta ruta exige sesión?
│   └── urls.py             El directorio: qué dirección lleva a qué ventanilla
│
├── management/commands/  LA PUERTA DE SERVICIO.
│   └── acceso_instalar.py  Instalar el equipo desde la consola
│
├── migrations/           EL MONTAJE DE LA OFICINA.
│   ├── 0001_initial.py     Crea las 17 tablas
│   └── 0002_plantillas.py  Siembra permisos y los tres roles de fábrica
│
├── models.py             LAS ESTANTERÍAS: la forma de las tablas
└── tests/                LAS PRUEBAS: 65 comprobaciones automáticas
```

### 1.4 · La regla de oro del diseño

**El reglamento no puede depender de la tecnología.** Ni `dominio/` ni `aplicacion/` mencionan Django, Django REST Framework, FastAPI, SQLAlchemy ni Pydantic. No es una intención: hay una prueba automática que recorre esos archivos y **falla** si alguien escribe uno de esos nombres.

```python
# acceso/tests/test_arquitectura.py
def test_dominio_y_aplicacion_no_importan_frameworks(self):
    ...
    self.assertEqual(violaciones, [])
```

Por qué importa, en términos de negocio: la regla «un PIN no puede ser 123456» y la regla «un profesor sólo administra a sus estudiantes» son de AVACOM, no de Django. Si algún día el backend cambia de tecnología, esas reglas y sus pruebas sobreviven intactas. Sólo se reescribe la ventanilla y el archivo.

---

## 2 · Los tres conceptos que aparecen en todos los casos de uso

Antes de recorrer las operaciones conviene conocer tres palabras que se repiten.

### 2.1 · `Principal`: quién está actuando

Cuando alguien inicia sesión recibe un **pase de entrada** (un JWT). En cada petición posterior lo presenta, y el backend lo convierte en un objeto llamado `Principal`: la ficha de quien actúa.

```python
Principal(
    usuario_id="a1b2…",        # quién es
    organizacion_id="c3d4…",   # de qué colegio
    rol_codigo="TEACHER",      # qué rol tiene
    menu="teacher",            # qué menú le toca en la app
    nivel=2,                   # 1 estudiante · 2 docente · 3 administración
    sesion_id="e5f6…",         # cuál de sus sesiones es esta
    clase_sesion=NORMAL,       # NORMAL o TEMPORAL (pase de examen)
    debe_cambiar_credencial=False,
    dispositivo_id="…",        # desde qué tableta
    evaluacion_ref=None,       # si el pase es sólo para un examen
)
```

Casi todos los casos de uso reciben un `Principal` como primer argumento. Los que no lo reciben son justamente los que ocurren **antes** de tener sesión: consultar la configuración, instalar, registrar la tableta, autenticarse y canjear un pase de examen.

### 2.2 · Permiso y alcance: «qué» y «sobre quién»

Un permiso solo no dice nada útil. `student.progress.read` (ver el progreso de un estudiante) significa cosas distintas según quién lo tenga:

| Alcance | Significa | Ejemplo |
|---|---|---|
| `SELF` | Sólo sobre sí mismo | Juan ve **su** progreso |
| `ASSIGNED_GROUPS` | Sobre los estudiantes de sus grupos | La profesora ve el progreso de **su** curso |
| `ORGANIZATION` | Sobre todo el colegio | El rector ve el de **cualquiera** |

La pregunta «¿es Juan mi estudiante?» **no se guarda en ninguna tabla de permisos**: se calcula. Existe un grupo donde yo soy docente vigente y Juan es miembro vigente, luego Juan es mi estudiante. Esto es lo que evita la tabla gigantesca de permisos por contexto que se descartó en el diseño.

### 2.3 · La Unidad de Trabajo: todo o nada

Casi todos los casos de uso empiezan igual:

```python
with self.s.uow() as uow:
    ...
```

Esa línea abre una **carpeta de gestión**. Todo lo que se escriba dentro se guarda de golpe al final, o no se guarda nada si algo falla. Crear un estudiante son siete escrituras (cuenta, datos cifrados, identificadores, credencial, inscripción al grupo, auditoría y aviso de sincronización); si la quinta falla, no queda medio estudiante en la base.

Hay **una excepción deliberada**: `AutenticarUsuario` y `CanjearAccesoTemporal` usan `ejecutar_registrando(...)`, que confirma la transacción **aunque la operación termine en error**. La razón: si alguien falla la clave cinco veces, esos cinco fallos tienen que quedar escritos, porque son justamente lo que dispara el bloqueo. Si se deshicieran junto con el error, nadie se bloquearía nunca.

---

## 3 · El viaje completo de una petición

Este es el ejemplo más didáctico del documento. Seguimos un caso real de principio a fin: **Juan, estudiante de octavo, entra a su tableta**.

### 3.1 · Lo que ocurre en la pantalla

Juan toca su tableta. Aparece un teclado numérico grande. Escribe su código, `122499`, y su PIN, `691302`. Toca el botón verde. Un segundo después ve su menú con sus asignaturas.

### 3.2 · Lo que ocurre por dentro

```
   TABLETA (.NET MAUI)
        │  POST http://192.168.1.10:8000/api/acceso/sesiones/
        │  { "identificador": "122499", "secreto": "691302", "dispositivo": "a8f3…" }
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 1. urls.py            "sesiones/" → SesionesView                      │
├───────────────────────────────────────────────────────────────────────┤
│ 2. views.py           SesionesView.post()                             │
│                       Es VistaPublica: no exige sesión previa         │
├───────────────────────────────────────────────────────────────────────┤
│ 3. serializers.py     LoginEntrada revisa la FORMA del formulario:    │
│                       ¿vienen los dos campos? ¿son texto? ¿caben?     │
│                       NO revisa si la clave es correcta: eso no es    │
│                       forma, es negocio                               │
├───────────────────────────────────────────────────────────────────────┤
│ 4. contenedor.py      Entrega las herramientas: archivo, caja fuerte, │
│                       sellador de pases, reloj y generador de azar    │
├───────────────────────────────────────────────────────────────────────┤
│ 5. casos_uso.py       AutenticarUsuario.ejecutar(…)  ← EL FUNCIONARIO │
│                       Abre la carpeta de gestión                      │
└───────────────────────────────────────────────────────────────────────┘
        │
        ├─ a) dominio/valores.py · DocumentNumber.normalizar_entrada()
        │     "122499" → "122499".  Si fuera "1.042.888-795" → "1042888795"
        │     Así el mismo documento escrito de tres formas es el mismo documento
        │
        ├─ b) infraestructura/seguridad.py · cifrador.indice()
        │     Convierte el código en una huella HMAC de 64 caracteres.
        │     Los identificadores están CIFRADOS en la base: no se puede buscar
        │     "122499" directamente. Se busca su huella, que sí es siempre igual
        │
        ├─ c) infraestructura/repositorios.py · usuarios.por_identificador(huella)
        │     Encuentra a Juan.  Si no lo encontrara, el código verifica igual
        │     contra un hash señuelo, para que "no existe" tarde lo mismo que
        │     "clave incorrecta" y nadie pueda adivinar quién está matriculado
        │
        ├─ d) casos_uso.py · politica_de(usuario, rol)
        │     Busca el reglamento del perfil "student" de ese colegio,
        │     y si su grupo tiene reglamento propio, ese manda
        │
        ├─ e) dominio/entidades.py · politica.admite_identificador(CODIGO)
        │     ¿Este colegio deja entrar con código estudiantil? Sí
        │
        ├─ f) dominio/politicas.py · PoliticaBloqueo.evaluar(intentos, politica)
        │     ¿Juan viene de fallar cinco veces? No. Puede seguir
        │
        ├─ g) infraestructura/seguridad.py · hasher.verificar(hash, "691302")
        │     Argon2id compara. La base NUNCA guardó el PIN, sólo una huella
        │     irreversible. Ni el programa ni nosotros podemos leer su PIN
        │
        ├─ h) repositorios · intentos.registrar(EXITO)
        │     Queda constancia del acceso
        │
        ├─ i) casos_uso.py · abrir_sesion()
        │     Crea la fila de sesión y pide a seguridad.py un JWT firmado,
        │     con caducidad de cuatro horas
        │
        └─ j) auditoría + outbox
              Un apunte legible para el profesor y un aviso por si algún día
              hay una sede central con la que sincronizar
        │
        ▼  Se cierra la carpeta: TODO lo anterior se confirma de golpe
┌───────────────────────────────────────────────────────────────────────┐
│ 6. views.py           Devuelve el diccionario tal cual, como JSON      │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
   TABLETA guarda el pase en el almacén seguro del dispositivo
        │  GET /api/acceso/yo/   con el pase en la cabecera
        ▼
   Recibe menú "student", permisos y grupos → pinta el menú del estudiante
```

### 3.3 · Las tres cosas que este viaje enseña

1. **La vista es muy corta a propósito.** `SesionesView.post()` tiene tres líneas: validar la forma, llamar al caso de uso, devolver. Toda la inteligencia está en el caso de uso, y por eso se puede probar sin levantar un servidor.
2. **El dominio decide, la infraestructura obedece.** Quién puede entrar lo decide `politicas.py`, que no sabe qué es una base de datos. Cómo se guarda lo resuelve `repositorios.py`, que no decide nada.
3. **Los datos sensibles cambian de forma al cruzar la frontera.** El código de Juan entra en texto, se guarda cifrado y se busca por huella. Su PIN entra en texto y nunca se guarda: sólo su huella Argon2id. Esa conversión ocurre siempre en el mismo sitio, la infraestructura, y nunca en la vista ni en el caso de uso.

---

## 4 · Los 35 casos de uso, uno por uno

Cada ficha tiene la misma estructura:

- **Qué hace**, en una frase sin tecnicismos
- **Ruta HTTP** y ejemplo real
- **Recorrido**: por qué capas pasa
- **Pantalla** del frontend que lo consume (códigos de [acceso-sugerencias.html](../../specs/presentaciones/acceso-sugerencias.html))

---

### Familia A · Arranque y dispositivos

#### A.1 · `InstalarNodo`

**Qué hace.** Es el día cero del equipo del aula. Resuelve un problema de huevo y gallina: para crear usuarios hace falta un administrador, y para crear al administrador hacen falta permisos que nadie tiene todavía. De una sola vez crea el colegio, le pone reglamento de acceso a cada perfil y crea a la primera persona, que es administradora.

**Ruta.** `POST /api/acceso/instalacion/` · pública · una única vez en la vida del equipo.

```bash
curl -X POST http://127.0.0.1:8000/api/acceso/instalacion/ -H "Content-Type: application/json" -d '{
  "organizacion": {"codigo":"IE-SANJOSE","nombre":"IE San José","pais":"CO","idioma":"es","locale":"es-CO"},
  "administrador": {"alias":"Rectoría","nombres":"Ana","apellidos":"Pérez","dni":"1042888795"}
}'
```

Respuesta:

```json
{ "organizacion": { "id": "…", "codigo": "IE-SANJOSE", "locale": "es-CO" },
  "administrador": { "id": "…", "alias": "Rectoría" },
  "password_inicial": "cozzz4S.3%B8" }
```

**Recorrido.**

| Paso | Capa | Qué pasa |
|---|---|---|
| 1 | `interfaces/serializers.py` · `InstalacionEntrada` | Comprueba que vengan organización y administrador con sus campos |
| 2 | `aplicacion/casos_uso.py` · `InstalarNodo` | Abre la carpeta. Si ya hay un colegio → **409** `ya_instalado`. Esto impide que alguien en la red se fabrique un administrador nuevo |
| 3 | `aplicacion/casos_uso.py` · `asegurar_plantillas()` | Se asegura de que existan el catálogo de permisos y los roles de fábrica (ya los sembró la migración, pero se comprueba) |
| 4 | `dominio/valores.py` | `CountryCode`, `LanguageCode` y `LocaleCode` validan los formatos internacionales: `CO`, `es`, `es-CO`. Si llega «Colombia», se rechaza |
| 5 | `dominio/plantillas.py` · `POLITICAS_POR_DEFECTO` | De aquí salen los tres reglamentos: estudiantes con código y PIN, docentes con documento y contraseña, administración con contraseña larga |
| 6 | `CrearUsuario._crear()` | Crea a la administradora reutilizando el mismo código que usará el profesor después. `creado_por=None`: es la única persona a la que no la creó nadie |
| 7 | `infraestructura/seguridad.py` | Si no mandaron contraseña, se genera una y se guarda su huella Argon2id |
| 8 | auditoría + outbox | Queda constancia de la instalación |

**Detalle importante.** `password_inicial` se devuelve **una sola vez**. De la contraseña sólo se guarda una huella irreversible; no hay forma de volver a consultarla. Quien instala tiene que anotarla.

**Pantalla.** Idealmente ninguna: lo hace el instalador de Windows, que sí corre con teclado. Si el equipo llega sin instalar, OPS detecta `acceso.instalado: false` en `/health/` y abre el asistente **A2 · primer arranque**.

---

#### A.2 · `ConsultarConfiguracion`

**Qué hace.** Le dice a la app **cómo debe pintar la pantalla de acceso**, sin revelar ningún dato de ninguna persona. Es la razón por la que el mismo programa sirve para un colegio de primaria y para una universidad.

**Ruta.** `GET /api/acceso/configuracion/` · pública.

```json
{ "instalado": true,
  "organizacion": { "codigo": "IE-SANJOSE", "nombre": "IE San José", "locale": "es-CO" },
  "perfiles": {
    "student": { "tipo_identificador": "CODIGO_ESTUDIANTIL", "tipo_secreto": "PIN", "longitud_minima": 6, "permite_acceso_temporal": true },
    "teacher": { "tipo_identificador": "DNI", "tipo_secreto": "PASSWORD", "longitud_minima": 8, "permite_acceso_temporal": false }
  },
  "duracion_sesion_min": 240,
  "claves_derivadas": true }
```

**Recorrido.** Vista pública → caso de uso → repositorio de organización y políticas. No toca dominio ni seguridad, salvo para preguntar si las claves de cifrado son las derivadas del prototipo.

**Cómo lo usa el frontend.** Si `tipo_secreto` es `PIN`, la app muestra teclado numérico y pide seis dígitos. Si es `PASSWORD`, muestra teclado completo en pantalla. La etiqueta del primer campo cambia entre «Código», «Documento» y «Correo». **Nada de esto está escrito en la app.**

**Pantalla.** S1 y S2 (tableta), O1 (nodo del profesor). Es la primera llamada de todas.

---

#### A.3 · `RegistrarDispositivo`

**Qué hace.** La tableta se presenta al aula y dice «soy esta». El profesor la verá luego como «tableta-07» cuando tenga que autorizarla para un examen.

**Ruta.** `POST /api/acceso/dispositivos/` · pública · **idempotente** (se puede llamar mil veces sin duplicar nada).

```bash
curl -X POST .../api/acceso/dispositivos/ -d '{"identificador":"a8f3-hw-id","nombre":"tableta-07","tipo":"TABLETA"}'
```

Devuelve **201** la primera vez y **200** las siguientes, actualizando la hora de última conexión.

**Recorrido.** `DispositivoEntrada` valida la forma → el caso de uso busca por identificador; si existe, actualiza; si no, crea. El `identificador` lo genera la app una vez y lo guarda en el almacén seguro del sistema operativo.

**Pantalla.** S1 · Conectar al aula. Sucede de forma invisible al conectar.

---

#### A.4 · `ListarDispositivos` y A.5 · `ActualizarDispositivo`

**Qué hacen.** Ver las tabletas del aula y darlas de baja o renombrarlas. Dar de baja una tableta **revoca sus sesiones abiertas**: si una tableta se pierde, deja de servir de inmediato.

**Rutas.** `GET /api/acceso/dispositivos/` y `PATCH /api/acceso/dispositivos/{id}/`.

**Detalle de permisos.** Listar lo puede hacer quien tenga `device.manage` (administración) **o** `exam.temporary_access.grant` (el profesor), porque el profesor necesita ver las tabletas para elegir cuál autorizar. Modificarlas es sólo de administración.

**Pantallas.** O3 (elegir tableta al autorizar un examen) y A1 · pestaña Tabletas.

---

### Familia B · Entrar, estar y salir

#### B.1 · `AutenticarUsuario`

**Qué hace.** La operación más usada del sistema: comprobar quién es alguien y entregarle un pase de entrada válido por cuatro horas. Ya la recorrimos entera en la sección 3.

**Ruta.** `POST /api/acceso/sesiones/` · pública.

**Las cuatro defensas que aplica, en orden.**

| Defensa | Qué evita |
|---|---|
| Mismo error y mismo tiempo para «no existe» y «clave incorrecta» | Que alguien descubra quién está matriculado probando códigos |
| El tipo de identificador debe estar permitido por el reglamento | Que un estudiante entre con su documento cuando el colegio dijo «aquí se entra con el código» |
| Bloqueo tras cinco fallos en quince minutos | Que alguien pruebe PIN uno por uno hasta acertar |
| Argon2id, deliberadamente lento | Que robar la base de datos sirva para adivinar las claves |

**Respuestas posibles.**

| Código | Significa | Qué hace la app |
|---|---|---|
| 200 | Adelante | Guarda el pase. Si `debe_cambiar_credencial`, va a la pantalla de cambio |
| 401 | Código o clave incorrectos | «Te quedan N intentos», con el número que devuelve el backend |
| 423 | Bloqueado | Pantalla de espera con cuenta regresiva |

**Pantallas.** S2 (estudiante) y O1 (profesor).

---

#### B.2 · `ResolverPrincipal`

**Qué hace.** Es el **portero invisible**. No tiene ruta propia: se ejecuta automáticamente en *cada* petición que traiga un pase de entrada, antes de que la vista vea nada.

**Recorrido.** `interfaces/autenticacion.py` · `AutenticacionJwt` lee la cabecera `Authorization: Bearer …` → llama a este caso de uso → comprueba cuatro cosas contra la base:

1. La firma del pase es válida y no ha caducado.
2. La sesión existe y no fue revocada.
3. La cuenta sigue activa.
4. Si la credencial es provisional, lo marca en el `Principal`.

**Por qué comprueba contra la base y no se fía del pase.** Porque el pase dura cuatro horas, y en ese rato pueden pasar cosas: el profesor cierra la sesión del estudiante, el rector suspende una cuenta, alguien cambia de rol. Al mirar la base en cada petición, esas decisiones **surten efecto en el instante**, sin esperar a que el pase caduque.

**Detalle de diseño.** Si no viene cabecera, este caso de uso no se ejecuta y el visitante queda como anónimo. Por eso añadir autenticación al proyecto **no rompió ninguna ruta anterior** del expediente ni de la biblioteca.

---

#### B.3 · `ConsultarIdentidad`

**Qué hace.** Responde «¿quién soy y qué puedo hacer aquí?». Es lo que decide qué menú ve cada persona.

**Ruta.** `GET /api/acceso/yo/` · con sesión.

```json
{ "usuario": { "id": "…", "alias": "Prof. Gómez", "rol": "TEACHER", "menu": "teacher", "nivel": 2,
               "persona": { "nombres": "Luis", "apellidos": "Gómez" } },
  "permisos": [ { "codigo": "credential.reset", "alcance": "ASSIGNED_GROUPS", "origen": "rol", "vigente_hasta": null },
                { "codigo": "audit.read", "alcance": "ORGANIZATION", "origen": "adicional", "vigente_hasta": 1791000000000 } ],
  "grupos": [ { "codigo": "8A", "nombre": "Octavo A", "papel": "DOCENTE" } ],
  "sesion": { "clase": "NORMAL", "expira_en": 1789014400000, "dispositivo": "master" } }
```

**Recorrido.** Vista → caso de uso → arma el «contexto» del actor (rol + permisos extra + grupos donde es docente) → pregunta a `dominio/politicas.py` el alcance real de cada permiso → descifra los datos personales sólo para su propio dueño.

**Por qué `alcance_concedido` se pregunta permiso a permiso.** Porque hay situaciones que recortan permisos sobre la marcha. Quien tiene una clave provisional sólo puede cambiarla. Quien entró con el pase de examen sólo puede rendir ese examen. Lo que aquí queda fuera, la app ni siquiera lo dibuja.

**La ventaja práctica.** Si mañana el rector concede un permiso extra a una coordinadora, ella lo ve al volver a entrar. **Sin actualizar ni reinstalar nada** en los equipos del aula.

**Advertencia que conviene repetir.** Esto sirve para dibujar la pantalla, no para proteger nada. Cada vez que alguien pulsa un botón, el servidor vuelve a comprobar el permiso por su cuenta. Ocultar un botón es comodidad; la seguridad está en la comprobación del servidor.

**Pantallas.** Todas las de después del acceso: S6, O2, A1, A2.

---

#### B.4 · `CambiarCredencialPropia`

**Qué hace.** Cambiar la propia clave. Es obligatorio la primera vez y después de que un profesor la restablezca.

**Ruta.** `PUT /api/acceso/yo/credencial/` · `{ "secreto_actual": "204915", "secreto_nuevo": "480215" }`

**Cuatro reglas que aplica.**

1. La clave actual debe ser correcta, aunque ya esté con sesión abierta.
2. La nueva debe cumplir el reglamento del colegio (`PoliticaFortaleza`): largo, mayúsculas, símbolos, y nada de PIN triviales como `123456` o `111111`.
3. No puede repetir ninguna de las tres últimas claves.
4. Al cambiarla, **se cierran las demás sesiones** de esa persona y se conserva la actual.

**Por qué la regla 4.** Si alguien cambió la clave porque sospecha que se la vieron, lo que quiere es echar al intruso. Si sus sesiones siguieran abiertas, cambiar la clave no serviría de nada.

**Respuesta a una clave débil:**

```json
{ "detail": "La clave no cumple la política del colegio.", "codigo": "secreto_debil",
  "reglas": ["Debe incluir al menos una letra mayúscula.", "Debe incluir al menos un símbolo (p. ej. . , ! # $ %)."] }
```

La lista `reglas` está redactada para **mostrarse tal cual en pantalla**. El frontend no tiene que traducir códigos ni duplicar las reglas del colegio.

**Pantallas.** S4 (estudiante) y el equivalente en O1 para el profesor.

---

#### B.5 · `RevocarSesion` · B.6 · `ListarSesiones`

**Qué hacen.** Cerrar sesión y ver quién está conectado.

**Rutas.** `DELETE /api/acceso/sesiones/actual/` (la propia), `DELETE /api/acceso/sesiones/{id}/` (la de otro) y `GET /api/acceso/sesiones/`.

**Un caso de uso, dos permisos.** `RevocarSesion` mira si la sesión es propia o ajena. Si es propia pide `session.revoke_own`, que todo el mundo tiene. Si es ajena pide `session.revoke` sobre su dueño, que el profesor sólo tiene sobre sus estudiantes. El motivo queda anotado: `logout`, `docente` o `administrador`.

**Es idempotente.** Revocar una sesión ya revocada devuelve 204 igual, sin error. Si la red falla y la app reintenta, no pasa nada raro.

**Pantallas.** Botón «Salir» en S6 y O2; acción «Cerrar sesión» en la lista de estudiantes O2; pestaña Sesiones activas en A2.

---

### Familia C · Personas

#### C.1 · `CrearUsuario`

**Qué hace.** Matricular a alguien: cuenta, datos personales cifrados, identificadores, primera clave y, si corresponde, inscripción a un grupo. Todo en una sola carpeta de gestión.

**Ruta.** `POST /api/acceso/usuarios/`

```bash
curl -X POST .../api/acceso/usuarios/ -H "Authorization: Bearer $TOKEN" -d '{
  "rol": "STUDENT",
  "alias": "Juan P.",
  "persona": {"nombres":"Juan","apellidos":"Pérez","fecha_nacimiento":"2012-04-09"},
  "identificadores": [{"tipo":"CODIGO_ESTUDIANTIL","valor":"122499","es_login":true},
                      {"tipo":"DNI","valor":"1.020.334.556","es_login":false}],
  "grupo_id": "…"
}'
```

Como no se mandó `secreto`, el backend genera un PIN y lo devuelve **una sola vez**:

```json
{ "id": "…", "alias": "Juan P.", "rol": "STUDENT", "debe_cambiar_credencial": true,
  "secreto_inicial": "204915",
  "identificadores": [ { "tipo": "CODIGO_ESTUDIANTIL", "valor": "122499", "es_login": true } ],
  "grupos": [ { "codigo": "8A", "papel": "ESTUDIANTE" } ] }
```

**Recorrido detallado.**

| Paso | Capa | Qué pasa |
|---|---|---|
| 1 | `serializers.py` · `UsuarioEntrada` | Forma del formulario: rol, alias, persona, al menos un identificador |
| 2 | `casos_uso.py` | Pregunta su alcance sobre `user.create`. Con `ASSIGNED_GROUPS` (profesor) sólo puede crear estudiantes y **debe** indicar uno de sus grupos. Con `ORGANIZATION` puede crear cualquier rol de nivel igual o inferior al suyo |
| 3 | `dominio/valores.py` · `DocumentNumber` | Normaliza cada identificador. `1.020.334.556` y `1020334556` son el mismo documento |
| 4 | `repositorios.py` · `existe_identificador()` | Comprueba por huella que ese código no sea ya de otra persona → **400** `identificador_duplicado` |
| 5 | `repositorios.py` · `guardar_persona()` | Cifra nombres, apellidos, fecha de nacimiento y teléfono con AES-256-GCM al escribir |
| 6 | `dominio/politicas.py` · `PoliticaFortaleza` | Si mandaron clave, la valida. Si no, se genera una que cumpla el reglamento |
| 7 | `infraestructura/seguridad.py` | Argon2id sobre la clave |
| 8 | grupos + auditoría + outbox | Inscripción y constancia |

**El detalle de `secreto_definitivo`.** Por defecto, una clave puesta por otra persona nace como provisional y el dueño debe cambiarla al entrar. Algunos colegios prefieren que el docente asigne un PIN fijo a niños pequeños: para eso existe `"secreto_definitivo": true` junto con un `secreto` explícito.

**Si algo falla, no queda rastro.** Una prueba lo comprueba: intentar crear un estudiante con PIN débil deja exactamente el mismo número de usuarios, credenciales y eventos que había antes.

**Pantalla.** O5 · Nuevo estudiante. La respuesta con `secreto_inicial` se muestra como O4, en dígitos grandes, con «Ya lo anoté».

---

#### C.2 · `ListarUsuarios` · C.3 · `VerUsuario`

**Qué hacen.** La lista de personas y la ficha de una.

**Rutas.** `GET /api/acceso/usuarios/?grupo=…&rol=STUDENT&estado=ACTIVO` y `GET /api/acceso/usuarios/{id}/`

**Lo interesante: la lista se recorta sola.** El mismo endpoint devuelve cosas distintas según quién pregunte:

| Quién pregunta | Qué recibe |
|---|---|
| Estudiante | Sólo a sí mismo |
| Profesor | A sí mismo y a los estudiantes vigentes de sus grupos |
| Administración | A todo el colegio hasta su propio nivel |

El recorte lo hace la consulta en `repositorios.py`, guiada por el alcance que calculó el dominio. El frontend **no filtra nada**: pinta lo que llega.

**Qué trae cada fila.** Además de nombre y rol, el estado de acceso que el profesor necesita de un vistazo: `bloqueado_hasta`, `intentos_fallidos`, `debe_cambiar_credencial`, `ultimo_acceso_en` y el tipo de clave que usa esa persona.

**Pantallas.** O2 · Estudiantes del grupo, y A2 · Usuarios del colegio.

---

#### C.4 · `ActualizarUsuario`

**Qué hace.** Cambiar alias, idioma, estado, datos personales o identificadores.

**Ruta.** `PATCH /api/acceso/usuarios/{id}/`

**Tres reglas que conviene conocer.**

1. Los estados que se pueden poner son `ACTIVO`, `SUSPENDIDO` y `RETIRADO`. **`BLOQUEADO` no se pone a mano** desde aquí: el bloqueo automático lo calcula el sistema y se levanta con `DesbloquearUsuario`.
2. Dejar a alguien en estado distinto de activo **le cierra las sesiones** en el acto.
3. Nadie puede suspenderse ni retirarse a sí mismo. Evita que el único administrador se deje fuera.

**Pantalla.** A2 · ficha de usuario, y edición rápida desde O2.

---

#### C.5 · `AsignarRol`

**Qué hace.** Convertir a alguien en docente, estudiante o administrador.

**Ruta.** `PUT /api/acceso/usuarios/{id}/rol/` · `{ "rol": "TEACHER" }` · sólo administración.

**Dos salvaguardas.** No se puede asignar un rol de nivel superior al propio, y no se puede rebajar el propio rol. Al cambiar de rol **se revocan las sesiones**, porque el menú y los permisos cambian: obligar a volver a entrar es más limpio que intentar refrescar la app por la mitad.

**Pantalla.** A2 · ficha de usuario.

---

#### C.6 · `OtorgarPermiso` · C.7 · `RevocarPermiso`

**Qué hacen.** Dar a una persona concreta un permiso que su rol no incluye, con motivo y fecha de caducidad. Es la alternativa a la tabla gigante de permisos por contexto que se descartó en el diseño.

**Rutas.** `POST /api/acceso/usuarios/{id}/permisos/` y `DELETE /api/acceso/usuarios/{id}/permisos/{permiso}/`

```json
{ "permiso": "audit.read", "alcance": "ORGANIZATION",
  "motivo": "Coordinadora académica 2026", "vigente_hasta": 1791000000000 }
```

**Dos techos, ninguno negociable.** Lo comprueba `PoliticaAutorizacion.alcance_otorgable()`:

1. No se puede superar el techo del permiso. `credential.change_own` nunca pasa de `SELF`, porque cambiar la clave de otro es otro permiso distinto.
2. Nadie puede conceder más alcance del que él mismo tiene.

**El motivo es obligatorio.** Es lo que se lee en la auditoría meses después, cuando alguien pregunte por qué esa persona podía hacer eso.

**Caducan solos.** Al pasar `vigente_hasta`, el permiso deja de contar sin que nadie tenga que acordarse de limpiarlo.

**Pantalla.** A2 · ficha de usuario, sección Permisos adicionales.

---

#### C.8 · `RestablecerCredencial`

**Qué hace.** La recuperación de verdad, la que resuelve «olvidé mi clave» sin correo, sin SMS y sin internet. El profesor le pone al estudiante una clave provisional desde el aula.

**Ruta.** `POST /api/acceso/usuarios/{id}/credencial/restablecer/`

El cuerpo puede ir vacío (el backend genera la clave) o traer un `secreto` elegido por el docente.

```json
{ "secreto_provisional": "204915", "tipo_secreto": "PIN", "debe_cambiar": true, "sesiones_revocadas": 2 }
```

**Cuatro cosas ocurren a la vez, dentro de la misma carpeta.**

1. La clave anterior deja de servir.
2. La nueva nace marcada como provisional: al entrar, el estudiante **está obligado** a elegir una suya.
3. Se cierran todas sus sesiones abiertas.
4. Se registra un `DESBLOQUEO`, que además reinicia su contador de fallos. Práctico: casi siempre quien olvidó la clave también se bloqueó intentándolo.

**Quién puede.** `credential.reset`. El profesor, sólo sobre estudiantes de sus grupos. Si intenta restablecer la del rector recibe un **404**, no un 403: el sistema no confirma ni desmiente que esa persona exista.

**Pantalla.** O2 · botón «Nuevo PIN», que abre O4 con el número en grande.

---

#### C.9 · `DesbloquearUsuario`

**Qué hace.** Levantar el castigo de alguien que falló la clave demasiadas veces.

**Ruta.** `POST /api/acceso/usuarios/{id}/desbloquear/`

**Cómo funciona, y por qué es elegante.** El bloqueo **no es una casilla** en la tabla de usuarios: se calcula contando los fallos recientes. Desbloquear no consiste en apagar una casilla, sino en **insertar una fila `DESBLOQUEO`** en el registro de intentos. Como el conteo sólo mira los fallos posteriores al último éxito o desbloqueo, esa fila borra el pasado de un plumazo.

La ventaja: el historial queda completo. Se puede ver que María falló cinco veces el martes y que la profesora la desbloqueó, algo que una casilla habría borrado.

**Pantalla.** O2 · botón «Desbloquear», visible sólo en las filas con el aviso de bloqueo.

---

### Familia D · La emergencia del examen

Esta familia existe por una escena concreta. El examen empieza a las 10:00. Son las 09:57. Juan dice que olvidó su clave. Puede ser verdad, puede haberse bloqueado solo, o puede estar buscando ventaja. **El sistema no tiene que adivinar cuál de las tres:** el profesor decide y todo queda registrado.

#### D.1 · `OtorgarAccesoTemporal`

**Qué hace.** Entrega un pase de emergencia, de dos formas posibles.

**Ruta.** `POST /api/acceso/autorizaciones-temporales/`

**Opción A · autorizar la tableta** (la recomendada, porque Juan no tiene que recordar nada):

```json
{ "usuario_id":"…", "tipo":"DISPOSITIVO", "dispositivo_id":"…",
  "evaluacion_ref":"co-sec-mat-eval-08", "minutos":5, "motivo":"Olvidó el PIN antes del parcial" }
```

Devuelve `entrega: { "grant_id": "…", "token": "b64url-256-bits" }`. El nodo envía eso a esa tableta concreta por el canal del aula. Nadie tiene que teclear nada.

**Opción B · código para dictar:**

```json
{ "usuario_id":"…", "tipo":"CODIGO", "evaluacion_ref":"co-sec-mat-eval-08", "minutos":5, "motivo":"…" }
```

Devuelve `entrega: { "codigo": "834195" }`. El profesor lo dicta y Juan lo escribe.

**Cómo se guarda cada secreto, y por qué distinto.**

| Tipo | Se guarda | Por qué |
|---|---|---|
| Token de tableta | SHA-256 | Son 256 bits al azar: imposible de adivinar, el hash rápido basta y el canje es instantáneo |
| Código de 6 dígitos | **Argon2id** | Sólo un millón de combinaciones. El hash lento, los cinco minutos de vida, el uso único y los tres fallos son lo que lo protege |

**Límites.** Entre uno y treinta minutos. El perfil del estudiante debe permitir acceso temporal (`permite_acceso_temporal`). El alcance máximo del permiso es `ASSIGNED_GROUPS`, así que **ni el rector** puede dar un pase a un estudiante que no esté en un grupo suyo: es una decisión del aula, tomada en el aula.

**Pantalla.** O3 · diálogo de dos toques, con las dos opciones lado a lado.

---

#### D.2 · `CanjearAccesoTemporal`

**Qué hace.** Convierte el pase en una sesión de verdad, limitada.

**Ruta.** `POST /api/acceso/autorizaciones-temporales/canjear/` · pública (quien canjea todavía no tiene sesión).

```bash
# Opción B
curl -X POST .../canjear/ -d '{"codigo":"834 195","dispositivo":"a8f3-hw-id"}'
# Opción A
curl -X POST .../canjear/ -d '{"grant_id":"…","token":"…","dispositivo":"a8f3-hw-id"}'
```

**Las cuatro comprobaciones.** No usado, no revocado, no caducado y, en la opción A, **que sea exactamente esa tableta**. Un pase emitido para la tableta 07 no sirve en la 03, aunque el token sea correcto.

**Al tercer fallo, el pase muere.** Los intentos fallidos se registran contra esa autorización concreta; al llegar a tres queda revocada y ya no sirve ni con el código correcto.

**Qué permite la sesión resultante.** Es de clase `TEMPORAL` y sólo deja rendir el examen, ver el propio progreso, ver contenido y cerrar sesión. **No permite cambiar la credencial.** Ese detalle es deliberado: si lo permitiera, el atajo de emergencia se convertiría en una forma de apoderarse de una cuenta. Para cambiar la clave está `RestablecerCredencial`, que exige al profesor.

Si la autorización fijó `evaluacion_ref`, el pase sólo sirve para esa evaluación.

**Pantalla.** S3. En la opción A ni siquiera hay formulario: un aviso «Tu profesor autorizó esta tableta» y un botón.

---

#### D.3 · `ListarAutorizaciones` · D.4 · `RevocarAccesoTemporal`

**Qué hacen.** Ver el historial de pases y anular uno.

**Rutas.** `GET /api/acceso/autorizaciones-temporales/?usuario=…&vigentes=1` y `DELETE /api/acceso/autorizaciones-temporales/{id}/`

**El listado nunca devuelve secretos.** Ni el código ni el token aparecen: sólo cuándo se emitió, si se usó, cuándo caduca y quién lo dio.

**Revocar también cierra la sesión.** Si el pase ya produjo una sesión y el profesor se arrepiente, anular el pase echa a esa sesión del sistema.

**Pantalla.** O3 · historial corto debajo de las dos opciones.

---

### Familia E · Configuración del colegio

#### E.1 · `ListarRoles` · E.2 · `ListarPermisos`

**Qué hacen.** Mostrar los roles disponibles y el catálogo completo de acciones posibles, cada una con su techo de alcance.

**Rutas.** `GET /api/acceso/roles/` y `GET /api/acceso/permisos/`

**Para qué sirve el catálogo.** Para que la pantalla de administración pueda dibujar la matriz permiso × rol sin tener la lista escrita a mano dentro de la app. Si mañana se añade un permiso nuevo en el backend, aparece solo en la pantalla.

**Pantalla.** A1 · pestaña Roles y permisos.

---

#### E.3 · `CrearRol`

**Qué hace.** Crear un rol propio del colegio, clonando una plantilla y ajustándola. El caso típico: un «Coordinador» que es como un docente pero además lee la auditoría.

**Ruta.** `POST /api/acceso/roles/`

```json
{ "codigo": "COORDINADOR", "nombre": "Coordinador", "plantilla": "TEACHER",
  "permisos": [ { "codigo": "audit.read", "alcance": "ORGANIZATION" },
                { "codigo": "content.project", "alcance": null } ] }
```

Se parte de la plantilla, se **añade** lo que traiga alcance y se **quita** lo que traiga `null`.

**Las plantillas nunca se tocan.** `STUDENT`, `TEACHER` y `ADMIN` son de sistema y no tienen dueño: cualquier colegio las usa tal cual. Los roles propios llevan el identificador de su organización y sólo existen ahí.

**Pantalla.** A1 · «Crear rol a partir de…».

---

#### E.4 · `ListarPoliticas` · E.5 · `ConfigurarPolitica`

**Qué hacen.** Ver y cambiar el reglamento de acceso de cada perfil. Es lo que permite que el mismo software sirva a un colegio de primaria y a una universidad.

**Rutas.** `GET /api/acceso/politicas/` y `PUT /api/acceso/politicas/{perfil}/`

```bash
curl -X PUT .../api/acceso/politicas/student/ -H "Authorization: Bearer $TOKEN" \
  -d '{"tipo_secreto":"PASSWORD","longitud_minima":8,"exige_mayuscula":true,"duracion_sesion_min":120}'
```

**El suelo de seguridad.** `PoliticaCredencial.validar()`, en el dominio, impide configuraciones absurdas: un PIN de menos de cuatro dígitos, una contraseña de menos de ocho caracteres, bloquear al primer error o una sesión de más de veinticuatro horas. Si algo no cuadra, **el cambio se rechaza entero** y el reglamento anterior sigue vigente.

**Efecto inmediato y visible.** Cambiar el tipo de secreto de los estudiantes a contraseña hace que la próxima llamada a `ConsultarConfiguracion` devuelva `PASSWORD`, y las tabletas pintan teclado completo en lugar de numérico. Sin reinstalar nada.

**Pantalla.** A1 · pestaña «Cómo entran», con tres tarjetas y un resumen en lenguaje llano del tipo «Los estudiantes entrarán con su código y un PIN de 6 números».

---

### Familia F · Grupos

Los grupos son el contexto que da sentido a «mis estudiantes». Sin grupos, el alcance `ASSIGNED_GROUPS` no significaría nada.

#### F.1 · `ListarGrupos` · F.2 · `VerGrupo`

**Rutas.** `GET /api/acceso/grupos/` y `GET /api/acceso/grupos/{id}/`

El listado también se recorta por alcance: la administración ve todos, el profesor los suyos, el estudiante aquel al que pertenece. Cada fila indica el papel de quien pregunta (`DOCENTE`, `MIEMBRO`) y cuántos miembros tiene.

**Pantallas.** Selector de grupo en O2; pestaña Grupos en A1.

#### F.3 · `CrearGrupo` · F.4 · `ActualizarGrupo`

**Rutas.** `POST /api/acceso/grupos/` y `PATCH /api/acceso/grupos/{id}/`

**El campo que más juego da: `politica_credencial_id`.** Un grupo puede tener su propio reglamento de acceso. Es la respuesta al requisito «en los grados superiores los estudiantes pueden usar contraseña profesional»: se crea el grupo de grado once apuntando al reglamento de docentes, y esos estudiantes entran con contraseña mientras el resto del colegio sigue con PIN.

**Pantalla.** A1 · pestaña Grupos.

#### F.5 · `AgregarMiembro` · F.6 · `RetirarMiembro`

**Rutas.** `POST /api/acceso/grupos/{id}/miembros/` y `DELETE /api/acceso/grupos/{id}/miembros/{usuario_id}/`

**Quién puede qué.** Con alcance de organización se puede añadir a cualquiera con cualquier papel. Con alcance de grupos (el profesor) **sólo estudiantes**: un profesor no puede nombrarse colega en otro curso ni añadir docentes al suyo.

**Retirar no borra.** Se sella la fecha de salida. El historial queda, y el estudiante deja de estar bajo el alcance de ese profesor de inmediato.

**Pantallas.** A1 · Grupos; alta rápida desde O5 al crear un estudiante.

---

## 5 · Las piezas que no son casos de uso

### 5.1 · Migraciones: el montaje de la oficina

| Archivo | Qué hace |
|---|---|
| `0001_initial.py` | Crea las 17 tablas `m01_*` con sus índices y sus reglas de integridad |
| `0002_plantillas.py` | Siembra el catálogo de 26 permisos y los tres roles de fábrica con sus alcances |

**Por qué la siembra está en una migración y no en el código.** Porque así, con sólo ejecutar `migrate`, el equipo ya tiene un sistema de roles funcionando. Es literalmente el «plug and play» del requisito: el colegio que no quiera configurar nada, no configura nada.

Es **idempotente**: se puede volver a ejecutar sin duplicar permisos ni roles.

```bash
.venv\Scripts\python manage.py migrate
```

### 5.2 · El comando de consola: la puerta de servicio

```bash
.venv\Scripts\python manage.py acceso_instalar --codigo IE-SANJOSE --nombre "IE San José" --pais CO --admin-dni 1042888795 --admin-nombres Ana --admin-apellidos Pérez
```

**Detalle de diseño que conviene subrayar:** este comando **no reimplementa nada**. Llama exactamente al mismo caso de uso `InstalarNodo` que la ruta HTTP. Dos puertas distintas, un solo funcionario. Si mañana cambia una regla de la instalación, cambia en un solo sitio y las dos puertas se enteran.

Es la vía natural para el instalador de Windows, que corre con teclado y puede pedir la contraseña cómodamente, a diferencia del nodo del aula.

### 5.3 · `/health/`: el semáforo

`GET /health/` incluye ahora el estado del módulo:

```json
{ "status": "ok", "biblioteca": { … },
  "acceso": { "instalado": true, "claves_derivadas": true } }
```

- `instalado: false` → el equipo aún no tiene colegio. El frontend debe ofrecer el asistente de instalación.
- `claves_derivadas: true` → las claves de cifrado se dedujeron de la clave general del proyecto. Sirve para el prototipo, pero en una instalación real el instalador debe generar tres claves propias.

### 5.4 · Las pruebas: la red de seguridad

| Archivo | Qué comprueba |
|---|---|
| `test_arquitectura.py` | Que el reglamento no dependa de la tecnología |
| `test_politicas.py` | Las decisiones de permisos, fortaleza y bloqueo, sin base de datos |
| `test_seguridad.py` | Que el cifrado cifre, detecte manipulación y que los pases caduquen |
| `test_api_sesiones.py` | Instalación única, entrada de estudiante y docente, bloqueo, desbloqueo, cierre |
| `test_api_usuarios.py` | Creación por alcance, claves provisionales, roles, permisos extra, grupos, políticas |
| `test_api_temporal.py` | Las dos opciones del pase de examen, uso único, caducidad, límites |
| `test_outbox.py` | Que una operación fallida no deje absolutamente nada escrito |

```bash
.venv\Scripts\python manage.py test acceso
```

---

## 6 · Tabla maestra: caso de uso ↔ endpoint ↔ pantalla

| # | Caso de uso | Endpoint | Sesión | Pantalla frontend |
|---|---|---|---|---|
| 1 | `InstalarNodo` | `POST /instalacion/` | no | Instalador de Windows · A2 (respaldo) |
| 2 | `ConsultarConfiguracion` | `GET /configuracion/` | no | S1 · S2 · O1 |
| 3 | `RegistrarDispositivo` | `POST /dispositivos/` | no | S1 (invisible) |
| 4 | `AutenticarUsuario` | `POST /sesiones/` | no | **S2** · **O1** |
| 5 | `ResolverPrincipal` | (todas, automático) | — | — |
| 6 | `ConsultarIdentidad` | `GET /yo/` | sí | S6 · O2 · A1 · A2 |
| 7 | `CambiarCredencialPropia` | `PUT /yo/credencial/` | sí | **S4** |
| 8 | `RevocarSesion` | `DELETE /sesiones/actual/` · `/{id}/` | sí | S6 · O2 · A2 |
| 9 | `ListarSesiones` | `GET /sesiones/` | sí | O2 · A2 |
| 10 | `CrearUsuario` | `POST /usuarios/` | sí | **O5** |
| 11 | `ListarUsuarios` | `GET /usuarios/` | sí | **O2** · A2 |
| 12 | `VerUsuario` | `GET /usuarios/{id}/` | sí | A2 |
| 13 | `ActualizarUsuario` | `PATCH /usuarios/{id}/` | sí | A2 |
| 14 | `AsignarRol` | `PUT /usuarios/{id}/rol/` | sí | A2 |
| 15 | `OtorgarPermiso` | `POST /usuarios/{id}/permisos/` | sí | A2 |
| 16 | `RevocarPermiso` | `DELETE /usuarios/{id}/permisos/{p}/` | sí | A2 |
| 17 | `RestablecerCredencial` | `POST /usuarios/{id}/credencial/restablecer/` | sí | **O4** |
| 18 | `DesbloquearUsuario` | `POST /usuarios/{id}/desbloquear/` | sí | **O2** |
| 19 | `OtorgarAccesoTemporal` | `POST /autorizaciones-temporales/` | sí | **O3** |
| 20 | `CanjearAccesoTemporal` | `POST /autorizaciones-temporales/canjear/` | no | **S3** |
| 21 | `ListarAutorizaciones` | `GET /autorizaciones-temporales/` | sí | O3 |
| 22 | `RevocarAccesoTemporal` | `DELETE /autorizaciones-temporales/{id}/` | sí | O3 |
| 23 | `ListarRoles` | `GET /roles/` | sí | A1 |
| 24 | `ListarPermisos` | `GET /permisos/` | sí | A1 |
| 25 | `CrearRol` | `POST /roles/` | sí | A1 |
| 26 | `ListarPoliticas` | `GET /politicas/` | sí | A1 |
| 27 | `ConfigurarPolitica` | `PUT /politicas/{perfil}/` | sí | **A1** |
| 28 | `ListarGrupos` | `GET /grupos/` | sí | O2 · A1 |
| 29 | `VerGrupo` | `GET /grupos/{id}/` | sí | A1 |
| 30 | `CrearGrupo` | `POST /grupos/` | sí | A1 |
| 31 | `ActualizarGrupo` | `PATCH /grupos/{id}/` | sí | A1 |
| 32 | `AgregarMiembro` | `POST /grupos/{id}/miembros/` | sí | A1 · O5 |
| 33 | `RetirarMiembro` | `DELETE /grupos/{id}/miembros/{u}/` | sí | A1 |
| 34 | `ListarDispositivos` | `GET /dispositivos/` | sí | O3 · A1 |
| 35 | `ActualizarDispositivo` | `PATCH /dispositivos/{id}/` | sí | A1 |

En negrita, la pantalla que es **dueña** de ese caso de uso.

---

## 7 · Las pantallas del frontend, vistas desde el backend

El detalle visual está en [acceso-sugerencias.html](../../specs/presentaciones/acceso-sugerencias.html). Aquí va sólo lo que el backend exige de cada una.

### 7.1 · Trece pantallas

| Código | Pantalla | Casos de uso que consume | Obligación que impone el backend |
|---|---|---|---|
| **S1** | Conectar al aula (tableta) | 2, 3 | Generar un identificador de dispositivo una vez y guardarlo en el almacén seguro del sistema |
| **S2** | Acceso del estudiante | 2, 4 | Teclado numérico propio si el reglamento dice `PIN`; teclado completo si dice `PASSWORD` |
| **S3** | Código del profesor | 20 | En la opción A no hay formulario: un aviso y un botón |
| **S4** | Elegir PIN nuevo | 7 | Interceptar el 403 `debe_cambiar_credencial` desde cualquier pantalla y traer aquí |
| **S5** | Bloqueado | (respuesta 423) | Cuenta regresiva con los segundos que da el backend. Sin botón de reintentar |
| **S6** | Menú del estudiante | 6, 8 | Pintar los hexágonos según `permisos[]`. Banda amarilla si la sesión es temporal |
| **O1** | Acceso del docente | 2, 4 | **Teclado completo en pantalla**: el nodo no tiene teclado físico |
| **O2** | Estudiantes del grupo | 6, 9, 11, 18, 28 | Una fila por estudiante con su estado de acceso y las acciones permitidas |
| **O3** | Autorizar acceso a examen | 19, 21, 22, 34 | Dos toques como máximo. Código en dígitos grandes con cuenta regresiva |
| **O4** | Nuevo PIN provisional | 17 | Mostrar el número una sola vez, con «Ya lo anoté» |
| **O5** | Nuevo estudiante | 10, 32 | Teclado en pantalla para texto y pad numérico para código y PIN |
| **A1** | Acceso y seguridad del colegio | 23-34 | Cuatro pestañas: Cómo entran, Roles y permisos, Grupos, Tabletas |
| **A2** | Personas y sesiones | 1, 6, 9, 12-16 | Usuarios, sesiones activas, auditoría y asistente de instalación |

### 7.2 · Cuatro comportamientos que no son una pantalla

Estos se resuelven **una sola vez** en el cliente HTTP de la app, no en cada pantalla:

| El backend responde | La app hace |
|---|---|
| 401 `sesion_expirada` · `sesion_revocada` · `sesion_invalida` | Borra el pase y vuelve al acceso con un aviso corto |
| 403 `debe_cambiar_credencial` | Navega a la pantalla de cambio de clave y no deja salir |
| 403 `sesion_temporal_limitada` | Banda amarilla y mensaje «Este acceso es sólo para la evaluación» |
| 423 `usuario_bloqueado` | Pantalla de espera con cuenta regresiva |

### 7.3 · Orden sugerido de construcción

| # | Entrega | Pantallas | Qué desbloquea |
|---|---|---|---|
| 1 | Cliente de acceso: sesión, cabecera automática, almacén seguro, teclados | — | Todo lo demás |
| 2 | Student: acceso, cambio de PIN, bloqueo, banda de sesión | S1 S2 S4 S5 S6 | Que el expediente se grabe con la identidad real |
| 3 | OPS: acceso docente y lista de estudiantes | O1 O2 O4 | Restablecer y desbloquear desde el aula |
| 4 | Acceso temporal a examen, de punta a punta | O3 S3 | El caso de las 09:57 |
| 5 | Alta de estudiantes e importación por lotes | O5 | Poblar un colegio de verdad |
| 6 | Administración | A1 A2 | Colegios que sí quieren configurar |

---

## 8 · Preguntas frecuentes

**¿Por qué las vistas son tan cortas?**
Porque una vista que decide reglas es una regla atrapada en la tecnología. Al dejar la vista en «validar la forma, llamar, devolver», toda la inteligencia queda en un sitio que se puede probar sin servidor y trasladar a otro framework sin reescribirla.

**¿Por qué hay serializers si los casos de uso también validan?**
Validan cosas distintas. El serializer revisa la **forma** (¿vino el campo? ¿es texto? ¿cabe?). El dominio revisa el **fondo** (¿el PIN es lo bastante fuerte? ¿esta persona puede hacer esto?). Mezclarlas es lo que hace que las reglas de negocio acaben repartidas por todo el código.

**¿Por qué los permisos no viajan dentro del pase de entrada?**
Porque entonces revocar un permiso tardaría hasta cuatro horas en surtir efecto. Al consultarlos contra la base en cada petición, cualquier cambio es inmediato y además el pase se mantiene pequeño.

**¿Por qué a veces responde 404 donde se esperaría 403?**
El 403 dice «no puedes hacer esto». El 404 dice «no existe, o no es asunto tuyo». Si un profesor pregunta por un estudiante de otro curso y recibiera un 403, sabría que esa persona existe. Con el 404 no averigua nada. La regla: sin el permiso, 403; con el permiso pero fuera de alcance, 404.

**¿Qué pasa si se corta la luz a mitad de una operación?**
Nada queda a medias. Cada operación ocurre dentro de una transacción: al reiniciar, o está entera o es como si nunca hubiera empezado.

**¿Se puede recuperar una clave olvidada?**
No, y es intencional. Sólo se guarda una huella irreversible. Lo que se hace es **poner una nueva** desde el aula, que es justo lo que resuelve el problema sin depender de correo ni de internet.

**¿Esto ya está en uso?**
El backend está implementado y probado. Las rutas del expediente y de la biblioteca **siguen funcionando exactamente igual que antes**: sin pase de entrada, el visitante es anónimo. Exigir sesión en todo el sistema es una decisión pendiente (Q-34) que se activará con el interruptor `AVACOM_LMS_EXIGIR_SESION=1` cuando las pantallas de acceso estén en las apps.

---

## 9 · Glosario mínimo

| Palabra | En lenguaje llano |
|---|---|
| **Caso de uso** | Una operación completa que alguien quiere hacer, con todas sus reglas |
| **Endpoint / ruta** | Una dirección a la que la app envía una petición |
| **APIView** | El trozo de código que atiende esa dirección |
| **Serializer** | El revisor de formularios: comprueba que el mensaje tenga la forma esperada |
| **Dominio** | Las reglas de AVACOM, escritas sin depender de ninguna tecnología |
| **Infraestructura** | Lo que guarda, lee, cifra y firma de verdad |
| **Repositorio** | El archivo: sabe guardar y encontrar, no decide nada |
| **Unidad de Trabajo** | La carpeta de una gestión: o se guarda entera o no se guarda |
| **Migración** | La instrucción que monta o modifica las tablas de la base |
| **JWT** | El pase de entrada sellado que se presenta en cada petición |
| **Argon2id** | La forma de guardar claves de modo que nadie, ni nosotros, pueda leerlas |
| **AES-256-GCM** | El cifrado de los datos personales, que sí se pueden volver a leer |
| **HMAC** | Una huella fija de un dato cifrado, que permite buscarlo sin descifrarlo |
| **Alcance** | Hasta dónde llega un permiso: uno mismo, sus grupos o todo el colegio |
| **Outbox** | La bandeja de salida: avisos guardados por si algún día hay que sincronizar |
| **Idempotente** | Que repetirlo no cambia el resultado ni duplica nada |
