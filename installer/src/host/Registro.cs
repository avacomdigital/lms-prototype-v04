namespace Avacom.Ops.Host;

/// <summary>
/// Registro en archivo. El host no tiene consola (es un servicio y un lanzador
/// tactil), asi que el unico diagnostico posible es lo que quede escrito.
///
/// Rota por tamaño para que un backend que reinicie en bucle no llene el disco
/// del equipo del aula.
/// </summary>
internal sealed class Registro
{
    private const long TamanoMaximoBytes = 2 * 1024 * 1024;
    private readonly string _ruta;
    private readonly Lock _candado = new();

    public Registro(string nombreArchivo)
    {
        Directory.CreateDirectory(Rutas.CarpetaLogs);
        _ruta = Path.Combine(Rutas.CarpetaLogs, nombreArchivo);
    }

    public string Ruta => _ruta;

    public void Escribir(string mensaje)
    {
        var linea = $"{DateTimeOffset.Now:yyyy-MM-dd HH:mm:ss zzz}  {mensaje}";
        lock (_candado)
        {
            try
            {
                Rotar();
                File.AppendAllText(_ruta, linea + Environment.NewLine);
            }
            catch (IOException)
            {
                // Un fallo al registrar no puede tumbar el servicio.
            }
            catch (UnauthorizedAccessException)
            {
            }
        }
    }

    public void Escribir(string mensaje, Exception error) =>
        Escribir($"{mensaje}: {error.GetType().Name}: {error.Message}");

    private void Rotar()
    {
        var info = new FileInfo(_ruta);
        if (!info.Exists || info.Length < TamanoMaximoBytes) return;

        var anterior = _ruta + ".1";
        if (File.Exists(anterior)) File.Delete(anterior);
        File.Move(_ruta, anterior);
    }
}
