using System.Diagnostics;

namespace Avacom.Ops.Host;

/// <summary>
/// El proceso hijo que atiende la API: Python embebido -> Waitress -> Django/DRF.
///
/// Se lanza siempre igual, lo llame el servicio o el diagnostico, para que lo
/// que se prueba en la instalacion sea exactamente lo que corre despues.
/// </summary>
internal sealed class ProcesoBackend : IDisposable
{
    private readonly Registro _registro;
    private Process? _proceso;

    public ProcesoBackend(Registro registro) => _registro = registro;

    public bool EstaVivo => _proceso is { HasExited: false };

    public static ProcessStartInfo Preparar(string ejecutable, IEnumerable<string> argumentos)
    {
        var inicio = new ProcessStartInfo
        {
            FileName = ejecutable,
            WorkingDirectory = Rutas.CarpetaBackend,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        foreach (var argumento in argumentos) inicio.ArgumentList.Add(argumento);

        // La configuracion del nodo, tal cual la lee settings.py.
        foreach (var (clave, valor) in Configuracion.Leer())
        {
            inicio.Environment[clave] = valor;
        }
        inicio.Environment["DJANGO_SETTINGS_MODULE"] = "avacom_lms.settings";
        inicio.Environment["PYTHONUNBUFFERED"] = "1";
        // Sin esto, un error con caracteres acentuados en la consola de Windows
        // se convierte en un UnicodeEncodeError que oculta el error real.
        inicio.Environment["PYTHONIOENCODING"] = "utf-8";
        return inicio;
    }

    public bool Iniciar()
    {
        if (!File.Exists(Rutas.PythonExe))
        {
            _registro.Escribir($"No se encontro el runtime de Python en {Rutas.PythonExe}.");
            return false;
        }

        var inicio = Preparar(Rutas.PythonExe, [Rutas.GuionServidor]);
        _proceso = new Process { StartInfo = inicio, EnableRaisingEvents = true };
        _proceso.OutputDataReceived += (_, e) => { if (e.Data is not null) _registro.Escribir($"[backend] {e.Data}"); };
        _proceso.ErrorDataReceived += (_, e) => { if (e.Data is not null) _registro.Escribir($"[backend] {e.Data}"); };

        try
        {
            _proceso.Start();
            _proceso.BeginOutputReadLine();
            _proceso.BeginErrorReadLine();
            _registro.Escribir($"Backend iniciado (pid {_proceso.Id}).");
            return true;
        }
        catch (Exception error)
        {
            _registro.Escribir("No se pudo iniciar el backend", error);
            return false;
        }
    }

    public async Task<int> EsperarSalidaAsync(CancellationToken cancelacion)
    {
        if (_proceso is null) return -1;
        try
        {
            await _proceso.WaitForExitAsync(cancelacion).ConfigureAwait(false);
            return _proceso.ExitCode;
        }
        catch (OperationCanceledException)
        {
            return -1;
        }
    }

    public void Detener()
    {
        if (_proceso is null || _proceso.HasExited) return;
        try
        {
            // Waitress no cierra por señal en Windows: se termina el arbol de
            // procesos para no dejar el puerto 8000 ocupado por un huerfano.
            _proceso.Kill(entireProcessTree: true);
            _proceso.WaitForExit(10_000);
            _registro.Escribir("Backend detenido.");
        }
        catch (Exception error)
        {
            _registro.Escribir("No se pudo detener el backend limpiamente", error);
        }
    }

    public void Dispose()
    {
        Detener();
        _proceso?.Dispose();
        _proceso = null;
    }
}
