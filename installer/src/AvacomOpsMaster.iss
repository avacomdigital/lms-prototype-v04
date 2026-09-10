; ============================================================================
;  Instalador de AVACOM OPS Master (aplicacion + backend Django REST Framework)
;
;  Se compila con installer\build\Build-Installer.ps1, que antes deja el
;  contenido a instalar en dist\staging. No compiles este archivo a mano: el
;  script de compilacion es el que garantiza que lo que se empaqueta es la
;  version actual del producto y no una copia vieja.
;
;  Tres cosas que este instalador NO hace, a proposito:
;
;    * No cambia el comportamiento del producto. Configura lo que el backend
;      ya sabe leer (variables de entorno) y no toca su codigo.
;    * No toca AVACOM Biblioteca. Otro AppId, otra carpeta, otro servicio,
;      otra base de datos, otros logs, otro grupo del menu inicio. De la
;      biblioteca solo se LEE la nota de enlace, y eso lo hace el backend.
;    * No pide escribir nada. El equipo principal del aula es tactil y no
;      tiene teclado: todo el asistente se maneja con toques.
; ============================================================================

#include "definiciones.iss"

[Setup]
; Este AppId identifica a AVACOM OPS Master y a nada mas. AVACOM Biblioteca
; tiene el suyo: por eso aparecen como dos productos independientes en
; "Aplicaciones instaladas" y desinstalar uno no afecta al otro.
AppId={{B6D1F0A4-3C57-4E2B-9A18-7F5C2E8D4A31}
AppName={#NombreProducto}
AppVersion={#VersionProducto}
AppVerName={#NombreProducto} {#VersionProducto}
AppPublisher={#Fabricante}
AppPublisherURL={#UrlProducto}
AppSupportURL={#UrlProducto}
AppUpdatesURL={#UrlProducto}
VersionInfoVersion={#VersionProducto}
VersionInfoDescription=Instalador de {#NombreProducto}
VersionInfoCompany={#Fabricante}
VersionInfoTextVersion={#VersionProducto} ({#Revision})

; Carpeta propia bajo AVACOM. La biblioteca usa AVACOM\Biblioteca.
DefaultDirName={autopf}\AVACOM\{#NombreCorto}
; Grupo propio en el menu inicio: no se comparte ni se sobrescribe ningun
; acceso directo de la biblioteca.
DefaultGroupName={#NombreProducto}
DisableProgramGroupPage=yes
UninstallDisplayName={#NombreProducto}
UninstallDisplayIcon={app}\App\{#EjecutableApp}

; El servicio, la regla de firewall y la carpeta de Program Files necesitan
; permisos de administrador. Es un unico consentimiento al principio.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=

ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0

OutputDir={#CarpetaSalida}
OutputBaseFilename=AVACOM-OPS-Master-Setup-{#VersionProducto}
; Icono del propio archivo del instalador. Se usa el que compone
; New-ImagenesAsistente.ps1 y no el appicon.ico de MAUI, porque ese trae un
; solo tamano de 64 px y Windows lo escalaria borroso justo en el archivo
; que el usuario toca para instalar.
SetupIconFile={#CarpetaContenido}\Asistente\instalador.ico

; Pantalla 2 del asistente: la informacion de AVACOM LMS 2.0.
InfoBeforeFile=informacion.txt

; Marca del asistente. Sin estas dos directivas, Inno Setup pone sus propias
; ilustraciones: la grande en Bienvenido y en Instalacion completada, y la
; pequena arriba a la derecha en TODAS las demas pantallas. Es decir, un logo
; ajeno repetido pantalla a pantalla.
;
; Las genera New-ImagenesAsistente.ps1 desde el mismo simbolo que usa la
; aplicacion (assets/avacom-symbol.svg). Dos tamanos por imagen: Inno escoge
; segun el DPI, que en una pantalla tactil de aula no suele ser 96.
WizardImageFile={#CarpetaContenido}\Asistente\banner.png,{#CarpetaContenido}\Asistente\banner-2x.png
WizardSmallImageFile={#CarpetaContenido}\Asistente\simbolo.png,{#CarpetaContenido}\Asistente\simbolo-2x.png
Compression=lzma2/max
SolidCompression=yes
LZMANumBlockThreads=4

; --- Asistente pensado para una pantalla tactil sin teclado ---
WizardStyle=modern
; Ventana grande: los objetivos de toque necesitan sitio.
WizardSizePercent=150
ShowLanguageDialog=no
AllowNoIcons=no
DisableWelcomePage=no
DisableReadyMemo=no
; Si algun archivo esta en uso, se avisa en lugar de reiniciar sin permiso.
RestartIfNeededByRun=no
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll
SetupLogging=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
es.WelcomeLabel1=Bienvenido a la instalación de [name]
es.WelcomeLabel2=Este asistente instalará [name/ver] en este equipo.%n%nToca Siguiente para continuar.
es.WizardInfoBefore=Información de AVACOM LMS 2.0
es.InfoBeforeLabel=Lee esta información antes de continuar.
es.InfoBeforeClickLabel=Cuando estés listo, toca Siguiente.
es.WizardSelectDir=Carpeta de instalación
es.SelectDirDesc=¿Dónde se debe instalar [name]?
es.SelectDirLabel3=La instalación colocará [name] en la carpeta siguiente. AVACOM Biblioteca, si está en este equipo, usa una carpeta distinta y no se modifica.
es.SelectDirBrowseLabel=Para continuar, toca Siguiente. Para elegir otra carpeta, toca Examinar.
es.FinishedHeadingLabel=Instalación completada
es.FinishedLabelNoIcons={#NombreProducto} quedó instalado en este equipo.
es.FinishedLabel={#NombreProducto} quedó instalado en este equipo. El servicio de la API local arranca solo con Windows.
es.ExitSetupTitle=Salir de la instalación
es.ExitSetupMessage=La instalación no se ha terminado. Si sales ahora, {#NombreProducto} no quedará instalado.%n%n¿Salir de la instalación?

[CustomMessages]
es.TareaIconoEscritorio=Crear un icono grande en el escritorio
es.EjecutarAhora=Abrir {#NombreProducto} ahora
es.GrupoAccesos=Accesos directos

[Tasks]
Name: "iconoescritorio"; Description: "{cm:TareaIconoEscritorio}"; GroupDescription: "{cm:GrupoAccesos}"

[Dirs]
; --------------------------------------------------------------------------
; Estado del nodo. Vive FUERA de Program Files por dos razones:
;   1. Program Files es de solo lectura para el usuario que da la clase.
;   2. El expediente del estudiante es el unico dato que no se puede volver a
;      generar, asi que no puede depender de la carpeta del programa.
;
; La carpeta padre %ProgramData%\AVACOM la comparten los dos productos (la
; biblioteca guarda ahi su nota de enlace), por eso ni ella ni las nuestras se
; borran al desinstalar: solo se borra lo que este instalador creo, y el
; expediente se borra unicamente si se pide expresamente.
; --------------------------------------------------------------------------
Name: "{commonappdata}\AVACOM"; Flags: uninsneveruninstall
Name: "{commonappdata}\AVACOM\{#NombreCorto}"; Flags: uninsneveruninstall
Name: "{commonappdata}\AVACOM\{#NombreCorto}\Config"; Flags: uninsneveruninstall
Name: "{commonappdata}\AVACOM\{#NombreCorto}\Data"; Flags: uninsneveruninstall
; El lanzador escribe su diagnostico como el usuario del aula, no como
; administrador: necesita poder escribir aqui.
Name: "{commonappdata}\AVACOM\{#NombreCorto}\Logs"; Permissions: users-modify; Flags: uninsneveruninstall

[Files]
; Interfaz .NET MAUI, con el runtime de .NET y el Windows App SDK dentro: el
; equipo del aula no instala prerrequisitos ni necesita internet.
Source: "{#CarpetaContenido}\App\*"; DestDir: "{app}\App"; Flags: ignoreversion recursesubdirs createallsubdirs

; Backend Django REST Framework, tal cual esta en el repositorio.
Source: "{#CarpetaContenido}\Backend\*"; DestDir: "{app}\Backend"; Flags: ignoreversion recursesubdirs createallsubdirs

; Runtime: Python embebido con Django, DRF y Waitress ya instalados, el
; arranque de Waitress y el host del servicio.
Source: "{#CarpetaContenido}\Runtime\*"; DestDir: "{app}\Runtime"; Flags: ignoreversion recursesubdirs createallsubdirs

; Que se empaqueto y desde que revision.
Source: "{#CarpetaContenido}\manifiesto.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#CarpetaContenido}\LEEME.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; El icono abre el lanzador, no la aplicacion: primero se asegura el backend,
; se valida y despues se abre la interfaz.
Name: "{group}\{#NombreProducto}"; Filename: "{app}\Runtime\{#EjecutableHost}"; Parameters: "iniciar"; WorkingDir: "{app}"; IconFilename: "{app}\App\{#EjecutableApp}"; IconIndex: 0; Comment: "Abre {#NombreProducto} y su API local"
Name: "{group}\Desinstalar {#NombreProducto}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#NombreProducto}"; Filename: "{app}\Runtime\{#EjecutableHost}"; Parameters: "iniciar"; WorkingDir: "{app}"; IconFilename: "{app}\App\{#EjecutableApp}"; IconIndex: 0; Tasks: iconoescritorio

[Run]
; Casilla en la ultima pantalla: un toque y se abre.
;
; runasoriginaluser importa: sin esa marca la aplicacion heredaria el token de
; administrador del instalador, se ejecutaria elevada el resto de la sesion y
; lo que escribiera quedaria a nombre del administrador. Debe correr como quien
; da la clase, que es justo el permiso que se le concedio sobre el servicio.
Filename: "{app}\Runtime\{#EjecutableHost}"; Parameters: "iniciar"; Description: "{cm:EjecutarAhora}"; Flags: postinstall nowait skipifsilent runasoriginaluser

[UninstallRun]
; Antes de borrar archivos: parar el servicio (que usa el propio host), quitarlo
; del sistema y retirar la regla de firewall. Solo lo nuestro.
Filename: "{app}\Runtime\{#EjecutableHost}"; Parameters: "detener-servicio"; Flags: runhidden waituntilterminated; RunOnceId: "DetenerServicioOps"
Filename: "{app}\Runtime\{#EjecutableHost}"; Parameters: "quitar-servicio"; Flags: runhidden waituntilterminated; RunOnceId: "QuitarServicioOps"
Filename: "{app}\Runtime\{#EjecutableHost}"; Parameters: "cerrar-firewall"; Flags: runhidden waituntilterminated; RunOnceId: "CerrarFirewallOps"

[UninstallDelete]
; Los __pycache__ los crea Python al ejecutar, no el instalador.
Type: filesandordirs; Name: "{app}\Backend"
Type: filesandordirs; Name: "{app}\Runtime\Python\Lib\site-packages"
Type: dirifempty; Name: "{app}"

; ============================================================================
[Code]
#include "codigo.iss"
