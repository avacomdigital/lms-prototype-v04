# 08 · Instalador de AVACOM OPS Master

| Campo | Valor |
|---|---|
| Ámbito | Distribución, instalación, configuración inicial, ejecución y desinstalación de AVACOM OPS Master y su backend |
| Estado | Implementado |
| Código | [`installer/`](../installer/) · construcción con [`installer/build/Build-Installer.ps1`](../installer/build/Build-Installer.ps1) |
| Salida | `installer/latest/AVACOM-OPS-Master-Setup-<versión>.exe` |

Este documento registra las decisiones del instalador. La guía de uso está en
[`installer/README.md`](../installer/README.md).

---

## 1 · Lo que el instalador no es

El instalador **no** es una oportunidad para arreglar nada del producto. Se
mueve dentro de un límite estrecho, y ese límite es el valor del documento:

| Prohibido | Cómo se cumple |
|---|---|
| Cambiar el comportamiento funcional | No se editó un solo archivo de `backend/` ni de `src/`. La configuración se entrega por variables de entorno, que `avacom_lms/settings.py` **ya** lee |
| Cambiar la arquitectura | Las propiedades de publicación viven en `installer/build/Distribucion.props` y se inyectan con `-p:CustomBeforeMicrosoftCommonProps`, no en los `.csproj` |
| Añadir `/health/` | Ya existía en `avacom_lms/urls.py`. El instalador lo consume tal cual |
| Sobrescribir algo de AVACOM Biblioteca | Ver el artículo 4 |
| Pedir comandos al usuario | Todo ocurre en el asistente; los `sc.exe` y `netsh.exe` los ejecuta el instalador |

La única decisión de configuración con consecuencia visible es
`AVACOM_LMS_DEBUG=0` en una instalación distribuida. Es configuración, no
código: el backend ya soporta esa variable, el valor queda escrito y comentado
en `backend.env`, y la razón es que un `DEBUG=1` publica trazas con código
fuente a toda la LAN del aula.

---

## 2 · El backend se ejecuta como servicio, no como `runserver`

**Principio.** La API del aula existe con independencia de que alguien tenga
abierta la interfaz.

**Justificación.** Las tabletas piden material al equipo maestro. Si la API
viviera dentro del proceso de la interfaz, cerrar la ventana del profesor
dejaría al aula sin contenido, y encender el equipo no bastaría para dar clase.

```text
Windows
   └── Servicio AVACOMOPSBackend        Startup Type = Automatic
            └── Avacom.Ops.Host.exe servicio
                     └── python.exe avacom_ops_backend.py
                              └── Waitress
                                       └── Django / DRF → 0.0.0.0:8000
```

| # | Regla | Cómo se comprueba |
|---|---|---|
| 2.1 | Se usa Waitress, no `manage.py runserver` | `Runtime\avacom_ops_backend.py` llama a `waitress.serve`; no hay ninguna llamada a `runserver` en el paquete |
| 2.2 | La aplicación WSGI y la configuración son las del producto | Se importa `avacom_lms.wsgi.application` con `DJANGO_SETTINGS_MODULE=avacom_lms.settings` |
| 2.3 | La escucha es `0.0.0.0:8000` | Cabecera `Server: AVACOM OPS Backend` en `http://<ip>:8000/health/` |
| 2.4 | El servicio arranca con Windows | `sc qc AVACOMOPSBackend` muestra `AUTO_START` |
| 2.5 | Un backend caído se vuelve a levantar | El servicio reintenta con espera creciente (2 s → 60 s) y `sc failure` reinicia el servicio |
| 2.6 | El usuario del aula puede arrancarlo sin credenciales | `sc sdset` concede `RP`/`WP` a los usuarios interactivos **solo** sobre este servicio |

**Startup Type = Automatic** es explícito y deliberado, tal como pedía la
especificación: el nodo presta servicio LAN antes de que se abra la interfaz.

---

## 3 · El paquete es autosuficiente

**Principio.** Se puede instalar en un aula sin internet y sin que nadie
instale Python ni .NET.

| Componente | Cómo viaja |
|---|---|
| Aplicación .NET MAUI | Publicada con `SelfContained` y `WindowsAppSDKSelfContained`: el runtime de .NET y el Windows App SDK van dentro |
| Python 3.12 | Paquete *embeddable* de python.org, sin instalador ni registro |
| Django, DRF, Waitress, tzdata | Instalados en `Runtime\Python\Lib\site-packages` en el equipo de compilación |
| Backend AVACOM | Copiado de `backend/`, sin `.venv` ni la base de datos de desarrollo |

| # | Regla | Cómo se comprueba |
|---|---|---|
| 3.1 | La instalación no ejecuta `pip` ni `winget` | No aparecen en el `.iss` ni en `Avacom.Ops.Host.exe` |
| 3.2 | El runtime empaquetado importa lo que el backend necesita | `Get-PythonRuntime.ps1` falla la compilación si `import django, rest_framework, waitress, zoneinfo, sqlite3` no funciona |
| 3.3 | La app no necesita prerrequisitos | La compilación falla si faltan `hostfxr.dll` o `Microsoft.WindowsAppRuntime.dll` |
| 3.4 | No se distribuye la base de datos del desarrollador | La compilación falla si `db.sqlite3` aparece en el paquete |

Detalle del runtime embebido: con un `python312._pth` presente, Python arranca
aislado y **no** añade el directorio del script, ni `site-packages`, ni
`PYTHONPATH`. Las tres rutas se declaran en ese archivo, incluida
`..\..\Backend`, que es lo que permite que `manage.py migrate` importe
`avacom_lms` sin depender del directorio de trabajo.

---

## 4 · Convivencia con AVACOM Biblioteca

**Principio.** Los dos productos comparten el equipo y no comparten nada más.

| Recurso | AVACOM OPS Master | AVACOM Biblioteca |
|---|---|---|
| Identificador de instalación | `{B6D1F0A4-…-7F5C2E8D4A31}` | El suyo |
| Archivos | `…\AVACOM\OPS Master` | `…\AVACOM\Biblioteca` |
| Configuración | `%ProgramData%\AVACOM\OPS Master\Config` | La suya |
| Base de datos | `%ProgramData%\AVACOM\OPS Master\Data\ops-master.sqlite3` | La suya |
| Logs | `%ProgramData%\AVACOM\OPS Master\Logs` | Los suyos |
| Servicio | `AVACOMOPSBackend` | — |
| Puerto | TCP 8000 (LAN) | loopback, puerto efímero |
| Regla de firewall | `AVACOM OPS Master Backend` | — |
| Menú inicio | Grupo `AVACOM OPS Master` | Grupo propio |
| Procesos | `Avacom.Lms.Ops.exe`, `Avacom.Ops.Host.exe`, `python.exe` del runtime | Los suyos |

| # | Regla | Cómo se comprueba |
|---|---|---|
| 4.1 | Único punto de contacto: la nota de enlace, en modo lectura | `%ProgramData%\AVACOM\contenido\enlace.json` lo lee `backend/biblioteca/cliente.py`; el instalador no lo toca |
| 4.2 | `AVACOM_CONTENIDO_ENLACE` se deja sin definir | Así el backend busca la nota donde la biblioteca la publica de verdad |
| 4.3 | La carpeta padre compartida no se borra | `{commonappdata}\AVACOM` va con `uninsneveruninstall` |
| 4.4 | Desinstalar uno no afecta al otro | `AppId` distinto ⇒ entradas de desinstalación independientes |

El asistente además **informa** de la presencia de la biblioteca en la pantalla
de comprobación, y de su ausencia: sin ella el producto instala y arranca, pero
no habrá cursos que mostrar.

---

## 5 · El expediente sobrevive a la instalación

Consecuencia directa del artículo 13 de la constitución: el expediente es el
único dato del sistema que no se puede volver a generar.

| # | Regla | Cómo se comprueba |
|---|---|---|
| 5.1 | El expediente no vive en la carpeta del programa | `AVACOM_LMS_DB` apunta a `%ProgramData%\AVACOM\OPS Master\Data` |
| 5.2 | Reinstalar no lo borra ni lo mueve | `Configuracion.CrearSiFalta` no sobrescribe un `backend.env` existente; `migrate` sólo aplica lo que falte |
| 5.3 | Reinstalar no cambia la clave del nodo | Misma razón: la clave se genera una vez |
| 5.4 | Desinstalar lo conserva salvo petición expresa | La pregunta final tiene **No** como respuesta por defecto |

---

## 6 · El asistente

Ocho pantallas, en el orden que pedía la especificación:

```text
Bienvenido → Información AVACOM LMS 2.0 → Carpeta de instalación
   → Comprobación del equipo → Listo para instalar → Instalando
   → Configuración del backend → Instalación completada
```

### 6.1 · Pantalla táctil, sin teclado

El nodo principal del aula tiene pantalla táctil y **no tiene teclado**. El
asistente se maneja íntegramente con toques:

| Decisión | Motivo |
|---|---|
| Ningún campo de texto obligatorio | No hay teclado con el que rellenarlo |
| La caja de la ruta es de sólo lectura | Se elige con «Examinar» o con «Usar la carpeta recomendada» |
| Ventana al 150 %, botones de 150 × 46 px | Objetivos de toque, no de ratón |
| Casillas de 34 px de alto | Ídem |
| Cada aviso se cierra con un toque | Ningún diálogo pide escribir ni confirmar dos veces |

### 6.2 · La comprobación del equipo

Nueve comprobaciones, con un botón «Volver a comprobar» que las repite sin
salir de la pantalla:

Windows 10/11 · arquitectura de 64 bits · espacio en disco (1200 MB) ·
permisos de administrador · puerto 8000 · instalación previa · procesos
activos · dependencias del backend · presencia de AVACOM Biblioteca.

**El puerto 8000** merece su propia regla, porque la especificación era
explícita: no terminar en silencio y no detener procesos ajenos.

| Situación | Qué hace el asistente |
|---|---|
| Libre | Continúa |
| Ocupado, y `/health/` responde `avacom-lms-backend` | Es una reinstalación: avisa, continúa, y detiene su propio servicio antes de copiar archivos |
| Ocupado por otro programa | Se detiene con un mensaje entendible y **no cierra nada** |

Distinguir los dos últimos casos es lo que evita que una actualización normal
se presente al usuario como un conflicto.

### 6.3 · La configuración del backend

Todo lo que el `README.md` del backend pide a una persona, ejecutado sin que
nadie escriba un comando:

| Paso | Equivalente manual |
|---|---|
| Configuración local del nodo | Redactar un `.env` con la clave y las rutas |
| Verificación del runtime | `import django, rest_framework, waitress` |
| Revisión de configuración | `manage.py check` |
| Base de datos del expediente | `manage.py migrate` |
| Archivos estáticos | `manage.py collectstatic`, **sólo si** el backend declara `STATIC_ROOT`; hoy no lo declara y no hay nada que recoger |
| Validación de ejecución | El puerto está disponible y `/health/` responde |
| Servicio y firewall | `sc create` + `netsh advfirewall` |

Es idempotente: repetirlo en una actualización no pierde nada.

---

## 6.4 · La marca es la de AVACOM, y sale de un solo sitio

La plantilla de .NET MAUI trae el logotipo de Microsoft: `appicon.svg` era el
cuadrado morado `#512BD4` y `appiconfg.svg` y `splash.svg` eran el logotipo de
.NET. Inno Setup, por su parte, pone sus propias ilustraciones en todas las
pantallas si no se le dan otras. Resultado: un logo ajeno repetido en el icono,
los accesos directos, el arranque y cada pantalla del asistente.

Fuente única: [`assets/avacom-symbol.svg`](../assets/avacom-symbol.svg).

| # | Regla | Cómo se comprueba |
|---|---|---|
| 6.4.1 | El símbolo no se duplica a mano | `avacom_mark` se enlaza al asset desde el `.csproj`, siguiendo la convención que ya usaba `ColorHexagon`; icono y arranque solo envuelven sus trazos en otro lienzo |
| 6.4.2 | Las imágenes del asistente son el mismo símbolo | `New-ImagenesAsistente.ps1` las compone del PNG que rasterizó la compilación de la app |
| 6.4.3 | El logo de la plantilla no puede volver | La compilación falla si `appicon.svg` contiene `512BD4` |

Queda pendiente, y fuera del alcance del instalador: **AVACOM Student** sigue
con los iconos de la plantilla de .NET MAUI. El instalador no lo distribuye.

---

## 7 · Firewall

El backend escucha en `0.0.0.0:8000` porque las tabletas llegan por la IP del
equipo maestro. Sin regla, Windows bloquea esas conexiones y el síntoma que ve
el aula («las tabletas no ven el curso») no se parece a la causa.

| Campo | Valor |
|---|---|
| Nombre | `AVACOM OPS Master Backend` |
| Protocolo y puerto | TCP 8000, entrante |
| Perfiles | `private`, `domain` |
| Programa | El `python.exe` del runtime instalado |

Se excluye el perfil público a propósito: esta API no tiene autenticación
(decisión Q-04 del prototipo) y el aula es una red privada.

---

## 8 · Distribución

El instalador ronda los 94 MB, contra un límite de 100 MB por archivo en un
push a GitHub, y cada versión añadiría otro tanto al historial. Se distribuye
como *release asset*; en el repositorio queda el código que lo reconstruye más
`installer/latest/SHA256.txt` para verificarlo.

| # | Regla | Cómo se comprueba |
|---|---|---|
| 8.1 | Lo empaquetado es la versión actual | `Build-Installer.ps1` publica desde el código fuente y falla si falta algo; el `manifiesto.json` instalado lleva la revisión de git |
| 8.2 | No se distribuyen versiones anteriores | El script borra los `.exe` previos de `installer/latest` antes de compilar |
| 8.3 | No se empaqueta un producto que no pasa sus pruebas | El paso 2 ejecuta la suite del backend y aborta si falla |
