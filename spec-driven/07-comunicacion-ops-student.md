# 07 · Comunicación OPS ↔ Student en la LAN del aula

| Campo | Valor |
|---|---|
| Estado | **Propuesta.** Se debe realizar una comunicación entre el backend de AVACOM OPS y AVACOM Student a través de la red local del aula |
| Proveedor | El backend DRF de `backend/`, en el **mismo equipo** que AVACOM OPS y que AVACOM Biblioteca (el equipo maestro) |
| Consumidor | Los clientes AVACOM Student, en Windows y en Android, desde otros equipos de la misma LAN; AVACOM OPS desde el propio equipo maestro |
| Transporte | HTTP/1.1 en texto claro contra la API en DRF **y WebSockets** (Django Channels) para la sesión en vivo: cuántos estudiantes están viendo un quiz, con indicador en OPS Master (Q-28). Hoy el backend **no sirve** WebSockets: hay que añadir Channels; el núcleo ya trae el cliente (`ActivitySocketClient`) |
| Transporte | La API del backend debe escuchar en `0.0.0.0:8000` para ser accesible en la red LAN. HTTP y WebSockets salen por **el mismo puerto**: una sola regla de cortafuegos y una sola dirección que dictar |
| Fecha de corte | 2026-09-10 · comprobado en el equipo maestro con IP `192.168.0.55` (Wi-Fi «Makers») |

Sin este contrato, el estudiante (AVACOM Student) no puede acceder al curso ni realizar sus actividades correspondientes.

Este documento sigue el método del proyecto: **lo que se conserva → especificación → clarificación → plan → errores → tareas → verificación**. No cambia ninguna decisión de [01-constitucion.md](01-constitucion.md) ni el contrato de [06-contrato-biblioteca.md](06-contrato-biblioteca.md): cambia **el host al que apunta Student**, no lo que le pide.

---

## El cambio, en una frase

> El backend y OPS viven en el equipo maestro; Student llega a ese equipo por su IP en la LAN y usa exactamente las mismas rutas que OPS.

Hoy todo se ha verificado con Student y backend en la misma máquina (`127.0.0.1:8000`, ver `specs/conexion_LMS_Biblioteca.md` §6). Esta especificación describe lo que falta para que Student corra **en otro equipo**, con especial atención a la tableta Android.

## Resultado esperado

Lo que tiene que verse al terminar, en el orden en que lo vive el estudiante:

| # | Resultado | Dónde se exige |
|---|---|---|
| 1 | AVACOM Student muestra la **lista de cursos disponibles** que ofrece AVACOM Biblioteca en el equipo maestro | RF-L13 · CA-L02 |
| 2 | El aspecto de esa lista es **similar al de AVACOM OPS Master**: hexágonos arriba, «Lista completa» debajo con tarjeta por curso (icono de color, título, subtítulo, materiales · lecciones · versión · ref) y botón «Abrir curso», más el chip de estado de la biblioteca en la cabecera | RF-L13 · CA-L12 |
| 3 | El estudiante **entra a consumir el contenido** de cada curso: lámina, video, PDF, interactivo, lección y evaluación, y su avance queda en el expediente | RF-L02 · CA-L03..CA-L05 |
| 4 | Los títulos dicen **«Tus cursos»**: en la cabecera de la pantalla y en el encabezado de la lista | RF-L14 · CA-L13 |
| 5 | Student se conecta a la **IP del equipo donde corren AVACOM OPS Master y el backend**, que es el mismo host; OPS muestra esa dirección para poder dictarla | RF-L01 · RF-L07 · CA-L01 |
| 6 | Mientras un estudiante está en un quiz, OPS Master muestra en vivo **cuántos estudiantes lo están viendo** (Q-28) | RF-L15 · RF-L16 · CA-L14..CA-L16 |

---

## 1 · Lo que ya existe y se conserva

1. Mantener las apps de `avacom_lms` (`biblioteca`, `expediente`) dentro del backend hecho en DRF. **No se añade ninguna ruta HTTP nueva de negocio.** Lo único que se añade es la app `aula` con el consumidor WebSocket de la sesión en vivo (Q-28), que **no tiene modelos ni escribe nada**: la presencia es efímera y no es expediente.
2. Mantener el modelado de datos actual, donde el progreso vive en el LMS: las 8 tablas de expediente y ninguna de curso (artículos 13 y 14).
3. El LMS no debe guardar información del curso; guarda únicamente información del LMS. Student, al estar en otro equipo, sigue sin guardar nada del curso: todo lo pide en vivo al backend.

Lo que el código ya resuelve y que esta prueba **reutiliza sin tocar**:

| Pieza | Dónde | Por qué importa en la LAN |
|---|---|---|
| El backend acepta cualquier `Host` | `backend/avacom_lms/settings.py` · `ALLOWED_HOSTS = ["*"]` | Una petición a `http://192.168.0.55:8000/` no es rechazada por Django |
| El arranque documentado ya es `0.0.0.0:8000` | `backend/README.md` | Escucha en todas las interfaces; OPS entra por `127.0.0.1`, las tabletas por la IP LAN |
| `/health/` incluye el estado de la biblioteca | `expediente/views.py` · `HealthView` | «Comprobar conexión» de Student ya distingue backend sin biblioteca de backend con biblioteca |
| Toda URL del cliente nace de `BaseUri` | `Avacom.Lms.Core/Services/BibliotecaDeContenido.cs` (`MedioUri`, `VozUri`, `ObtenerAsync`, `EnviarAsync`) | Imágenes, video, PDF, interactivos y voz salen también por `http://<IP>:8000/api/biblioteca/medio/…`. **La tableta nunca habla con la biblioteca**, que sólo escucha en loopback |
| La dirección se normaliza | `Avacom.Lms.Core/Models/ConnectionOptions.cs` · `Normalize` | El estudiante puede escribir `192.168.0.55:8000` sin `http://` |
| Cuerpos con `Content-Length` | `BibliotecaDeContenido.Cuerpo` | El servidor de desarrollo de Django no lee cuerpos troceados; ya está resuelto (C-11) |
| Los tiempos los pone el servidor | `expediente/models.py` · `ahora_ms()` | El reloj de la tableta no participa en el expediente |
| Fallos a archivo | `RegistroDeFallos` · `%LOCALAPPDATA%\AVACOM\lms\fallos-student.log` | Un fallo de red en la tableta deja rastro sin consola |
| Permisos Android de red | `Platforms/Android/AndroidManifest.xml` · `INTERNET`, `ACCESS_NETWORK_STATE` | Necesarios, pero **no suficientes** (ver §4.3) |
| Regla de cortafuegos en el equipo maestro | «AVACOM OPS Core (TCP 8000)» · entrada, TCP 8000, perfil *Any*, programa *Any* | Ya existe en el equipo de prueba; es una regla de **puerto**, así que vale para el Python del sistema y para el del `.venv`, y cubre también los WebSockets porque van por el mismo puerto |
| Cliente WebSocket y URL `ws://` | `Avacom.Lms.Core/Services/ActivitySocketClient.cs`, `ConnectionOptions.WebSocketBaseUri` | Ya derivan `ws://<IP>:8000/` de la misma dirección HTTP; sólo hay que apuntar a la ruta nueva de §4.8 |
| Lista de cursos en OPS | `Avacom.Lms.Ops/Pages/AsignaturasPage.xaml(.cs)` | Es el **modelo visual** que Student debe imitar (resultado esperado 2): hexágonos, «Lista completa», tarjeta con `Detalle` y `curso_ref`, botón «Abrir curso», chip con capacidades |

Reglas que no cambian: la biblioteca sólo en `127.0.0.1`, con puerto efímero y ficha; el backend es su único cliente; el expediente se escribe por identidad lógica; la degradación es 503 / 501 / 502 / 404 y nunca una pantalla en blanco.

---

## 2 · Especificación

### 2.1 · Topología de la prueba

```
Tableta Android (Student) ──┐
Portátil Windows (Student) ─┤  HTTP LAN  →  http://192.168.0.55:8000
                            │
                            ▼
┌──────────────────── Equipo maestro (host) ──────────────────────────┐
│                                                                     │
│  AVACOM OPS (MAUI) ── http://127.0.0.1:8000 ──►  Backend DRF        │
│                                                  0.0.0.0:8000       │
│                                                       │             │
│                                                       │ loopback, puerto efímero,
│                                                       │ X-Avacom-Ficha
│                                                       ▼             │
│                                          AVACOM Biblioteca          │
│                                          127.0.0.1:{enlace.json}    │
└─────────────────────────────────────────────────────────────────────┘
```

Tres consecuencias que hay que hacer explícitas:

1. **Un solo punto de entrada en la LAN**: el puerto 8000 del equipo maestro. El puerto efímero de la biblioteca no es alcanzable desde ninguna tableta, y así debe seguir (CA-L08).
2. **OPS y Student consumen las mismas rutas.** La diferencia es que Student manda `persona` y OPS no; eso ya está así en `BibliotecaDeContenido.CursosAsync`.
3. **La dirección que escribe el estudiante es la IP LAN del equipo maestro.** No `127.0.0.1` (apuntaría a la propia tableta) ni la IP de un adaptador virtual del host (en el equipo de prueba, `172.31.224.1` es de Hyper‑V/WSL y no llega a ninguna tableta).

### 2.2 · Actores

| Actor | Dónde está | Qué hace en esta prueba |
|---|---|---|
| Docente | OPS en el equipo maestro | Enciende biblioteca y backend, dicta la dirección, sigue el consolidado |
| Estudiante | Student en tableta Android o portátil Windows | Escribe nombre y dirección, entra, abre materiales, hace una evaluación |
| Técnico | Equipo maestro y red del aula | Comprueba IP, perfil de red, cortafuegos y que la red no aísle clientes |

### 2.3 · Historias

| ID | Historia | Por qué existe |
|---|---|---|
| US-L1 | Como estudiante, escribo la dirección que aparece en la pantalla del profesor y «Comprobar conexión» me dice si el aula está lista | Hoy la pantalla de Student promete esa dirección («la dirección que aparece en la pantalla principal del profesor») y OPS **no la muestra** |
| US-L2 | Como estudiante en la tableta, veo los mismos cursos que el docente y entro a uno; abrir un material registra mi avance | Es el objetivo de la prueba |
| US-L3 | Como estudiante, hago una evaluación desde la tableta; la corrección ocurre en la biblioteca y la nota aparece en el consolidado del docente | Cierra el ciclo expediente ↔ biblioteca a través de la LAN |
| US-L4 | Como estudiante, si el docente cierra la biblioteca a mitad de clase sigo viendo mi expediente con un aviso | Ya existe para loopback; hay que confirmarlo desde otro equipo |
| US-L5 | Como estudiante, si el backend no responde veo «No hay conexión con el aula» y puedo reintentar | La red es una capa nueva de fallo que en loopback nunca aparecía |
| US-L6 | Como docente, veo en OPS la dirección que debo dictar, sin abrir una consola | Sin esto la prueba depende de `ipconfig` |
| US-L7 | Como estudiante, la pantalla «Tus cursos» se ve como la de mi profesor: reconozco los mismos hexágonos y la misma lista, con mi avance añadido | Resultado esperado 2 y 4 |
| US-L8 | Como docente, mientras la clase hace un quiz veo en OPS cuántos estudiantes lo están viendo ahora mismo, y el número baja cuando alguien sale | Q-28 · sesión en vivo |

### 2.4 · Requisitos funcionales

| ID | Requisito | Cómo se comprueba |
|---|---|---|
| RF-L01 | El backend escucha en `0.0.0.0:8000` y acepta peticiones cuyo `Host` es la IP LAN del equipo maestro | `netstat -ano \| findstr :8000` muestra `0.0.0.0:8000`; `GET http://<IP>:8000/health/` → 200 |
| RF-L02 | Toda URL que construyen los clientes parte de la `BaseUri` configurada, incluidas las de medio y voz. No existe ninguna URL absoluta a `127.0.0.1` en `Avacom.Lms.Core`, `Avacom.Lms.Ui` ni `Avacom.Lms.Student` fuera de un valor por defecto editable | `grep` de `127.0.0.1` y `localhost` en esos proyectos sólo encuentra valores por defecto |
| RF-L03 | Student acepta `IP:puerto` sin esquema, guarda la última dirección válida y la propone en la siguiente sesión | Reiniciar Student conserva la dirección |
| RF-L04 | «Comprobar conexión» distingue tres estados: sin backend, backend sin biblioteca, todo listo. Los tres se explican con texto, no sólo con color | Apagar el backend, cerrar la biblioteca y tener todo abierto producen tres mensajes distintos |
| RF-L05 | La app Android permite tráfico HTTP en texto claro hacia el aula, **declarado explícitamente** en el manifiesto | El `AndroidManifest.xml` generado en `obj/` contiene `android:usesCleartextTraffic="true"` |
| RF-L06 | El equipo maestro tiene una regla de cortafuegos de **entrada** para TCP 8000 vigente en el perfil de red activo (o en todos) | `Get-NetFirewallRule` la lista habilitada; `Test-NetConnection <IP> -Port 8000` desde otro equipo devuelve `TcpTestSucceeded: True` |
| RF-L07 | OPS muestra la dirección o direcciones LAN del equipo donde corre el backend, sin loopback ni adaptadores virtuales | La pantalla de inicio de OPS muestra `http://192.168.0.55:8000` en el equipo de prueba |
| RF-L08 | La identidad de la persona y los tiempos se calculan donde hoy: el slug en el cliente, los milisegundos en el servidor. Ningún dato del expediente depende del reloj de la tableta | Cambiar la hora de la tableta no altera `inscrito_en`, `abierto_en` ni `finalizado_en` |
| RF-L09 | Sin backend, el cliente muestra el motivo y ofrece reintentar; con backend pero sin biblioteca, muestra expediente y aviso (ya existe) | Escenarios de §7.2 |
| RF-L10 | Tiempos de espera del cliente hacia el backend: 3 s para la comprobación de conexión, 15 s para contenido | Ya así en `ConnectionPage` y `Sesion`; se conserva |
| RF-L11 | La biblioteca **no** es alcanzable desde la LAN | Desde una tableta, el puerto de `enlace.json` no responde |
| RF-L12 | Los únicos cambios en el backend son aditivos: `direcciones_lan` en `/health/` (Q-30) y la ruta WebSocket de §4.8. Ninguna ruta HTTP de contenido o expediente cambia de forma | Diff del backend limitado a `HealthView`, su prueba, `asgi.py`, `settings.py` y la app `aula` |
| RF-L13 | La pantalla de cursos de Student reproduce la estructura de la de OPS: chip de estado en la cabecera, hexágonos, encabezado «Lista completa», tarjeta por curso con icono de color, título, subtítulo, `Detalle` con `curso_ref`, y botón «Abrir curso». Student añade la barra y el porcentaje de progreso, que OPS no tiene | Captura de ambas pantallas lado a lado con los mismos dos cursos |
| RF-L14 | Los títulos de esa pantalla dicen **«Tus cursos»**: el de la cabecera (hoy «Asignaturas») y el encabezado principal (hoy «Tus cursos, {nombre}») | Ninguna etiqueta de la pantalla dice «Asignaturas» |
| RF-L15 | El backend publica una ruta WebSocket por evaluación en el mismo puerto 8000. Cada Student que abre un quiz se une como `estudiante`; OPS se une como `docente`. El grupo recibe `presence_changed` con el número de estudiantes presentes cada vez que alguien entra o sale | Dos tabletas en el quiz → OPS recibe `viendo: 2`; una sale → `viendo: 1` |
| RF-L16 | OPS muestra ese número como indicador junto al quiz («N estudiantes viendo este quiz») y, sin señal WebSocket, dice «sin señal en vivo» en lugar de mostrar 0 | Apagar el backend con OPS abierto cambia el indicador a «sin señal en vivo» |
| RF-L17 | La presencia en vivo es **efímera**: vive en memoria del proceso del backend, no se persiste, no alimenta progreso ni nota, y no participa en ninguna decisión de disponibilidad | La app `aula` no tiene `models.py` con modelos; prueba de esquema sin tablas nuevas |
| RF-L18 | Un solo proceso sirve HTTP y WebSockets en `0.0.0.0:8000` (Daphne vía Channels). El flujo de medios (`StreamingHttpResponse` con `Range`) sigue funcionando sobre ASGI | `runserver` arranca con «Starting ASGI/Daphne»; CA-L05 sigue en verde |

### 2.5 · Criterios de aceptación

| ID | Criterio |
|---|---|
| CA-L01 | Desde una tableta en la misma LAN, `GET http://<IP>:8000/health/` responde 200 con `biblioteca.disponible = true` (se puede hacer con el navegador de la tableta) |
| CA-L02 | Student en Android y OPS en el equipo maestro muestran los mismos cursos y la misma `huella_catalogo` |
| CA-L03 | Abrir un material desde la tableta produce `POST /api/aperturas/` → 201 y el consolidado de OPS lo refleja al pulsar «Actualizar», sin reiniciar nada |
| CA-L04 | Una evaluación completa desde la tableta produce nota en `GET /api/resultados/` y en `GET /api/cursos/{curso_ref}/consolidado/` |
| CA-L05 | Un video se reproduce en la tableta con adelanto: el backend responde 206 con `Content-Range` a través de la LAN |
| CA-L06 | Cerrar la biblioteca en el equipo maestro: Student muestra aviso y expediente; reabrirla: Student vuelve a mostrar contenido tras «Actualizar», sin reiniciar la app |
| CA-L07 | Apagar el backend: Student muestra «No hay conexión con el aula» y ofrece reintentar y modo demo; no se cierra ni queda en blanco |
| CA-L08 | Desde la tableta, ningún puerto del equipo maestro distinto de 8000 es necesario, y el puerto efímero de la biblioteca **no** responde |
| CA-L09 | Dos tabletas con nombres distintos producen expedientes separados en el consolidado |
| CA-L10 | El manifiesto Android generado declara `usesCleartextTraffic="true"` |
| CA-L11 | La suite del backend incluye una prueba que pide `/health/` con `HTTP_HOST` igual a una IP LAN y recibe 200 |
| CA-L12 | Con los mismos dos cursos, la pantalla de cursos de Student y la de OPS muestran los mismos hexágonos, la misma «Lista completa» y el mismo botón «Abrir curso»; Student añade progreso |
| CA-L13 | La cabecera y el encabezado de esa pantalla en Student dicen «Tus cursos» |
| CA-L14 | Con OPS en un quiz y dos tabletas dentro del mismo quiz, el indicador de OPS dice «2 estudiantes viendo este quiz» en menos de 2 s; al salir una, dice «1» |
| CA-L15 | La conexión WebSocket desde la tableta llega por `ws://<IP>:8000/` (mismo puerto, misma regla de cortafuegos); no hace falta abrir ningún otro puerto |
| CA-L16 | Con el backend apagado, el indicador de OPS pasa a «sin señal en vivo»; al reiniciarlo y volver a entrar, se recupera. Nada de esto altera el expediente |
| CA-L17 | La suite del backend incluye una prueba con `WebsocketCommunicator`: dos estudiantes entran → el docente recibe `viendo: 2`; uno sale → `viendo: 1` |

---

## 3 · Clarificación

Las decisiones Q-01..Q-26 de [03-clarificacion.md](03-clarificacion.md) siguen vigentes. Esta prueba añade las siguientes. Ninguna se responde por inferencia del código: cada una lleva una propuesta que hay que ratificar.

| Q | Pregunta | Estado | Propuesta |
|---|---|---|---|
| Q-27 | ¿HTTP en texto claro o TLS dentro del aula? | **Propuesta** | Texto claro. El aula no tiene Internet ni una autoridad de certificación; un certificado autofirmado obligaría a instalarlo en cada tableta. La ficha de la biblioteca **nunca** viaja por la LAN (sólo por loopback), así que el texto claro no la expone. Se documenta como límite en §8 |
| Q-28 | ¿Forman parte de la prueba los WebSockets? | **Cerrada: Sí** | Deben incluirse los channels (Django Channels, junto a DRF) para hacer peticiones en vivo (*live session*) y saber cuántos estudiantes están viendo un «Quiz» en vivo; ese número se representa en un indicador en AVACOM OPS Master. Consecuencias: hoy el backend no incluye Channels ni servidor ASGI (`requirements.txt` sólo trae Django y DRF), así que se añaden `channels` y `daphne`; el cliente `ActivitySocketClient` ya existe y se reutiliza. La presencia es efímera y **no es expediente** (RF-L17). Plan en §4.8 |
| Q-36 | ¿Capa de canales con Redis o en memoria? | **Propuesta** | `InMemoryChannelLayer`. El aula no tiene Internet ni un segundo servidor, y el backend es un solo proceso (Q-16). Redis se evaluará sólo si se pasa a varios procesos |
| Q-37 | ¿Qué identifica una sesión en vivo? | **Propuesta** | La `evaluacion_ref` de la biblioteca, igual que el intento. No se crea ninguna tabla de «sesión»: entrar al quiz es entrar al grupo; salir o perder la conexión es salir del grupo |
| Q-38 | ¿Qué ve el docente cuando no hay señal en vivo? | **Propuesta** | «Sin señal en vivo», nunca «0 estudiantes». Igual que con la biblioteca: **«no se pudo comprobar» no es «no hay nadie»** |
| Q-29 | ¿Puerto fijo o configurable? | **Propuesta** | Fijo en 8000: la regla de cortafuegos, la documentación y lo que el docente dicta dependen de él. Cambiarlo es una decisión de despliegue, no del estudiante |
| Q-30 | ¿Quién le dice al docente la dirección a dictar? | **Propuesta** | El backend publica `direcciones_lan` (IPv4 no loopback del equipo) en `/health/` y OPS las muestra. Alternativa: OPS las calcula con `NetworkInterface` y filtra adaptadores virtuales por descripción (`vEthernet`, `WSL`, `Hyper-V`). La primera vale para cualquier cliente y para `curl`; la segunda filtra mejor. Se puede hacer la primera y, si OPS está en el mismo equipo, refinar con la segunda |
| Q-31 | ¿Qué perfil de red exige la prueba? | **Propuesta** | Ninguno en particular, **siempre que** la regla de entrada TCP 8000 esté en perfil *Any*. El equipo de prueba está hoy en perfil **Público** con esa regla ya creada. Se recomienda marcar la red del aula como Privada por higiene, pero no es requisito |
| Q-32 | ¿Y si la Wi‑Fi del aula aísla a los clientes (*AP isolation*)? | **Propuesta** | La prueba exige una red sin aislamiento. Alternativa autónoma y sin Internet: el **punto de acceso móvil de Windows** en el equipo maestro; las tabletas se conectan a él y la dirección pasa a ser la del adaptador del hotspot (habitualmente `192.168.137.1:8000`) |
| Q-33 | ¿Dos estudiantes con el mismo nombre? | Ya conocido (Q-04) | Comparten `persona_id`. En la prueba se usan nombres distintos y se anota como límite; la solución es el módulo de identidad, no un parche aquí |
| Q-34 | ¿Servidor de desarrollo de Django para la prueba? | **Propuesta** | Sí. `runserver` es multihilo y basta para un aula pequeña con video por flujo. Para un aula real se evaluará un servidor WSGI/ASGI de producción, sin cambiar nada del contrato |
| Q-35 | ¿Qué dirección propone Student por defecto? | **Propuesta** | Ninguna inventada. Hoy propone `http://192.168.1.10:8000`, que no existe en la red de prueba y confunde. Debe proponer la última usada y, si no hay, dejar el campo vacío con un ejemplo como *placeholder* |

---

## 4 · Plan técnico

### 4.1 · Equipo maestro: qué corre y en qué orden

| Orden | Qué | Cómo | Comprobación |
|---|---|---|---|
| 1 | AVACOM Biblioteca | Abrir la app y entrar en la pestaña «Contenido AVACOM» con la licencia cargada | Existe `%ProgramData%\AVACOM\contenido\enlace.json` |
| 2 | Backend | `cd backend; .venv\Scripts\python manage.py runserver 0.0.0.0:8000` (con Channels instalado, `runserver` arranca Daphne y sirve HTTP y WebSockets en el mismo puerto) | `GET http://127.0.0.1:8000/health/` → `biblioteca.disponible: true`; la consola dice «Starting ASGI/Daphne» |
| 3 | AVACOM OPS | `dotnet run --project src/Avacom.Lms.Ops -f net10.0-windows10.0.19041.0`, dirección `http://127.0.0.1:8000` | «Asignaturas» lista los cursos; la pantalla de inicio muestra la dirección LAN (RF-L07) |

> Nota del equipo de prueba: el backend que hoy escucha en 8000 (PID 3952) se lanzó con el Python del sistema (`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`), no con el del `.venv`. Funciona igual, pero la documentación y la regla de cortafuegos se escriben pensando en el `.venv`; por eso la regla debe ser de **puerto** y no de programa.

### 4.2 · Red y cortafuegos del equipo maestro

1. **Averiguar la IP LAN.** `ipconfig` y quedarse con el adaptador Wi‑Fi o Ethernet real. En el equipo de prueba: `192.168.0.55` (Wi‑Fi «Makers»). Descartar `172.31.224.1` (adaptador virtual).
2. **Regla de entrada TCP 8000.** En el equipo de prueba ya existe («AVACOM OPS Core (TCP 8000)», perfil *Any*, programa *Any*). Si en otro equipo falta, desde PowerShell como administrador:

   ```powershell
   New-NetFirewallRule -DisplayName "AVACOM LMS backend (TCP 8000)" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
   ```

   Se elige regla de puerto y no de programa porque la ruta de `python.exe` cambia entre el `.venv` y el Python del sistema, y una regla de programa dejaría de aplicar sin avisar.
3. **Perfil de red.** El equipo de prueba está en perfil **Público**. Con la regla en perfil *Any* no bloquea; si se prefiere Privado (administrador): `Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private`.
4. **Aislamiento de clientes.** Si dos equipos de la misma Wi‑Fi no se ven (`Test-NetConnection` falla aunque la regla exista), la red aísla clientes: usar otra red o el punto de acceso móvil de Windows (Q-32).
5. **DHCP.** La IP puede cambiar entre días. Para un aula estable, reserva DHCP en el router o hotspot del equipo maestro.

### 4.3 · Android: tráfico en texto claro

Desde Android 9 (API 28), con `targetSdk ≥ 28`, el sistema **bloquea HTTP en texto claro** salvo que la app lo declare. El manifiesto generado hoy (`src/Avacom.Lms.Student/obj/Debug/net10.0-android/android/AndroidManifest.xml`) tiene `targetSdkVersion="36"` y **no** declara `usesCleartextTraffic`: la compilación Debug no lo añade sola. Con la app actual, la tableta fallaría en la primera petición con `Cleartext HTTP traffic to 192.168.0.55 not permitted`, tanto en `HttpClient` (`AndroidMessageHandler` respeta la política) como en el `WebView` que reproduce video, PDF e interactivos.

Cambio en `src/Avacom.Lms.Student/Platforms/Android/AndroidManifest.xml`:

```xml
<application android:allowBackup="true" android:icon="@mipmap/appicon" android:roundIcon="@mipmap/appicon_round"
             android:supportsRtl="true" android:usesCleartextTraffic="true"></application>
```

Se prefiere el atributo a un `network_security_config` porque este último no acepta rangos de IP en `domain-config`, con lo que acabaría siendo un `base-config` equivalente al atributo pero con más piezas. La razón de negocio está en Q-27.

### 4.4 · Student: pantalla de conexión

| Cambio | Archivo | Detalle |
|---|---|---|
| Dirección por defecto | `Pages/ConnectionPage.xaml` | Quitar `http://192.168.1.10:8000`; proponer la última usada (`Preferences` `student_server`) o campo vacío con *placeholder* `192.168.0.55:8000` a modo de ejemplo (Q-35) |
| Tres estados de la comprobación | `Pages/ConnectionPage.xaml.cs` | Usar la respuesta completa de `/health/`: sin respuesta → «No encontramos el aula»; `biblioteca.disponible=false` → «Aula encontrada, pero la biblioteca está cerrada en el equipo del profesor» + `sugerencia`; ambas → «Conectado al aula correctamente» |
| Salud con detalle | `Avacom.Lms.Core/Services/LmsApiClient.cs` | `CheckHealthAsync` hoy devuelve `bool`; añadir una variante que devuelva el estado (o usar `BibliotecaDeContenido.EstadoAsync`, que ya lee `/api/biblioteca/estado/`) |
| Sin cambios | `Sesion.cs`, `CursoBibliotecaPage`, `CourseContentView` | Ya construyen todo desde `BaseUri` y ya degradan (RF-L02, RF-L09) |

### 4.4 bis · Student: pantalla «Tus cursos» con el aspecto de OPS

La pantalla de Student ya comparte con OPS los hexágonos (`ProfessorHexTile`), el encabezado «Lista completa» y la tarjeta por curso. Lo que falta para cumplir el resultado esperado 2 y 4:

| Cambio | Archivo | Detalle |
|---|---|---|
| Títulos | `Pages/AsignaturasPage.xaml`, `.xaml.cs` | Cabecera: «Asignaturas» → **«Tus cursos»**. Encabezado: `SaludoLabel` deja de decir «Tus cursos, {nombre}» y dice **«Tus cursos»**; el nombre pasa al subtítulo («Elige una asignatura, {nombre}. Tu avance se guarda solo») |
| Chip de estado como en OPS | `Pages/AsignaturasPage.xaml.cs` | Con biblioteca: «● Biblioteca conectada · N curso(s) · capacidades» (hoy sólo «N curso(s) disponibles»). Sin biblioteca: «● Biblioteca no disponible». Se toma de `RespuestaCursos.Capacidades`, que el backend ya envía |
| Tarjeta | `Pages/AsignaturasPage.xaml.cs` · `Fila` | Añadir la tercera línea de OPS: `{curso.Detalle} · ref {curso.CursoRef}`; botón «Entrar» → **«Abrir curso»**, ancho 150; toda la tarjeta responde al toque como en OPS. Se conserva la barra de progreso, que es lo que Student añade |
| Conteo y huella | `Pages/AsignaturasPage.xaml` | Junto a «Lista completa», la etiqueta «N curso(s) · huella …» de OPS, además del botón «Actualizar» |
| Bloque informativo | `Pages/AsignaturasPage.xaml` | Variante estudiantil de «¿Falta un curso?»: «Los cursos los decide tu escuela en AVACOM Biblioteca. Si falta uno, avisa a tu profesor» |
| Sin cambios | `AbrirAsync` y la navegación a `curso-biblioteca` | Resultado esperado 3 ya está cubierto por `CursoBibliotecaPage` + `CourseContentView` |

Lo que **no** se copia de OPS: el texto «se registra lo que hacen los estudiantes» y el botón «Mostrar en el aula», que son del docente.

### 4.5 · OPS: mostrar la dirección a dictar

| Cambio | Archivo | Detalle |
|---|---|---|
| `direcciones_lan` en `/health/` | `backend/expediente/views.py` · `HealthView` | Lista de IPv4 del equipo distintas de `127.*`, obtenida con `socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)`. Aditivo: ningún cliente actual se rompe |
| Prueba | `backend/expediente/tests.py` | `/health/` con `HTTP_HOST="192.168.0.55:8000"` → 200 y `direcciones_lan` es una lista (CA-L11) |
| Mostrarla | `src/Avacom.Lms.Ops/Pages/LoginPage.xaml(.cs)` y/o `DashboardPage.xaml` | Texto «Dirección para las tabletas: `http://192.168.0.55:8000`». Si hay varias, todas, con la nota «usa la de la red del aula». Si OPS corre en el mismo equipo, puede filtrar adaptadores virtuales con `NetworkInterface` (Q-30) |

### 4.6 · Secuencia de una sesión desde la tableta

Las mismas llamadas que hoy hace Student en loopback, con otro host:

| Paso | Petición desde la tableta | Respuesta esperada |
|---|---|---|
| 1 | `GET /health/` | 200, `biblioteca.disponible: true`, `direcciones_lan` |
| 2 | `GET /api/students/{persona}/courses/` | 200 con los cursos ofrecidos y el progreso de la persona |
| 3 | `GET /api/biblioteca/cursos/{curso_ref}/?persona=` | 200 con el árbol vigente anotado |
| 4 | `POST /api/aperturas/` | 201 con `progreso_seccion` y `progreso_curso` |
| 5 | `GET /api/biblioteca/medio/{ref}/` con `Range` | 206 con `Content-Range` (video) o 200 (lámina, PDF, `index.html` del interactivo) |
| 6 | `POST /api/aperturas/{id}/cerrar/` | 200 |
| 7 | `POST /api/intentos/start/` → `answer/` → `finish/` | 200/201; el veredicto llega de la biblioteca por loopback, nunca la clave |
| 8 | (OPS) `GET /api/cursos/{curso_ref}/consolidado/` | 200 con la fila del estudiante de la tableta |

### 4.7 · Degradación por capa

| Capa que falla | Cómo se ve desde la tableta | Qué responde el backend | Qué escribe |
|---|---|---|---|
| Red LAN o IP equivocada | `HttpRequestException` / tiempo de espera | Nada | Nada |
| Cortafuegos del equipo maestro | Tiempo de espera (la conexión no se rechaza, se descarta) | Nada | Nada |
| Backend apagado | Conexión rechazada | Nada | Nada |
| Backend encendido, biblioteca cerrada, ruta de contenido | 503 con `motivo` y `sugerencia` | `BibliotecaNoDisponible` → 503 | Nada |
| Backend encendido, biblioteca cerrada, ruta de expediente | 200 con `disponible: false` y `aviso` | Expediente + aviso | Nada nuevo |
| Capacidad no publicada | 501 con `capacidades` | `_exigir` | Nada |
| Android sin texto claro permitido | Excepción **local** antes de salir a la red | No llega nada al backend | Nada; queda en `fallos-student.log` |

| WebSocket caído (red, backend reiniciado) | El cliente recibe cierre o excepción; HTTP sigue funcionando | Nada por el socket | Nada; OPS muestra «sin señal en vivo» (Q-38) |

La regla estructural se conserva: **«no se pudo comprobar» no es «no está»**. Un fallo de red se cuenta como «no hay conexión con el aula», nunca como «el curso desapareció»; un socket caído se cuenta como «sin señal en vivo», nunca como «nadie está viendo el quiz».

### 4.8 · Sesión en vivo con Django Channels (Q-28)

**Objetivo acotado.** Una sola pregunta en vivo: *¿cuántos estudiantes están viendo este quiz ahora?* Todo lo demás (progreso, respuestas, notas) sigue yendo por HTTP y quedando en el expediente. La presencia no se guarda (RF-L17).

**Backend.**

| Pieza | Detalle |
|---|---|
| Dependencias | `channels` y `daphne` en `backend/requirements.txt`. Con `"daphne"` como primera app de `INSTALLED_APPS`, `manage.py runserver 0.0.0.0:8000` sirve HTTP y WebSockets en el mismo puerto: el comando de arranque **no cambia** |
| `settings.py` | `ASGI_APPLICATION = "avacom_lms.asgi.application"` (ya está); `CHANNEL_LAYERS` con `InMemoryChannelLayer` (Q-36) |
| `asgi.py` | `ProtocolTypeRouter({"http": get_asgi_application(), "websocket": URLRouter(aula.routing.websocket_urlpatterns)})`. Sin `AuthMiddlewareStack`: no hay autenticación (Q-04) |
| App `aula` | `routing.py`, `consumers.py`, `tests.py`. **Sin `models.py` con modelos**: la prueba de esquema de `FronteraTests` debe seguir contando 8 tablas |
| Ruta | `ws://<IP>:8000/ws/quiz/<evaluacion_ref>/?role=estudiante\|docente&persona=<persona_id>` |
| Consumidor | `QuizEnVivoConsumer(AsyncJsonWebsocketConsumer)`: al conectar se une al grupo `quiz.<evaluacion_ref>`; si `role=estudiante`, incrementa el conteo del grupo en memoria y difunde `presence_changed`; al desconectar (cierre limpio o pérdida de red) decrementa y difunde. `role=docente` sólo escucha. `persona` repetida desde dos tabletas cuenta una vez (conjunto de `persona_id`, no contador) |
| Evento | `{"type": "presence_changed", "evaluacion_ref": "…", "viendo": 2, "personas": ["ethan-martinez", "ana-perez"]}`. Se emite al unirse, al salir, y como respuesta a `{"type": "ping"}` → `{"type": "pong", …}` para que OPS confirme que la señal sigue viva |
| Cierres | `4400` si falta `role` o `persona` con `role=estudiante`; `4404` si la `evaluacion_ref` está vacía. Se conservan los códigos de [04-plan.md](04-plan.md) §3.4 |
| Lo que **no** hace | No lee ni escribe expediente; no consulta la biblioteca; no valida que la evaluación exista (eso lo hace HTTP al montar el intento). Una capacidad ausente no cambia la presencia: es sólo quién está mirando |

**Clientes.**

| Pieza | Detalle |
|---|---|
| `ActivitySocketClient` | Se conserva y se parametriza la ruta (`ws/quiz/{ref}/` en lugar de `ws/activities/{id}/`); acepta `persona`. La URL base sale de `ConnectionOptions.WebSocketBaseUri`, que ya deriva `ws://` de la dirección HTTP: la tableta llega por `ws://192.168.0.55:8000/` |
| Student | Al abrir una evaluación en `CourseContentView` (modo estudiante) conecta como `estudiante`; al cerrar el visor o salir del curso, cierra el socket. Si el socket falla, **el quiz sigue funcionando** por HTTP: la presencia es opcional |
| OPS | Al abrir una evaluación en modo docente conecta como `docente` y pinta el indicador: «N estudiantes viendo este quiz» con la lista de nombres al tocarlo. Sin conexión o tras cierre: «sin señal en vivo» (Q-38). El mismo indicador puede mostrarse en «Estudiantes y progreso» junto a cada evaluación |
| Android | El atributo `usesCleartextTraffic` de §4.3 cubre también `ws://`; no hace falta nada más |
| Cortafuegos | Nada nuevo: mismo puerto 8000 |

**Constitución.** La presencia es un hecho del aula en curso, no del expediente (artículo 13: no se puede volver a generar lo que no se guardó, y aquí **no hay nada que guardar**). No hay tabla, no hay auditoría, no hay clave. Si más adelante se quiere «quién estuvo en el quiz», eso ya lo responde `m05_apertura_material` e `Intento`, que sí son expediente.

---

## 5 · Errores

Lo que el backend responde cuando la biblioteca falla no cambia; se añade la capa de red, que el backend no ve y que sólo el cliente puede explicar.

| Situación | Estado de la biblioteca | El backend responde | Student muestra |
|---|---|---|---|
| Ficha ausente o inválida | 401 | 502 con el detalle | «El backend respondió 502» + detalle; reintentar |
| Referencia inexistente | 404 | 404 con la referencia, sin inventar un título | «No se pudo leer el curso» + detalle |
| Capacidad no publicada | 501 | 501 con la lista de capacidades | El material o la evaluación no se abre; se explica qué capacidad falta |
| Componente cerrado o nota ausente | — | 503 con motivo y sugerencia | Aviso «AVACOM Biblioteca está cerrada en el equipo del aula» + expediente |
| Backend apagado, IP equivocada o cortafuegos | — | *(sin respuesta)* | «No hay conexión con el aula» + reintentar + modo demo |
| Android bloquea texto claro (sin RF-L05) | — | *(la petición no sale de la tableta)* | Igual que el anterior, pero el registro de fallos dice `Cleartext HTTP traffic … not permitted` |
| `Host` no permitido | — | 400 de Django | No debe ocurrir: `ALLOWED_HOSTS = ["*"]` |
| WebSocket sin `role` o sin `persona` | — | Cierre `4400` | El quiz sigue por HTTP; OPS: «sin señal en vivo» |
| WebSocket con `evaluacion_ref` vacía | — | Cierre `4404` | Igual que el anterior |
| WebSocket caído a mitad del quiz | — | *(nada)* | Student: nada visible, el quiz continúa; OPS: «sin señal en vivo» hasta reconectar |

---

## 6 · Tareas

Cada tarea indica si **conserva**, **prueba**, **corrige** o **documenta** comportamiento. `[P]` marca las que pueden ir en paralelo sin escribir los mismos archivos.

| ID | Acción | Tipo | Archivos | Verificación |
|---|---|---|---|---|
| T-L01 `[P]` | Confirmar o crear la regla de entrada TCP 8000 en perfil *Any* en el equipo maestro | conserva | *(configuración del host)* | `Get-NetFirewallRule` la lista; `Test-NetConnection <IP> -Port 8000` desde otro equipo → `True` |
| T-L02 `[P]` | Script de diagnóstico de red del aula: IP por adaptador, perfil de red, regla 8000, quién escucha en 8000, `GET /health/` por loopback y por la IP LAN | prueba | `backend/tools/diagnostico_red.ps1` | Ejecutado en el equipo de prueba imprime `192.168.0.55`, Público, regla presente, PID en 8000, dos 200 |
| T-L03 `[P]` | Declarar `android:usesCleartextTraffic="true"` en el manifiesto de Student | corrige | `src/Avacom.Lms.Student/Platforms/Android/AndroidManifest.xml` | `dotnet build -f net10.0-android` y el manifiesto de `obj/…/android/AndroidManifest.xml` lo contiene (CA-L10) |
| T-L04 | `LmsApiClient`: variante de salud que devuelve el estado (`biblioteca.disponible`, `sugerencia`, `direcciones_lan`) | corrige | `src/Avacom.Lms.Core/Services/LmsApiClient.cs`, `Models/BibliotecaModels.cs` | Prueba en `tests/Avacom.Lms.Core.Tests` que deserializa un `/health/` de ejemplo |
| T-L05 | Student: dirección por defecto (Q-35) y tres estados de «Comprobar conexión» (RF-L04) | corrige | `src/Avacom.Lms.Student/Pages/ConnectionPage.xaml(.cs)` | Los tres escenarios de §7.2 producen tres mensajes distintos; la dirección sobrevive al reinicio |
| T-L06 `[P]` | Backend: `direcciones_lan` en `/health/` y prueba con `HTTP_HOST` de una IP LAN | corrige | `backend/expediente/views.py`, `backend/expediente/tests.py` | `manage.py test` en verde; CA-L11 |
| T-L07 | OPS muestra la dirección para las tabletas (RF-L07) | corrige | `src/Avacom.Lms.Ops/Pages/LoginPage.xaml(.cs)`, `DashboardPage.xaml` | En el equipo de prueba aparece `http://192.168.0.55:8000` y no `172.31.224.1` |
| T-L08 | Documentar «Prueba en LAN»: pasos, perfil de red, cortafuegos, hotspot como alternativa, Android en texto claro | documenta | `backend/README.md`, `README.md`, `docs/architecture.md` | Una persona sin contexto reproduce §7.2 sólo con la documentación |
| T-L09 | Prueba negativa: desde la tableta el puerto de `enlace.json` no responde (RF-L11) | prueba | *(manual, registrada en §7.3)* | `Test-NetConnection <IP> -Port <efímero>` → `False` |
| T-L10 | Ejecutar la lista de §7.2 con una tableta Android y un portátil Windows; registrar resultados en §7.3 | prueba | este documento | Todos los CA-L en verde o con hallazgo anotado |
| T-L11 `[P]` | Student: títulos «Tus cursos», chip con capacidades, tarjeta con `Detalle` y `curso_ref`, botón «Abrir curso», conteo y huella, bloque informativo (§4.4 bis) | corrige | `src/Avacom.Lms.Student/Pages/AsignaturasPage.xaml(.cs)` | Compila para Windows y Android; CA-L12, CA-L13 con captura lado a lado |
| T-L12 `[P]` | Backend: `channels` + `daphne`, `CHANNEL_LAYERS` en memoria, `ProtocolTypeRouter` en `asgi.py`, app `aula` sin modelos | corrige | `backend/requirements.txt`, `backend/avacom_lms/settings.py`, `backend/avacom_lms/asgi.py`, `backend/aula/` | `runserver` dice «Starting ASGI/Daphne»; `FronteraTests` sigue contando 8 tablas; CA-L05 sigue en verde sobre ASGI |
| T-L13 | Backend: `QuizEnVivoConsumer` con conjunto de personas por grupo, `presence_changed`, `ping`/`pong`, cierres 4400/4404, y prueba con `WebsocketCommunicator` | corrige | `backend/aula/consumers.py`, `routing.py`, `tests.py` | CA-L17 en verde |
| T-L14 | Core: `ActivitySocketClient` parametrizado a `ws/quiz/{ref}/` con `persona`; reconexión sencilla con espera creciente | corrige | `src/Avacom.Lms.Core/Services/ActivitySocketClient.cs` | Prueba unitaria de la URL generada (`ws://192.168.0.55:8000/ws/quiz/co-sec-mat-eval-funcion/?role=estudiante&persona=…`) |
| T-L15 | Student conecta como `estudiante` al abrir un quiz y cierra al salir; OPS conecta como `docente` y pinta el indicador con «sin señal en vivo» por defecto | corrige | `src/Avacom.Lms.Ui/Controls/CourseContentView.xaml(.cs)`, `src/Avacom.Lms.Ops/Pages/CursoBibliotecaPage.xaml(.cs)` | CA-L14, CA-L16 con dos tabletas |

Dependencias: T-L04 → T-L05; T-L06 → T-L07; T-L12 → T-L13 → T-L15; T-L14 → T-L15; T-L08 después de T-L03..T-L07 y T-L11..T-L15; T-L10 al final. T-L01, T-L02, T-L03, T-L06, T-L11 y T-L12 no comparten archivos y pueden empezar hoy.

Ruta crítica para Android: **T-L03**. Sin ella ninguna otra tarea produce una tableta funcional.
Ruta crítica para el indicador en vivo: **T-L12 → T-L13 → T-L15**.

---

## 7 · Verificación

### 7.1 · Lo comprobado en el equipo maestro el 2026-09-10

Hechos observados, no supuestos:

| Comprobación | Resultado |
|---|---|
| Quién escucha en 8000 | `TCP 0.0.0.0:8000 LISTENING`, PID 3952, `python.exe` del sistema (no el del `.venv`) |
| `GET http://192.168.0.55:8000/health/` desde el propio equipo | 200 · `biblioteca.disponible: true` · contrato 1 · `huella_catalogo h944a694c3fbe3213` · capacidades `curso, medio, leccion, evaluacion, comprobar, voz` · 2 cursos, 2 paquetes, 10 elementos |
| `GET http://127.0.0.1:8000/health/` | 200 |
| Red | Wi‑Fi «Makers», perfil **Público**, conectividad a Internet; IPv4 `192.168.0.55` (aula) y `172.31.224.1` (adaptador virtual) |
| Cortafuegos | Regla «AVACOM OPS Core (TCP 8000)»: entrada, TCP 8000, perfil *Any*, programa *Any*, habilitada, permitir. Perfiles Dominio/Privado/Público habilitados con acción de entrada por defecto no configurada (bloquear) |
| Manifiesto Android generado | `targetSdkVersion 36`, `debuggable true`, **sin** `usesCleartextTraffic` → RF-L05 pendiente y bloqueante para Android |
| WebSockets | `requirements.txt`: Django 5.2.3 y DRF 3.16.1, sin Channels; `asgi.py` es el de Django; `ActivitySocketClient` sin usos en OPS ni Student → Q-28 exige T-L12..T-L15 |
| Dirección que muestra OPS | Ninguna (`DashboardPage` y `LoginPage` no la enseñan); Student propone `http://192.168.1.10:8000` |
| Pantalla de cursos de Student frente a OPS | Comparten hexágonos, «Lista completa» y tarjeta. Difieren: cabecera «Asignaturas» (OPS: «Asignaturas · cursos de AVACOM Biblioteca»), encabezado «Tus cursos, {nombre}», botón «Entrar» (OPS: «Abrir curso»), sin línea `Detalle · ref`, chip sin capacidades, sin conteo ni huella, sin bloque «¿Falta un curso?» → T-L11 |
| Hard-codes de host en clientes | Sólo valores por defecto: `Sesion.DireccionPorDefecto`, `ConnectionOptions.Default`, `LoginPage`, `ConnectionPage` |

**No comprobado en esta sesión**: nada desde un segundo equipo. La prueba desde tableta y portátil (CA-L01..CA-L09) queda para T-L10.

### 7.2 · Lista de comprobación de la prueba LAN

En el **equipo maestro**:

1. Biblioteca abierta en «Contenido AVACOM» con licencia. Comprobar que existe `%ProgramData%\AVACOM\contenido\enlace.json`.
2. Backend:

   ```powershell
   cd backend; .venv\Scripts\python manage.py runserver 0.0.0.0:8000
   ```

3. Comprobar escucha y salud:

   ```powershell
   netstat -ano | findstr :8000
   ```

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8000/health/ | ConvertTo-Json -Depth 4
   ```

4. IP LAN y perfil:

   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' } | Select-Object InterfaceAlias, IPAddress
   ```

   ```powershell
   Get-NetConnectionProfile | Select-Object Name, InterfaceAlias, NetworkCategory
   ```

5. Regla de cortafuegos:

   ```powershell
   Get-NetFirewallRule -Direction Inbound -Enabled True | Where-Object { ($_ | Get-NetFirewallPortFilter).LocalPort -eq 8000 } | Select-Object DisplayName, Profile, Action
   ```

6. OPS abierto con `http://127.0.0.1:8000`; anotar la dirección que muestra para las tabletas (RF-L07).

En un **portátil Windows** de la misma red:

7. Alcance del puerto:

   ```powershell
   Test-NetConnection 192.168.0.55 -Port 8000
   ```

8. Salud por la LAN:

   ```powershell
   Invoke-RestMethod http://192.168.0.55:8000/health/ | ConvertTo-Json -Depth 4
   ```

9. Student (Windows): nombre + `192.168.0.55:8000` → «Comprobar conexión» → «Entrar al aula» → **Tus cursos** (comparar con la pantalla de OPS: mismos hexágonos, misma lista, «Abrir curso») → curso → abrir lámina, PDF, video, interactivo → evaluación → Finalizar.

En la **tableta Android**:

10. En el navegador de la tableta abrir `http://192.168.0.55:8000/health/`. Debe verse el JSON (CA-L01). Si no se ve, el problema es de red o cortafuegos, no de la app.
11. Student (Android): mismo recorrido que el paso 9. Si la app dice «No encontramos el aula» pero el navegador sí ve el JSON, el problema es el texto claro (RF-L05): revisar `fallos-student.log`.
12. Prueba negativa: `Test-NetConnection 192.168.0.55 -Port <Puerto de enlace.json>` desde el portátil → `TcpTestSucceeded: False` (CA-L08).

Degradación, con las dos tabletas dentro del curso:

13. Cerrar la biblioteca → en Student, «Actualizar»: aviso + expediente (CA-L06). Reabrirla → «Actualizar»: contenido de vuelta.
14. Detener el backend (Ctrl+C) → en Student, «Actualizar»: «No hay conexión con el aula» (CA-L07). Reiniciarlo → vuelve.
15. En OPS, «Estudiantes y progreso» → «Actualizar»: aparecen las dos personas con sus aperturas y notas (CA-L03, CA-L04, CA-L09).

Sesión en vivo (Q-28), con OPS dentro de la evaluación del curso de Matemáticas:

16. La tableta y el portátil entran a la misma evaluación → el indicador de OPS dice «2 estudiantes viendo este quiz» (CA-L14). Comprobar en la consola del backend que el *handshake* llegó por `ws://192.168.0.55:8000/ws/quiz/…` (CA-L15).
17. El portátil cierra el visor → «1 estudiante viendo este quiz».
18. Detener el backend → OPS: «sin señal en vivo»; la tableta sigue pudiendo contestar cuando el backend vuelve (CA-L16).
19. En el equipo maestro, `manage.py test` incluye la prueba del consumidor en verde (CA-L17).

### 7.3 · Registro de resultados (a rellenar en T-L10)

| Criterio | Windows | Android | Observación |
|---|---|---|---|
| CA-L01 · `/health/` desde el otro equipo | | | |
| CA-L02 · mismos cursos y huella | | | |
| CA-L03 · apertura reflejada en el consolidado | | | |
| CA-L04 · nota en resultados y consolidado | | | |
| CA-L05 · video con 206 | | | |
| CA-L06 · biblioteca cerrada y reabierta | | | |
| CA-L07 · backend apagado | | | |
| CA-L08 · puerto efímero no accesible | | | |
| CA-L09 · dos expedientes separados | | | |
| CA-L10 · manifiesto con texto claro | — | | |
| CA-L11 · prueba `HTTP_HOST` en verde | | | |
| CA-L12 · lista de cursos con el aspecto de OPS | | | |
| CA-L13 · títulos «Tus cursos» | | | |
| CA-L14 · indicador «2 → 1 estudiantes viendo» | | | |
| CA-L15 · WebSocket por el puerto 8000 | | | |
| CA-L16 · «sin señal en vivo» con el backend apagado | | | |
| CA-L17 · prueba del consumidor en verde | — | — | |

---

## 8 · Riesgos y límites

| Riesgo o límite | Mitigación |
|---|---|
| Wi‑Fi con aislamiento de clientes: la regla existe, el backend escucha y aun así la tableta no llega | Red del aula sin aislamiento o punto de acceso móvil del equipo maestro (Q-32) |
| Android bloquea texto claro y la app parece «sin red» | RF-L05 / T-L03; el paso 10 de §7.2 separa red de app |
| Regla de cortafuegos por programa que deja de aplicar al cambiar de `python.exe` | Regla de **puerto** (T-L01) |
| La IP cambia por DHCP entre sesiones | Reserva DHCP, o hotspot; OPS muestra siempre la vigente (RF-L07) |
| Adaptadores virtuales (Hyper‑V, WSL) confunden al docente | Filtro en OPS o nota «usa la de la red del aula» (Q-30) |
| Sin autenticación (Q-04): cualquiera en la LAN lee expediente y registra aperturas | Aceptado para un aula cerrada de prototipo; anotado. La biblioteca sigue fuera del alcance de la LAN |
| Servidor de desarrollo de Django con varias tabletas reproduciendo video | Suficiente para la prueba; medir. Un servidor de producción no cambia el contrato (Q-34) |
| SQLite con escrituras simultáneas de varias tabletas | Aula pequeña: aceptable. Si aparece `database is locked`, subir `timeout` de la conexión antes de pensar en otro motor |
| Suspensión o apagado del equipo maestro | Corta la clase entera; desactivar la suspensión durante la prueba |
| PDF en Android se abre fuera de la app con una URL `http://` | Límite ya conocido; con texto claro permitido el visor del sistema puede descargarlo, pero no forma parte de los CA-L |
| Dos estudiantes con el mismo nombre comparten expediente | Nombres distintos en la prueba (Q-33); en el indicador en vivo cuentan como una sola persona |
| Capa de canales en memoria: si el backend se reinicia, el conteo vuelve a cero hasta que los clientes reconecten | Reconexión sencilla en `ActivitySocketClient` (T-L14) y «sin señal en vivo» mientras tanto (Q-38) |
| Tentación de convertir la presencia en expediente («quién estuvo en el quiz») | Está prohibido por RF-L17; esa pregunta ya la responden `m05_apertura_material` e `Intento` |
| Wi‑Fi que corta conexiones largas (ahorro de energía de la tableta) | `ping`/`pong` cada 20–30 s desde el cliente y reconexión; no afecta al expediente |

## 9 · Lo que este documento NO cambia

- El contrato con AVACOM Biblioteca ([06-contrato-biblioteca.md](06-contrato-biblioteca.md)) y su transporte por loopback.
- El modelo de datos del expediente y la ausencia de tablas de curso (artículos 13 y 14). La app `aula` no añade ninguna tabla.
- Las rutas HTTP del backend, salvo el campo aditivo `direcciones_lan` en `/health/` (Q-30). La ruta WebSocket de §4.8 es nueva y aditiva.
- La regla de que ninguna respuesta al estudiante trae una clave. Por el socket sólo viajan conteos y `persona_id`.
