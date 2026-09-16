# Instalador de AVACOM OPS Master

Produce un único `.exe` que instala en un equipo Windows la aplicación del
profesor y la API local del aula, sin pedirle al usuario que escriba nada.

```text
installer/
├── build/
│   ├── Build-Installer.ps1     Un comando: del código fuente al .exe
│   ├── Get-PythonRuntime.ps1   Ensambla el Python embebido con Django/DRF/Waitress
│   ├── Distribucion.props      Propiedades de publicación (no toca ningún .csproj)
│   ├── New-ImagenesAsistente.ps1  Imágenes de marca de las pantallas del asistente
│   ├── New-ProbadorBat.ps1     Empaqueta el diagnóstico en un .bat autocontenido
│   ├── Verificar-Asistente.ps1 Ejecuta las comprobaciones del asistente de verdad
│   └── PruebaAsistente.iss     Arnés: la misma lógica, sin nada que instalar
├── src/
│   ├── AvacomOpsMaster.iss     El asistente (Inno Setup 6): 8 pantallas
│   ├── definiciones.iss        Nombres, versión, puerto y servicio, en un sitio
│   ├── codigo.iss              La lógica del asistente (compartida con el arnés)
│   ├── informacion.txt         Pantalla 2 · Información de AVACOM LMS 2.0
│   ├── host/                   Avacom.Ops.Host: servicio, lanzador y preparación
│   └── payload/
│       ├── avacom_ops_backend.py       Arranque de Waitress
│       └── requirements-runtime.txt    Dependencias que viajan en el paquete
├── tools/
│   ├── AVACOM-Probar-Comunicacion.bat  Diagnóstico en UN archivo (lo que se distribuye)
│   └── Probar-Comunicacion.ps1         Su código fuente
└── latest/
    ├── AVACOM-OPS-Master-Setup-<versión>.exe
    └── SHA256.txt
```

## Construirlo

```powershell
powershell -ExecutionPolicy Bypass -File installer\build\Build-Installer.ps1
```

Requiere, **solo en el equipo de compilación**: .NET SDK 10, Python 3.12 e
Inno Setup 6 (`winget install JRSoftware.InnoSetup`), y acceso a internet la
primera vez, para descargar el runtime de Python que después viaja dentro del
paquete.

El script pasa las pruebas del backend, publica la app, ensambla el runtime,
copia el backend, escribe el manifiesto, **verifica el asistente** y lo compila.
Si algo falla, se detiene: no produce un instalador a medias. Con `-OmitirApp`
reutiliza la publicación anterior de la app, que es la etapa lenta.

## Comprobar un equipo sin instalar nada

El propio instalador sabe diagnosticar sin tocar el equipo. Con `/VOLCADO`
ejecuta sus nueve comprobaciones, las escribe en un archivo y aborta:

```powershell
.\AVACOM-OPS-Master-Setup-2.0.0.exe /VERYSILENT /VOLCADO=C:	emp\diagnostico.txt
```

Eso es también lo que usa `Verificar-Asistente.ps1` en cada compilación: un
compilador comprueba la sintaxis del asistente, no que su lógica funcione en un
Windows real (parsear `netstat`, preguntar a `/health/` por COM, leer el
registro, crear los controles de la página táctil).

## Lo que instala

```text
AVACOM OPS Master
│
├── App\        Aplicación .NET MAUI, con el runtime de .NET y el
│               Windows App SDK dentro (no hay prerrequisitos)
├── Backend\    Django + Django REST Framework, tal cual está en backend\
├── Runtime\    Python 3.12 embebido + Django + DRF + Waitress
│               + Avacom.Ops.Host.exe (servicio, lanzador, preparación)
├── manifiesto.json
└── LEEME.txt
```

Y fuera de la carpeta del programa, porque cambia con el uso:

```text
%ProgramData%\AVACOM\OPS Master\Config    backend.env de este equipo
%ProgramData%\AVACOM\OPS Master\Data      ops-master.sqlite3 (el expediente)
%ProgramData%\AVACOM\OPS Master\Logs      instalacion, servicio, backend, lanzador
```

El expediente vive ahí porque es el único dato del sistema que no se puede
volver a generar: sobrevive a reinstalaciones y actualizaciones, y solo se
borra si en la desinstalación se pide expresamente.

## Cómo se ejecuta el backend

```text
Windows
   │
   ├── AVACOM OPS Master  (icono)
   │        └── Avacom.Ops.Host.exe iniciar
   │                 servicio en marcha → /health/ validado → interfaz
   │
   └── Servicio AVACOMOPSBackend   (Startup Type = Automatic)
            └── Avacom.Ops.Host.exe servicio
                     └── python.exe avacom_ops_backend.py
                              └── Waitress
                                       └── Django / DRF → 0.0.0.0:8000
```

`Startup Type = Automatic` es deliberado: el nodo debe atender a las tabletas
desde que arranca Windows, sin esperar a que alguien abra la interfaz. Si el
backend se cae, el servicio lo reinicia con espera creciente, y Windows
reinicia el servicio si es él el que muere.

No se usa `manage.py runserver`: es un servidor de desarrollo. Se usa
**Waitress**, que es un servidor WSGI de producción para Windows, sirviendo la
misma aplicación (`avacom_lms.wsgi.application`), con la misma configuración y
en la misma dirección: `0.0.0.0:8000`.

### Verbos de `Avacom.Ops.Host.exe`

| Verbo | Quién lo usa | Qué hace |
|---|---|---|
| `servicio` | El SCM de Windows | Punto de entrada del servicio |
| `iniciar` | El icono del escritorio | Backend → validación → interfaz |
| `preparar` | El instalador | Configuración del nodo, migraciones, validación |
| `salud [seg]` | El instalador | Espera a que `/health/` responda |
| `puerto-libre` | Diagnóstico | 0 libre · 12 nuestro backend · 13 ajeno |
| `instalar-servicio`, `quitar-servicio` | El instalador | Registro en el SCM |
| `iniciar-servicio`, `detener-servicio` | El instalador | Control del servicio |
| `abrir-firewall`, `cerrar-firewall` | El instalador | Regla TCP 8000 |

Ninguno pide interacción. El único que muestra algo es `iniciar`, y solo si el
backend no responde.

## Las ocho pantallas

| # | Pantalla | Qué ocurre |
|---|---|---|
| 1 | Bienvenido | — |
| 2 | Información de AVACOM LMS 2.0 | `informacion.txt` |
| 3 | Carpeta de instalación | `C:\Program Files\AVACOM\OPS Master` |
| 4 | Comprobación del equipo | 9 comprobaciones, con «Volver a comprobar» |
| 5 | Listo para instalar | Resumen de lo que se va a hacer |
| 6 | Instalando | Copia de archivos |
| 7 | Configuración del backend | Configuración, migraciones, servicio, firewall, validación |
| 8 | Instalación completada | Casilla para abrir el producto |

### Pantalla 4 · qué se comprueba

Windows 10/11 · arquitectura de 64 bits · espacio en disco · permisos de
administrador · **puerto 8000** · instalación previa · procesos activos ·
dependencias del backend · presencia de AVACOM Biblioteca.

Sobre el puerto 8000, el asistente distingue dos casos que se parecen y no son
lo mismo:

- **Lo ocupa un backend de AVACOM OPS** (se comprueba preguntando a
  `/health/`): es una reinstalación. Se avisa y se continúa; el propio
  instalador detiene su servicio antes de copiar archivos.
- **Lo ocupa otro programa**: la instalación se detiene con un mensaje
  entendible y **no cierra nada ajeno**. El usuario cierra ese programa y toca
  «Volver a comprobar».

## Pantalla táctil, sin teclado

El nodo principal del aula se maneja solo con toques, así que:

- ningún campo de texto es obligatorio: la caja de la ruta es de solo lectura
  y la carpeta se elige con «Examinar» o con el botón «Usar la carpeta
  recomendada»;
- la ventana se abre al 150 % y los botones del asistente miden 150 × 46 px;
- las casillas de tareas tienen 34 px de alto;
- cualquier aviso se cierra con un solo toque.

## La marca

Todo lo que se ve lleva el símbolo de AVACOM, y todo sale de un único archivo:
[`assets/avacom-symbol.svg`](../assets/avacom-symbol.svg).

| Dónde se ve | De dónde sale |
|---|---|
| Icono del instalador | `appicon.ico`, que MAUI genera de `Resources\AppIconppicon.svg` (placa blanca) + `appiconfg.svg` (el símbolo) |
| Icono del escritorio y del menú inicio | El mismo `appicon.ico` |
| Panel izquierdo de Bienvenido y de Instalación completada | `WizardImageFile` |
| Esquina superior derecha del resto de pantallas | `WizardSmallImageFile` |
| Pantalla de arranque de la aplicación | `Resources\Splash\splash.svg` |
| Tablero de AVACOM OPS Master | `Resources\Imagesvacom_mark.svg`, enlazado al asset |

Las dos imágenes del asistente las genera `New-ImagenesAsistente.ps1` en cada
compilación, a partir del símbolo que ya rasterizó la compilación de la
aplicación: así el asistente y el producto muestran la misma marca y no hay una
segunda copia que se desvíe.

Antes de esto, el icono era el cuadrado morado `#512BD4` de la plantilla de
.NET MAUI y el primer plano y el arranque eran el logotipo de .NET; el asistente
usaba además las ilustraciones genéricas de Inno Setup en cada pantalla. La
compilación ahora **falla** si el icono de la plantilla vuelve a aparecer.

## Diagnosticar la comunicación con AVACOM Biblioteca

Cuando en el aula «no aparecen los cursos», la causa puede estar en cualquiera
de los cuatro eslabones de la cadena, y desde la pantalla del profesor los
cuatro se ven igual. `AVACOM-Probar-Comunicacion.bat` los separa.

Es **un solo archivo**: se descarga de la release y se toca. No necesita nada al
lado. Al terminar deja en el escritorio un informe y un `.zip` con las
evidencias, y los abre.

Un `.bat` y no un `.ps1` por dos razones, las dos del equipo del aula: Windows
no ejecuta un `.ps1` con un doble toque —lo abre en el Bloc de notas— y, al
descargarlo de la release, lo marca como venido de internet y la política
`RemoteSigned` (la de fábrica) lo rechaza con *«no está firmado digitalmente»*.
El `.bat` lleva el PowerShell dentro, detrás de un marcador, lo extrae a un
temporal y lo ejecuta con la política en Bypass, que ignora esa marca.

Lo genera [`build/New-ProbadorBat.ps1`](build/New-ProbadorBat.ps1) desde
[`tools/Probar-Comunicacion.ps1`](tools/Probar-Comunicacion.ps1), que es la
única fuente. El generador extrae lo que quedaría incrustado y lo pasa por el
analizador de PowerShell: si no parsea, no hay archivo. Sin esa comprobación un
`.bat` roto sólo se descubre al ejecutarlo en el aula.

**No modifica nada**: solo lee y consulta. Códigos de salida: `0` todo bien ·
`1` hay algo que bloquea · `2` sólo avisos.

### Qué lleva el paquete de evidencias

```text
AVACOM-diagnostico-<fecha>.zip
├── informe.txt                        el diagnóstico legible
├── respuestas/
│   ├── biblioteca-salud.json          /v1/salud de la Biblioteca
│   ├── biblioteca-cursos.json         SUS cursos, preguntados directamente
│   ├── biblioteca-catalogo.json       su contenido instalado
│   ├── biblioteca-enlace.json         la nota de enlace (sin la ficha)
│   ├── lms-health.json                /health/ del backend
│   └── lms-cursos.json                los cursos que ENTREGA el LMS
└── logs/                              los registros del servicio
```

Las dos listas de cursos, una al lado de la otra, son lo que permite decidir
quién pierde los cursos sin tener acceso al equipo. La ficha de la Biblioteca se
sustituye antes de escribir nada: es una credencial y no sale del nodo.

Lo que comprueba, en orden:

| # | Eslabón | Qué distingue |
|---|---|---|
| 1–2 | Instalación y configuración del nodo | Si `AVACOM_CONTENIDO_ENLACE` quedó apuntando a la nota del host de pruebas |
| 3–4 | Servicio y puerto | Servicio parado, inicio no automático, un `runserver` compitiendo, escucha sólo en loopback |
| 5 | La API local | Si contesta, y si quien contesta en ese puerto es de verdad el backend |
| 6 | La nota de enlace | Nota ausente, incompleta, de una sesión anterior, o ilegible por la cuenta del servicio |
| 7 | **Contacto directo con la Biblioteca** | Habla con ella con la ficha de la nota, sin pasar por el backend |
| 8 | Lo que ve el backend | Compara 6 y 7 con `/health/` |
| 9 | Extremo a extremo por capacidad | `medio`, `leccion`, `evaluacion`, `voz` |
| 9 | **Cursos: Biblioteca vs LMS** | Compara los que ella tiene con los que él entrega |
| 10 | **Errores de Python** | Clasifica los tracebacks y marca los que ocurren en hilos de Waitress |
| 11 | Interfaz y tabletas | Regla de firewall, IP del nodo, interfaz de desarrollo abierta por error |

El apartado 7 es el que gana el diagnóstico. Dos fallos que se ven idénticos
desde el aula tienen causas opuestas:

- el script **no** alcanza la Biblioteca → el problema es de la Biblioteca
  (pestaña «Contenido AVACOM» sin abrir, nota vieja, puerto muerto);
- el script **sí** la alcanza y el backend no → el problema es del backend
  (nota forzada por variable de entorno, permisos de la cuenta del servicio, o
  el servicio arrastrando un error y necesitando reinicio).

El apartado 9 responde la pregunta del aula comparando recuentos, y sólo hay
tres desenlaces: la Biblioteca ofrece 0 (el problema es suyo, no hay contenido
publicado o la política de la escuela lo oculta), ofrece N y el LMS entrega N
(la cadena funciona y el fallo está en la interfaz), u ofrece N y el LMS entrega
0 (los cursos se pierden dentro del backend). Además prueba cada capacidad con
una referencia que a propósito no existe. No importa el contenido, importa **qué tipo** de fallo vuelve, porque
cada uno señala un eslabón distinto: `404` significa que la petición llegó
hasta la Biblioteca y volvió (el enlace funciona), `501` que el enlace funciona
pero la Biblioteca no publica esa capacidad, `503` que el backend no la
alcanza, y `502` que la Biblioteca falló por su cuenta.

### Errores de Python en hilos

Waitress sirve con ocho hilos, y un error dentro de uno de ellos es el más
difícil de ver: revienta una petición suelta, la interfaz muestra un cuelgue o
un 500, y el servicio sigue apareciendo «en marcha». El apartado 10 los busca
en los registros, los agrupa por excepción y marca con `Hilo ·` los de esa
clase: SQLite usado desde otro hilo, `database is locked` por concurrencia,
`SynchronousOnlyOperation`, `Exception while serving` de Waitress y bucles de
eventos ausentes. De cada grupo dice qué es y qué hacer.

Para analizar registros traídos de otro equipo, sin tocar ese equipo:

```powershell
.\Probar-Comunicacion.ps1 -CarpetaDeLogs C:\logs-del-nodo
```

## Convivencia con AVACOM Biblioteca

Los dos productos pueden estar en el mismo equipo. Nada se comparte salvo la
carpeta padre `%ProgramData%\AVACOM`, y ahí cada uno escribe solo lo suyo.

| | AVACOM OPS Master | AVACOM Biblioteca |
|---|---|---|
| Carpeta | `…\AVACOM\OPS Master` | `…\AVACOM\Biblioteca` |
| Datos | `%ProgramData%\AVACOM\OPS Master\Data` | `%ProgramData%\AVACOM\contenido` |
| Servicio | `AVACOMOPSBackend` | — |
| Puerto | TCP 8000 (LAN del aula) | loopback, puerto efímero |
| Regla de firewall | `AVACOM OPS Master Backend` | — |
| Menú inicio | `AVACOM OPS Master` | grupo propio |
| Desinstalación | Entrada propia | Entrada propia |

De la biblioteca solo se **lee** `%ProgramData%\AVACOM\contenido\enlace.json`,
y lo hace el backend en tiempo de ejecución, no el instalador.

## Desinstalar

Desde «Aplicaciones instaladas» de Windows. Detiene el servicio, lo quita del
SCM, retira la regla de firewall y borra los archivos del programa. Después
pregunta si eliminar también el expediente de los estudiantes; la respuesta por
defecto es **conservarlo**.

## Publicar el instalador

El instalador ronda los **94 MB**, muy cerca del límite de 100 MB por archivo
que acepta un push a GitHub, y cada versión añadiría otro tanto al historial.
Se distribuye como *release asset*, que es donde GitHub espera un binario:

```bash
gh release create v2.0.0 installer/latest/AVACOM-OPS-Master-Setup-2.0.0.exe installer/latest/SHA256.txt installer/tools/AVACOM-Probar-Comunicacion.bat --title "AVACOM OPS Master 2.0.0" --notes "Instalador de AVACOM OPS Master y su backend."
```

El `.bat` del diagnóstico se adjunta a la release para poder revisar un nodo sin
clonar el repositorio en él: se descarga y se toca.

En el repositorio quedan el código del instalador, el script que lo reconstruye
y `SHA256.txt`, que permite verificar el `.exe` descargado:

```powershell
Get-FileHash .\AVACOM-OPS-Master-Setup-2.0.0.exe -Algorithm SHA256
```
