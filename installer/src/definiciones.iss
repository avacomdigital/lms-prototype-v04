; Valores compartidos por el instalador (AvacomOpsMaster.iss) y por el arnes
; de diagnostico (build\PruebaAsistente.iss). Se definen una sola vez para que
; el arnes no pueda comprobar un puerto o un servicio distinto del que se
; instala de verdad.

#define NombreProducto      "AVACOM OPS Master"
#define NombreCorto         "OPS Master"
#define Fabricante          "AVACOM"
#ifndef VersionProducto
  #define VersionProducto   "2.0.0"
#endif
#define UrlProducto         "https://github.com/avacomdigital/lms-prototype-v04"
#define NombreServicio      "AVACOMOPSBackend"
#define PuertoBackend       "8000"
#define EjecutableApp       "Avacom.Lms.Ops.exe"
#define EjecutableHost      "Avacom.Ops.Host.exe"

; Carpeta preparada por Build-Installer.ps1. Se puede sobrescribir con
; ISCC /DCarpetaContenido=...
#ifndef CarpetaContenido
  #define CarpetaContenido "..\..\dist\staging"
#endif
#ifndef CarpetaSalida
  #define CarpetaSalida "..\latest"
#endif
#ifndef Revision
  #define Revision "sin-revision"
#endif

