# AVACOM LMS · clientes .NET MAUI

Prototipo nativo en C# para el aula AVACOM. La solución contiene dos aplicaciones:

- **AVACOM LMS OPS**: nodo principal Windows del profesor. Incluye diagnóstico de API, tablero, creación de curso y monitoreo de quiz.
- **AVACOM LMS Student**: nodo secundario Windows/Android. Incluye nombre y dirección del aula, menú hexagonal, curso navegable y quiz.

## Estructura

```text
src/
  Avacom.Lms.Core/       Dominio, demo, HTTP y WebSocket
  Avacom.Lms.Ui/         Controles MAUI compartidos
  Avacom.Lms.Ops/        Cliente profesor (Windows)
  Avacom.Lms.Student/    Cliente estudiante (Windows + Android)
tests/
  Avacom.Lms.Core.Tests/ Pruebas de contratos del núcleo
specs/
  001-maui-clients/      Especificación y criterios de aceptación
```

## Compilar

```powershell
dotnet restore Avacom.Lms.slnx
dotnet build src/Avacom.Lms.Ops/Avacom.Lms.Ops.csproj -f net10.0-windows10.0.19041.0
dotnet build src/Avacom.Lms.Student/Avacom.Lms.Student.csproj -f net10.0-windows10.0.19041.0
dotnet test tests/Avacom.Lms.Core.Tests/Avacom.Lms.Core.Tests.csproj
```

## Abrir las aplicaciones en Windows

`dotnet build` sólo compila. Para iniciar cada interfaz usa:

```powershell
dotnet run --project src/Avacom.Lms.Ops/Avacom.Lms.Ops.csproj -f net10.0-windows10.0.19041.0
dotnet run --project src/Avacom.Lms.Student/Avacom.Lms.Student.csproj -f net10.0-windows10.0.19041.0
```

También puedes abrir directamente los ejecutables después de compilar:

```powershell
& '.\src\Avacom.Lms.Ops\bin\Debug\net10.0-windows10.0.19041.0\win-x64\Avacom.Lms.Ops.exe'
& '.\src\Avacom.Lms.Student\bin\Debug\net10.0-windows10.0.19041.0\win-x64\Avacom.Lms.Student.exe'
```

Para Android, con un emulador o dispositivo configurado:

```powershell
dotnet build src/Avacom.Lms.Student/Avacom.Lms.Student.csproj -f net10.0-android
```

Ambas apps ofrecen modo demo si el backend no está disponible. El servidor esperado es DRF/ASGI en `0.0.0.0:8000`; el cliente consulta `/health/` y el núcleo incluye el cliente para `/ws/activities/{activity_id}/`.

## Correr tu proyecto

```powershell
dotnet run --project src/Avacom.Lms.Ops/Avacom.Lms.Ops.csproj -f net10.0-windows10.0.19041.0
dotnet run --project src/Avacom.Lms.Student/Avacom.Lms.Student.csproj -f net10.0-windows10.0.19041.0
```

## Construye el proyecto

```powershell
dotnet restore Avacom.Lms.slnx
dotnet build src/Avacom.Lms.Ops/Avacom.Lms.Ops.csproj -f net10.0-windows10.0.19041.0 -c Release
dotnet build src/Avacom.Lms.Student/Avacom.Lms.Student.csproj -f net10.0-windows10.0.19041.0 -c Release
```

Los ejecutables quedan en:

```powershell
.\src\Avacom.Lms.Ops\bin\Release\net10.0-windows10.0.19041.0\win-x64\Avacom.Lms.Ops.exe
.\src\Avacom.Lms.Student\bin\Release\net10.0-windows10.0.19041.0\win-x64\Avacom.Lms.Student.exe
```
