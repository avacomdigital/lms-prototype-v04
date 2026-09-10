// Logica del asistente de AVACOM OPS Master.
//
// Vive en su propio archivo para que build\PruebaAsistente.iss pueda
// ejecutarla tal cual, sin instalar nada, y comprobar que las nueve
// comprobaciones del equipo funcionan de verdad en un Windows real.
//
// Se incluye desde la seccion [Code]; aqui no va ninguna cabecera de seccion.


const
  PuertoApi = {#PuertoBackend};
  ClaveDesinstalar =
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{B6D1F0A4-3C57-4E2B-9A18-7F5C2E8D4A31}_is1';

var
  PaginaValidacion: TWizardPage;
  EtiquetaCheck: array[0..8] of TNewStaticText;
  ResumenValidacion: TNewStaticText;
  BotonRevalidar: TNewButton;
  BotonRutaRecomendada: TNewButton;
  ValidacionSuperada: Boolean;
  AvisoConfiguracion: String;

{ ------------------------------------------------------------------ Utiles }

function EjecutarYLeer(const Orden: String): String;
var
  Temporal: String;
  Codigo: Integer;
  Contenido: AnsiString;
begin
  Result := '';
  Temporal := ExpandConstant('{tmp}\avacom-salida.txt');
  if Exec(ExpandConstant('{cmd}'), '/C ' + Orden + ' > "' + Temporal + '" 2>&1',
          '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
  begin
    if LoadStringFromFile(Temporal, Contenido) then
      Result := String(Contenido);
    DeleteFile(Temporal);
  end;
end;

{ Devuelve la linea completa de netstat que escucha en el puerto, o ''.
  Se mira la columna de direccion local en lugar de la palabra LISTENING,
  porque netstat traduce esa palabra segun el idioma de Windows. }
function QuienEscuchaEnPuerto(Puerto: Integer): String;
var
  Salida: String;
  Lineas: TArrayOfString;
  Linea, Local, Sufijo: String;
  i, Corte: Integer;
begin
  Result := '';
  Sufijo := ':' + IntToStr(Puerto);
  Salida := EjecutarYLeer('netstat -ano -p tcp');
  if Salida = '' then Exit;

  Lineas := StringSplitEx(Salida, [#10], #0, stExcludeEmpty);
  for i := 0 to GetArrayLength(Lineas) - 1 do
  begin
    Linea := Trim(Lineas[i]);
    if Copy(Linea, 1, 4) <> 'TCP ' then Continue;

    { Tras "TCP" viene la direccion local, y despues el resto de columnas. }
    Linea := Trim(Copy(Linea, 5, Length(Linea)));
    Corte := Pos(' ', Linea);
    if Corte = 0 then Continue;

    Local := Copy(Linea, 1, Corte - 1);
    if Length(Local) < Length(Sufijo) then Continue;

    { Se compara el final de la direccion local: asi cuentan 0.0.0.0:8000 y
      127.0.0.1:8000, y no cuenta una conexion saliente hacia el :8000 de otro
      equipo, que aparece en la columna remota. }
    if Copy(Local, Length(Local) - Length(Sufijo) + 1, Length(Sufijo)) = Sufijo then
    begin
      Result := Trim(Lineas[i]);
      Exit;
    end;
  end;
end;

{ ¿Lo que contesta en el puerto es un backend de AVACOM OPS? Distinguirlo
  evita tratar una reinstalacion como un conflicto con otro programa. }
function RespondeNuestroBackend(Puerto: Integer): Boolean;
var
  Peticion: Variant;
  Estado: Integer;
  Cuerpo: String;
begin
  Result := False;
  try
    Peticion := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Peticion.SetTimeouts(2000, 2000, 2000, 4000);
    Peticion.Open('GET', 'http://127.0.0.1:' + IntToStr(Puerto) + '/health/', False);
    Peticion.Send('');
    { Las propiedades del objeto COM llegan como Variant: hay que convertirlas
      antes de pasarlas a Pos, que espera String. }
    Estado := Integer(Peticion.Status);
    Cuerpo := String(Peticion.ResponseText);
    Result := (Estado = 200) and (Pos('avacom-lms-backend', Cuerpo) > 0);
  except
    Result := False;
  end;
end;

function ProcesoActivo(const Imagen: String): Boolean;
var
  Salida: String;
begin
  Salida := EjecutarYLeer('tasklist /FI "IMAGENAME eq ' + Imagen + '" /NH');
  Result := Pos(LowerCase(Imagen), LowerCase(Salida)) > 0;
end;

function ServicioRegistrado(const Nombre: String): Boolean;
var
  Codigo: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\sc.exe'), 'query "' + Nombre + '"',
                 '', SW_HIDE, ewWaitUntilTerminated, Codigo) and (Codigo = 0);
end;

function BibliotecaPresente: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonappdata}\AVACOM\contenido\enlace.json'))
         or DirExists(ExpandConstant('{autopf}\AVACOM\Biblioteca'))
         or ServicioRegistrado('AVACOMBiblioteca');
end;

function VersionInstalada: String;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE, ClaveDesinstalar, 'DisplayVersion', Result) then
    Result := '';
end;

{ ----------------------------------------------- Asistente para pantalla tactil }

procedure AgrandarBoton(Boton: TNewButton; AnchoNuevo, AltoNuevo: Integer);
begin
  if Boton = nil then Exit;
  { Se mantiene fijo el borde inferior derecho y el boton crece hacia
    arriba y hacia la izquierda: asi no se sale de la ventana. }
  Boton.Left := Boton.Left - (AnchoNuevo - Boton.Width);
  Boton.Top := Boton.Top - (AltoNuevo - Boton.Height);
  Boton.Width := AnchoNuevo;
  Boton.Height := AltoNuevo;
  Boton.Font.Size := 11;
end;

procedure AjustarParaPantallaTactil;
var
  Ancho, Alto, Delta: Integer;
begin
  Ancho := ScaleX(150);
  Alto := ScaleY(46);
  Delta := Alto - WizardForm.NextButton.Height;

  { Los botones crecen hacia arriba; se le quita ese alto al area de las
    paginas para que no queden encima del contenido. }
  if Delta > 0 then
  begin
    WizardForm.Bevel.Top := WizardForm.Bevel.Top - Delta;
    WizardForm.OuterNotebook.Height := WizardForm.OuterNotebook.Height - Delta;
  end;

  AgrandarBoton(WizardForm.NextButton, Ancho, Alto);
  AgrandarBoton(WizardForm.BackButton, Ancho, Alto);
  AgrandarBoton(WizardForm.CancelButton, Ancho, Alto);
  AgrandarBoton(WizardForm.DirBrowseButton, ScaleX(150), ScaleY(38));

  { Casillas y textos que hay que poder tocar sin precision de raton. }
  WizardForm.TasksList.Font.Size := 11;
  WizardForm.TasksList.MinItemHeight := ScaleY(34);
  WizardForm.RunList.Font.Size := 11;
  WizardForm.RunList.MinItemHeight := ScaleY(34);
  WizardForm.InfoBeforeMemo.Font.Size := 10;
  WizardForm.ReadyMemo.Font.Size := 10;

  { Sin teclado no se puede escribir una ruta: la caja se vuelve de solo
    lectura y la carpeta se elige con Examinar o con el boton de al lado. }
  WizardForm.DirEdit.ReadOnly := True;
  WizardForm.DirEdit.Font.Size := 11;
  WizardForm.DirEdit.Height := ScaleY(32);
end;

procedure UsarRutaRecomendadaClick(Sender: TObject);
begin
  WizardForm.DirEdit.Text := ExpandConstant('{autopf}\AVACOM\{#NombreCorto}');
end;

procedure CrearBotonRutaRecomendada;
begin
  BotonRutaRecomendada := TNewButton.Create(WizardForm);
  BotonRutaRecomendada.Parent := WizardForm.SelectDirPage;
  BotonRutaRecomendada.Left := WizardForm.DirEdit.Left;
  BotonRutaRecomendada.Top := WizardForm.DirEdit.Top + WizardForm.DirEdit.Height + ScaleY(14);
  BotonRutaRecomendada.Width := ScaleX(330);
  BotonRutaRecomendada.Height := ScaleY(42);
  BotonRutaRecomendada.Font.Size := 11;
  BotonRutaRecomendada.Caption := 'Usar la carpeta recomendada';
  BotonRutaRecomendada.OnClick := @UsarRutaRecomendadaClick;
end;

{ --------------------------------------------------- Pantalla de validaciones }

procedure PonerCheck(Indice: Integer; Correcto, Bloqueante: Boolean; const Texto: String);
begin
  if Correcto then
  begin
    EtiquetaCheck[Indice].Caption := '✓   ' + Texto;
    EtiquetaCheck[Indice].Font.Color := clGreen;
  end
  else if Bloqueante then
  begin
    EtiquetaCheck[Indice].Caption := '✗   ' + Texto;
    EtiquetaCheck[Indice].Font.Color := clRed;
  end
  else
  begin
    EtiquetaCheck[Indice].Caption := '⚠   ' + Texto;
    EtiquetaCheck[Indice].Font.Color := clOlive;
  end;
end;

procedure EjecutarValidaciones;
var
  Version: TWindowsVersion;
  Libres, Total: Int64;
  Bloqueo: String;
  Anterior, Ocupante: String;
  RequeridoMb: Integer;
begin
  Bloqueo := '';
  RequeridoMb := 1200;

  { 1. Version de Windows }
  GetWindowsVersionEx(Version);
  if (Version.Major > 10) or ((Version.Major = 10) and (Version.Build >= 10240)) then
  begin
    if Version.Build >= 22000 then
      PonerCheck(0, True, True, 'Windows 11 (compilación ' + IntToStr(Version.Build) + ')')
    else
      PonerCheck(0, True, True, 'Windows 10 (compilación ' + IntToStr(Version.Build) + ')');
  end
  else
  begin
    PonerCheck(0, False, True, 'Se necesita Windows 10 o Windows 11');
    Bloqueo := 'Este equipo no tiene una versión de Windows compatible.';
  end;

  { 2. Arquitectura }
  if IsX64OS then
    PonerCheck(1, True, True, 'Procesador de 64 bits compatible')
  else
  begin
    PonerCheck(1, False, True, 'Se necesita Windows de 64 bits (x64)');
    if Bloqueo = '' then Bloqueo := 'La arquitectura de este equipo no es compatible.';
  end;

  { 3. Espacio en disco }
  if GetSpaceOnDisk64(ExtractFileDrive(WizardDirValue), Libres, Total) then
  begin
    if Libres >= Int64(RequeridoMb) * 1048576 then
      PonerCheck(2, True, True, 'Espacio disponible: ' + IntToStr(Libres div 1048576) + ' MB')
    else
    begin
      PonerCheck(2, False, True, 'Espacio insuficiente: hay ' + IntToStr(Libres div 1048576) +
                                 ' MB y se necesitan ' + IntToStr(RequeridoMb) + ' MB');
      if Bloqueo = '' then Bloqueo := 'Libera espacio en el disco y vuelve a comprobar.';
    end;
  end
  else
    PonerCheck(2, False, False, 'No se pudo medir el espacio libre del disco');

  { 4. Permisos }
  if IsAdmin then
    PonerCheck(3, True, True, 'Permisos de administrador concedidos')
  else
  begin
    PonerCheck(3, False, True, 'Se necesitan permisos de administrador');
    if Bloqueo = '' then Bloqueo := 'Vuelve a abrir la instalación como administrador.';
  end;

  { 5. Puerto de la API local }
  Ocupante := QuienEscuchaEnPuerto(PuertoApi);
  if Ocupante = '' then
    PonerCheck(4, True, True, 'Puerto ' + IntToStr(PuertoApi) + ' libre para la API local')
  else if RespondeNuestroBackend(PuertoApi) then
    PonerCheck(4, True, False, 'Puerto ' + IntToStr(PuertoApi) +
                               ' en uso por un backend de AVACOM OPS ya instalado; se reemplazará')
  else
  begin
    PonerCheck(4, False, True, 'Puerto ' + IntToStr(PuertoApi) + ' ocupado por otro programa');
    if Bloqueo = '' then
      Bloqueo := 'El puerto ' + IntToStr(PuertoApi) + ' lo está usando otra aplicación.' + #13#10#13#10 +
                 'AVACOM OPS Master necesita ese puerto para su API local.' + #13#10#13#10 +
                 'Cierra la aplicación que lo ocupa y toca «Volver a comprobar». ' +
                 'La instalación no va a detener programas ajenos por su cuenta.';
  end;

  { 6. Instalacion previa }
  Anterior := VersionInstalada;
  if Anterior = '' then
    PonerCheck(5, True, True, 'Primera instalación de AVACOM OPS Master en este equipo')
  else
    PonerCheck(5, True, False, 'Ya está instalada la versión ' + Anterior +
                               '; se actualizará conservando el expediente');

  { 7. Procesos activos }
  if ProcesoActivo('{#EjecutableApp}') then
  begin
    PonerCheck(6, False, True, 'AVACOM OPS Master está abierto en este equipo');
    if Bloqueo = '' then
      Bloqueo := 'Cierra AVACOM OPS Master y toca «Volver a comprobar».';
  end
  else
    PonerCheck(6, True, True, 'Ninguna ventana de AVACOM OPS Master está abierta');

  { 8. Dependencias criticas: van dentro del paquete, no se instalan aparte }
  if FileExists(ExpandConstant('{sys}\sc.exe')) and FileExists(ExpandConstant('{sys}\netsh.exe')) then
    PonerCheck(7, True, True, 'Dependencias del backend incluidas en el paquete (no requiere internet)')
  else
    PonerCheck(7, False, False, 'No se encontraron herramientas del sistema para registrar el servicio');

  { 9. Convivencia con AVACOM Biblioteca }
  if BibliotecaPresente then
    PonerCheck(8, True, True, 'AVACOM Biblioteca detectada: se instalará junto a ella sin modificarla')
  else
    PonerCheck(8, True, False, 'AVACOM Biblioteca no está en este equipo; los cursos no se verán hasta instalarla');

  ValidacionSuperada := (Bloqueo = '');
  if ValidacionSuperada then
  begin
    ResumenValidacion.Caption := 'Todo listo. Toca Siguiente para continuar.';
    ResumenValidacion.Font.Color := clGreen;
  end
  else
  begin
    ResumenValidacion.Caption := Bloqueo;
    ResumenValidacion.Font.Color := clRed;
  end;

  WizardForm.NextButton.Enabled := ValidacionSuperada;
end;

procedure RevalidarClick(Sender: TObject);
begin
  EjecutarValidaciones;
end;

procedure CrearPaginaValidacion;
var
  Titulo: TNewStaticText;
  i, y: Integer;
begin
  PaginaValidacion := CreateCustomPage(wpSelectDir,
    'Comprobación del equipo',
    'Antes de instalar nada, se revisa que este equipo pueda ejecutar AVACOM OPS Master.');

  Titulo := TNewStaticText.Create(PaginaValidacion);
  Titulo.Parent := PaginaValidacion.Surface;
  Titulo.Left := 0;
  Titulo.Top := 0;
  Titulo.Width := PaginaValidacion.SurfaceWidth;
  Titulo.AutoSize := False;
  Titulo.Height := ScaleY(20);
  Titulo.Font.Size := 10;
  Titulo.Caption := 'Resultado de la comprobación:';

  y := ScaleY(30);
  for i := 0 to 8 do
  begin
    EtiquetaCheck[i] := TNewStaticText.Create(PaginaValidacion);
    EtiquetaCheck[i].Parent := PaginaValidacion.Surface;
    EtiquetaCheck[i].Left := 0;
    EtiquetaCheck[i].Top := y;
    EtiquetaCheck[i].Width := PaginaValidacion.SurfaceWidth;
    EtiquetaCheck[i].AutoSize := False;
    EtiquetaCheck[i].Height := ScaleY(24);
    EtiquetaCheck[i].Font.Size := 10;
    EtiquetaCheck[i].Caption := '';
    y := y + ScaleY(26);
  end;

  ResumenValidacion := TNewStaticText.Create(PaginaValidacion);
  ResumenValidacion.Parent := PaginaValidacion.Surface;
  ResumenValidacion.Left := 0;
  ResumenValidacion.Top := y + ScaleY(14);
  ResumenValidacion.Width := PaginaValidacion.SurfaceWidth;
  ResumenValidacion.AutoSize := False;
  ResumenValidacion.Height := ScaleY(86);
  ResumenValidacion.WordWrap := True;
  ResumenValidacion.Font.Size := 10;
  ResumenValidacion.Font.Style := [fsBold];
  ResumenValidacion.Caption := '';

  BotonRevalidar := TNewButton.Create(PaginaValidacion);
  BotonRevalidar.Parent := PaginaValidacion.Surface;
  BotonRevalidar.Left := 0;
  BotonRevalidar.Top := ResumenValidacion.Top + ResumenValidacion.Height + ScaleY(8);
  BotonRevalidar.Width := ScaleX(240);
  BotonRevalidar.Height := ScaleY(44);
  BotonRevalidar.Font.Size := 11;
  BotonRevalidar.Caption := 'Volver a comprobar';
  BotonRevalidar.OnClick := @RevalidarClick;
end;

{ ------------------------------------------------------------ Ciclo de vida }

{ ------------------------------------------------------------- Diagnostico }

{ Con /VOLCADO=<archivo> el asistente ejecuta sus comprobaciones, las escribe
  en ese archivo y NO instala nada. Sirve para dos cosas:

    * que soporte pueda saber si un equipo del aula esta listo sin tocarlo;
    * que la compilacion pueda probar esta logica en un Windows de verdad
      (installeruild\PruebaAsistente.iss).

  Combinalo con /VERYSILENT para que no aparezca ninguna ventana. }
function RutaVolcado: String;
var
  i: Integer;
  Parametro: String;
begin
  Result := '';
  for i := 1 to ParamCount do
  begin
    Parametro := ParamStr(i);
    if CompareText(Copy(Parametro, 1, 9), '/VOLCADO=') = 0 then
    begin
      Result := Copy(Parametro, 10, Length(Parametro));
      Exit;
    end;
  end;
end;

procedure VolcarDiagnostico(const Archivo: String);
var
  Lineas: TArrayOfString;
  i: Integer;
begin
  EjecutarValidaciones;

  SetArrayLength(Lineas, 12);
  Lineas[0] := 'Diagnostico de AVACOM OPS Master ' + '{#VersionProducto}';
  Lineas[1] := 'Carpeta prevista: ' + WizardDirValue;
  for i := 0 to 8 do
    { El prefijo es ASCII a proposito: quien lea este archivo no deberia
      depender de acertar con la codificacion de una marca de verificacion. }
    Lineas[2 + i] := 'check: ' + EtiquetaCheck[i].Caption;
  Lineas[11] := 'Resultado: ' + ResumenValidacion.Caption;

  SaveStringsToUTF8File(Archivo, Lineas, False);
end;

procedure InitializeWizard;
begin
  AjustarParaPantallaTactil;
  CrearBotonRutaRecomendada;
  CrearPaginaValidacion;

  if RutaVolcado <> '' then
    VolcarDiagnostico(RutaVolcado);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (PaginaValidacion <> nil) and (CurPageID = PaginaValidacion.ID) then
    EjecutarValidaciones
  else
    WizardForm.NextButton.Enabled := True;

  { Si la configuracion del backend no salio, se dice en la propia pantalla
    final: dejar un producto instalado que no funciona sin explicacion es
    peor que cualquier mensaje. }
  if (CurPageID = wpFinished) and (AvisoConfiguracion <> '') then
  begin
    WizardForm.FinishedLabel.Caption :=
      'AVACOM OPS Master quedó instalado, pero la configuración de la API local no terminó:'
      + #13#10 + #13#10 + AvisoConfiguracion
      + #13#10 + #13#10 + 'El detalle está en la carpeta de registros del producto.';
    WizardForm.FinishedLabel.Font.Color := clMaroon;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (PaginaValidacion <> nil) and (CurPageID = PaginaValidacion.ID) then
    Result := ValidacionSuperada;
end;

function UpdateReadyMemo(const Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result :=
    'Se va a instalar en este equipo:' + NewLine +
    Space + 'AVACOM OPS Master (interfaz del profesor)' + NewLine +
    Space + 'AVACOM OPS Backend (API local del aula, puerto ' + IntToStr(PuertoApi) + ')' + NewLine +
    NewLine +
    MemoDirInfo + NewLine + NewLine +
    'Configuración que hará el asistente, sin intervención:' + NewLine +
    Space + 'Configuración local del nodo y base de datos del expediente' + NewLine +
    Space + 'Servicio de Windows «{#NombreServicio}», con inicio automático' + NewLine +
    Space + 'Regla de Windows Defender Firewall para TCP ' + IntToStr(PuertoApi) +
            ' en redes privadas' + NewLine +
    NewLine;

  if MemoTasksInfo <> '' then
    Result := Result + MemoTasksInfo + NewLine + NewLine;

  Result := Result +
    'No se modificará AVACOM Biblioteca ni ningún dato suyo.';
end;

{ Antes de copiar archivos: si ya habia una instalacion, su servicio tiene
  abiertos los archivos que vamos a reemplazar. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Codigo: Integer;
begin
  Result := '';
  NeedsRestart := False;

  { El modo diagnostico no instala: solo informa. }
  if RutaVolcado <> '' then
  begin
    Result := 'Modo diagnostico: las comprobaciones se escribieron en ' + RutaVolcado +
              ' y no se instalo nada.';
    Exit;
  end;

  if ServicioRegistrado('{#NombreServicio}') then
  begin
    Exec(ExpandConstant('{sys}\sc.exe'), 'stop "{#NombreServicio}"', '', SW_HIDE,
         ewWaitUntilTerminated, Codigo);
    { El SCM tarda en soltar el ejecutable del servicio. }
    Sleep(4000);
  end;
end;

{ La pantalla "Backend Configuration": lo que el README del backend pide a
  mano, hecho aqui sin que nadie escriba un comando. }
procedure ConfigurarBackend;
var
  Pagina: TOutputProgressWizardPage;
  Host, Estado: String;
  Codigo: Integer;
  Contenido: AnsiString;
begin
  Host := ExpandConstant('{app}\Runtime\{#EjecutableHost}');
  AvisoConfiguracion := '';

  Pagina := CreateOutputProgressPage('Configuración del backend',
    'Se está preparando la API local de AVACOM OPS Master. No hace falta hacer nada.');
  Pagina.SetProgress(0, 100);
  Pagina.Show;
  try
    Pagina.SetText('Creando la configuración de este equipo y la base de datos del expediente...', '');
    Pagina.SetProgress(10, 100);
    if not Exec(Host, 'preparar', '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
      Codigo := -1;
    if Codigo <> 0 then
    begin
      Estado := '';
      if LoadStringFromFile(ExpandConstant('{commonappdata}\AVACOM\{#NombreCorto}\Logs\preparacion-estado.txt'), Contenido) then
        Estado := Trim(String(Contenido));
      if Estado = '' then
        Estado := 'La preparación del backend terminó con el código ' + IntToStr(Codigo) + '.';
      AvisoConfiguracion := Estado;
      Exit;
    end;
    Pagina.SetProgress(40, 100);

    Pagina.SetText('Registrando el servicio de la API local...', '');
    if not Exec(Host, 'instalar-servicio', '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
      Codigo := -1;
    if Codigo <> 0 then
    begin
      AvisoConfiguracion := 'No se pudo registrar el servicio {#NombreServicio}.';
      Exit;
    end;
    Pagina.SetProgress(60, 100);

    Pagina.SetText('Autorizando el puerto ' + IntToStr(PuertoApi) +
                   ' para las tabletas del aula...', '');
    Exec(Host, 'abrir-firewall', '', SW_HIDE, ewWaitUntilTerminated, Codigo);
    Pagina.SetProgress(75, 100);

    Pagina.SetText('Iniciando la API local...', '');
    if not Exec(Host, 'iniciar-servicio', '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
      Codigo := -1;
    if Codigo <> 0 then
    begin
      AvisoConfiguracion := 'El servicio {#NombreServicio} quedó instalado pero no arrancó. ' +
                            'Se iniciará al reiniciar el equipo.';
      Exit;
    end;
    Pagina.SetProgress(85, 100);

    Pagina.SetText('Comprobando que la API local responde...', '');
    if not Exec(Host, 'salud 90', '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
      Codigo := -1;
    if Codigo <> 0 then
      AvisoConfiguracion := 'La API local no respondió durante la instalación. ' +
                            'Revisa la carpeta de registros de AVACOM OPS Master.';
    Pagina.SetProgress(100, 100);
  finally
    Pagina.Hide;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    ConfigurarBackend;
end;

{ ------------------------------------------------------------ Desinstalacion }

function InitializeUninstall: Boolean;
begin
  Result := True;
  if ProcesoActivo('{#EjecutableApp}') then
  begin
    MsgBox('Cierra AVACOM OPS Master antes de desinstalarlo.', mbInformation, MB_OK);
    Result := False;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Estado: String;
begin
  if CurUninstallStep <> usPostUninstall then Exit;

  Estado := ExpandConstant('{commonappdata}\AVACOM\{#NombreCorto}');
  if not DirExists(Estado) then Exit;

  { El expediente del estudiante no se puede volver a generar. No se borra
    salvo que se pida expresamente, y la respuesta por defecto es conservarlo. }
  if MsgBox('¿Eliminar también el expediente de los estudiantes de este equipo' + #13#10 +
            '(notas, progreso e intentos) y la configuración local?' + #13#10#13#10 +
            'Si vas a reinstalar AVACOM OPS Master, toca No para conservarlo.',
            mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    DelTree(Estado, True, True, True);
end;
