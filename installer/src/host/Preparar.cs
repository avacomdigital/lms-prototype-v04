using System.Diagnostics;
using System.Text;

namespace Avacom.Ops.Host;

/// <summary>
/// La pantalla "Backend Configuration" del instalador, hecha de verdad.
///
/// Todo lo que el README del backend le pide a una persona -crear el entorno,
/// instalar dependencias, migrar, arrancar- ocurre aqui sin que nadie escriba
/// un comando. Las dependencias ya vienen dentro del paquete, asi que este
/// paso no necesita internet ni pip.
///
/// Es idempotente: se puede repetir en una actualizacion sin perder el
/// expediente ni regenerar la clave del nodo.
/// </summary>
internal static class Preparar
{
    /// <summary>Lo que la pantalla del instalador lee para decir como fue.</summary>
    public static string ArchivoEstado => Path.Combine(Rutas.CarpetaLogs, "preparacion-estado.txt");

    public static int Ejecutar()
    {
        var registro = new Registro("instalacion.log");
        registro.Escribir("--- Preparacion del backend ---");
        registro.Escribir($"Instalacion: {Rutas.RaizInstalacion}");
        registro.Escribir($"Estado del nodo: {Rutas.RaizDatos}");

        try
        {
            Rutas.AsegurarCarpetasDeEstado();
            var nueva = Configuracion.CrearSiFalta(registro);

            if (!File.Exists(Rutas.PythonExe))
            {
                return Terminar(registro, 2, "No se encontro el runtime del backend en la carpeta de instalacion.");
            }
            if (!File.Exists(Rutas.ManagePy))
            {
                return Terminar(registro, 3, "No se encontro el backend en la carpeta de instalacion.");
            }

            // 1. El runtime distribuido puede importar lo que el backend necesita.
            var comprobacion = Python(registro,
                ["-c", "import django, rest_framework, waitress, zoneinfo, sqlite3; print(django.get_version())"]);
            if (comprobacion.Codigo != 0)
            {
                return Terminar(registro, 4, "El runtime del backend no esta completo.");
            }
            registro.Escribir($"Runtime verificado. Django {comprobacion.Salida.Trim()}.");

            // 2. Configuracion valida antes de tocar la base de datos: si algo
            //    esta mal en el .env generado, se ve aqui y no a mitad de migrar.
            var revision = Python(registro, [Rutas.ManagePy, "check"]);
            if (revision.Codigo != 0)
            {
                return Terminar(registro, 5, "La configuracion del backend no paso la revision de Django.");
            }
            registro.Escribir("Revision de configuracion de Django correcta.");

            // 3. Base de datos del expediente. Crea el archivo si no existe y
            //    aplica solo lo que falte si ya venia de una version anterior.
            var migracion = Python(registro, [Rutas.ManagePy, "migrate", "--noinput"]);
            if (migracion.Codigo != 0)
            {
                return Terminar(registro, 6, "No se pudieron aplicar las migraciones de la base de datos.");
            }
            registro.Escribir("Base de datos del expediente al dia.");

            // 4. Archivos estaticos: solo si el backend declara donde recogerlos.
            //    Este backend sirve JSON y no define STATIC_ROOT, asi que no hay
            //    nada que recoger. Se comprueba en vez de suponerlo, porque si
            //    una version futura lo define, la instalacion debe cubrirlo.
            var estaticos = Python(registro,
                ["-c",
                 "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','avacom_lms.settings');" +
                 "django.setup();from django.conf import settings;print(settings.STATIC_ROOT or '')"]);
            if (estaticos.Codigo == 0 && estaticos.Salida.Trim().Length > 0)
            {
                var recogida = Python(registro, [Rutas.ManagePy, "collectstatic", "--noinput"]);
                registro.Escribir(recogida.Codigo == 0
                    ? "Archivos estaticos recogidos."
                    : "No se pudieron recoger los archivos estaticos; la API no los necesita.");
            }
            else
            {
                registro.Escribir("El backend no publica archivos estaticos: nada que recoger.");
            }

            // 5. Validacion de ejecucion: el puerto que va a usar el servicio.
            var puerto = Configuracion.PuertoConfigurado();
            if (!Salud.PuertoLibre(puerto))
            {
                var propio = Salud.EsNuestroBackendAsync(puerto).GetAwaiter().GetResult();
                registro.Escribir(propio
                    ? $"El puerto {puerto} lo esta usando un backend de AVACOM OPS que ya estaba corriendo."
                    : $"El puerto {puerto} esta ocupado por otro programa.");
                if (!propio)
                {
                    return Terminar(registro, 7,
                        $"El puerto {puerto} esta ocupado por otro programa. " +
                        "Cierra ese programa y vuelve a ejecutar la instalacion.");
                }
            }

            var resumen = nueva
                ? "Backend configurado: configuracion del nodo creada y base de datos inicializada."
                : "Backend configurado: se conservo la configuracion y el expediente existentes.";
            return Terminar(registro, 0, resumen);
        }
        catch (Exception error)
        {
            registro.Escribir("Fallo inesperado en la preparacion", error);
            return Terminar(registro, 1, "La preparacion del backend no se pudo completar.");
        }
    }

    private static int Terminar(Registro registro, int codigo, string mensaje)
    {
        registro.Escribir($"Resultado ({codigo}): {mensaje}");
        try
        {
            File.WriteAllText(ArchivoEstado, mensaje, new UTF8Encoding(false));
        }
        catch (IOException)
        {
        }
        return codigo;
    }

    private sealed record Resultado(int Codigo, string Salida);

    private static Resultado Python(Registro registro, IEnumerable<string> argumentos)
    {
        var inicio = ProcesoBackend.Preparar(Rutas.PythonExe, argumentos);
        try
        {
            using var proceso = Process.Start(inicio);
            if (proceso is null) return new Resultado(-1, string.Empty);

            var salida = proceso.StandardOutput.ReadToEnd();
            var errores = proceso.StandardError.ReadToEnd();
            proceso.WaitForExit(300_000);

            foreach (var linea in (salida + errores).Split('\n', StringSplitOptions.RemoveEmptyEntries))
            {
                registro.Escribir($"[python] {linea.TrimEnd('\r')}");
            }
            return new Resultado(proceso.ExitCode, salida);
        }
        catch (Exception error)
        {
            registro.Escribir("No se pudo ejecutar el runtime de Python", error);
            return new Resultado(-1, string.Empty);
        }
    }
}
