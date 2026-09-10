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
gh release create v2.0.0 installer/latest/AVACOM-OPS-Master-Setup-2.0.0.exe installer/latest/SHA256.txt --title "AVACOM OPS Master 2.0.0" --notes "Instalador de AVACOM OPS Master y su backend."
```

En el repositorio quedan el código del instalador, el script que lo reconstruye
y `SHA256.txt`, que permite verificar el `.exe` descargado:

```powershell
Get-FileHash .\AVACOM-OPS-Master-Setup-2.0.0.exe -Algorithm SHA256
```
