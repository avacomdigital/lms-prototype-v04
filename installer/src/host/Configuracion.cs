using System.Security.Cryptography;
using System.Text;

namespace Avacom.Ops.Host;

/// <summary>
/// La configuracion local del nodo: un archivo de variables de entorno que el
/// instalador genera en la primera instalacion y que el servicio le pasa al
/// backend.
///
/// Por que variables de entorno y no un settings.py editado: el backend YA lee
/// su configuracion de os.environ (AVACOM_LMS_SECRET, AVACOM_LMS_DB,
/// AVACOM_LMS_DEBUG, ...). Configurarlo asi es usar el mecanismo que el
/// producto ya tiene, sin tocar una sola linea de su codigo.
/// </summary>
internal static class Configuracion
{
    public const string HostPorDefecto = "0.0.0.0";
    public const int PuertoPorDefecto = 8000;
    public const int HilosPorDefecto = 8;

    public static Dictionary<string, string> Leer()
    {
        var valores = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        if (!File.Exists(Rutas.ArchivoConfig)) return valores;

        foreach (var linea in File.ReadAllLines(Rutas.ArchivoConfig))
        {
            var texto = linea.Trim();
            if (texto.Length == 0 || texto.StartsWith('#')) continue;

            var corte = texto.IndexOf('=');
            if (corte <= 0) continue;

            var clave = texto[..corte].Trim();
            var valor = texto[(corte + 1)..].Trim();
            if (clave.Length > 0) valores[clave] = valor;
        }
        return valores;
    }

    public static int PuertoConfigurado()
    {
        var valores = Leer();
        return valores.TryGetValue("AVACOM_OPS_BACKEND_PORT", out var texto)
            && int.TryParse(texto, out var puerto)
            && puerto is > 0 and < 65536
                ? puerto
                : PuertoPorDefecto;
    }

    /// <summary>
    /// Genera la configuracion si no existe. Es idempotente a proposito: una
    /// reinstalacion o una actualizacion no debe cambiar la clave secreta ni
    /// mover la base de datos de un nodo que ya tiene expediente cargado.
    /// </summary>
    /// <returns>true si el archivo se creo en esta llamada.</returns>
    public static bool CrearSiFalta(Registro registro)
    {
        Rutas.AsegurarCarpetasDeEstado();

        if (File.Exists(Rutas.ArchivoConfig))
        {
            registro.Escribir($"La configuracion ya existia, se conserva: {Rutas.ArchivoConfig}");
            return false;
        }

        var contenido = new StringBuilder();
        contenido.AppendLine("# Configuracion local de AVACOM OPS Master (backend).");
        contenido.AppendLine("# Generada por el instalador. Una reinstalacion NO la sobrescribe.");
        contenido.AppendLine("#");
        contenido.AppendLine("# Formato: CLAVE=valor, una por linea. El servicio AVACOMOPSBackend");
        contenido.AppendLine("# las entrega al backend como variables de entorno.");
        contenido.AppendLine();
        contenido.AppendLine("# Clave de firma de este nodo. Unica por instalacion.");
        contenido.AppendLine($"AVACOM_LMS_SECRET={ClaveNueva()}");
        contenido.AppendLine();
        contenido.AppendLine("# 0 en una instalacion distribuida: sin trazas de error hacia la LAN del aula.");
        contenido.AppendLine("# Ponlo en 1 solo para diagnosticar, y reinicia el servicio AVACOMOPSBackend.");
        contenido.AppendLine("AVACOM_LMS_DEBUG=0");
        contenido.AppendLine();
        contenido.AppendLine("# El expediente del estudiante. Es el unico dato del sistema que no se");
        contenido.AppendLine("# puede volver a generar: vive fuera de Program Files y sobrevive a");
        contenido.AppendLine("# cualquier reinstalacion o actualizacion del producto.");
        contenido.AppendLine($"AVACOM_LMS_DB={Rutas.BaseDeDatos}");
        contenido.AppendLine();
        contenido.AppendLine("# Escucha de la API local. Las tabletas llegan por la IP del equipo maestro.");
        contenido.AppendLine($"AVACOM_OPS_BACKEND_HOST={HostPorDefecto}");
        contenido.AppendLine($"AVACOM_OPS_BACKEND_PORT={PuertoPorDefecto}");
        contenido.AppendLine($"AVACOM_OPS_BACKEND_THREADS={HilosPorDefecto}");
        contenido.AppendLine();
        contenido.AppendLine("# Tiempo de espera hacia AVACOM Biblioteca, en segundos.");
        contenido.AppendLine("AVACOM_CONTENIDO_TIEMPO_ESPERA_SEG=3");
        contenido.AppendLine();
        contenido.AppendLine("# AVACOM_CONTENIDO_ENLACE se deja SIN definir a proposito: el backend");
        contenido.AppendLine("# busca la nota de enlace de AVACOM Biblioteca donde la biblioteca la");
        contenido.AppendLine("# publica (%ProgramData%\AVACOM\contenido\enlace.json). Definirla aqui");
        contenido.AppendLine("# solo sirve para pruebas con el host de pruebas del repositorio.");

        File.WriteAllText(Rutas.ArchivoConfig, contenido.ToString(), new UTF8Encoding(false));
        registro.Escribir($"Configuracion creada: {Rutas.ArchivoConfig}");
        return true;
    }

    private static string ClaveNueva()
    {
        const string alfabeto = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%^&*(-_=+)";
        var salida = new StringBuilder(64);
        for (var i = 0; i < 64; i++)
        {
            salida.Append(alfabeto[RandomNumberGenerator.GetInt32(alfabeto.Length)]);
        }
        return salida.ToString();
    }
}
