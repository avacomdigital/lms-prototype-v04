using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;

namespace Avacom.Ops.Host;

/// <summary>
/// Comprobaciones sobre el puerto y sobre la salud real del backend.
///
/// El endpoint /health/ ya existe en el backend (avacom_lms/urls.py). El
/// instalador lo usa tal cual: añadirlo o cambiarlo seria modificar el
/// comportamiento del producto, que es justo lo que no debe hacer.
/// </summary>
internal static class Salud
{
    /// <summary>
    /// El backend escucha en 0.0.0.0 pero a 0.0.0.0 no se le puede preguntar:
    /// la comprobacion se hace por loopback, que es donde vive el cliente OPS.
    /// </summary>
    public static string UrlSalud(int puerto) => $"http://127.0.0.1:{puerto}/health/";

    public sealed record Resultado(bool Correcto, string Detalle);

    /// <summary>Espera hasta <paramref name="segundos"/> a que el backend conteste.</summary>
    public static async Task<Resultado> EsperarAsync(int puerto, int segundos, CancellationToken cancelacion = default)
    {
        using var cliente = new HttpClient { Timeout = TimeSpan.FromSeconds(4) };
        var limite = DateTimeOffset.UtcNow.AddSeconds(segundos);
        var ultimo = "el backend no contesto todavia";

        while (DateTimeOffset.UtcNow < limite && !cancelacion.IsCancellationRequested)
        {
            try
            {
                using var respuesta = await cliente.GetAsync(UrlSalud(puerto), cancelacion).ConfigureAwait(false);
                var cuerpo = await respuesta.Content.ReadAsStringAsync(cancelacion).ConfigureAwait(false);

                if (respuesta.IsSuccessStatusCode && cuerpo.Contains("avacom-lms-backend", StringComparison.Ordinal))
                {
                    return new Resultado(true, Resumir(cuerpo));
                }
                ultimo = $"contesto {(int)respuesta.StatusCode} en {UrlSalud(puerto)}";
            }
            catch (Exception error) when (error is HttpRequestException or TaskCanceledException)
            {
                ultimo = "el backend no acepta conexiones todavia";
            }

            try
            {
                await Task.Delay(TimeSpan.FromSeconds(1), cancelacion).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                break;
            }
        }
        return new Resultado(false, ultimo);
    }

    /// <summary>true si nadie escucha aun en el puerto.</summary>
    public static bool PuertoLibre(int puerto)
    {
        var escuchando = IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners();
        if (escuchando.Any(p => p.Port == puerto)) return false;

        // Escuchar en la lista de puertos no basta: un socket exclusivo puede
        // impedir el bind sin figurar. Se comprueba haciendo el mismo bind que
        // hara Waitress.
        try
        {
            using var prueba = new TcpListener(IPAddress.Any, puerto);
            prueba.Start();
            prueba.Stop();
            return true;
        }
        catch (SocketException)
        {
            return false;
        }
    }

    /// <summary>
    /// Si el puerto esta ocupado, ¿lo ocupa nuestro propio backend? Distinguirlo
    /// evita que una reinstalacion se lea como un conflicto con otro programa.
    /// </summary>
    public static async Task<bool> EsNuestroBackendAsync(int puerto)
    {
        var resultado = await EsperarAsync(puerto, 2).ConfigureAwait(false);
        return resultado.Correcto;
    }

    private static string Resumir(string cuerpo)
    {
        var disponible = cuerpo.Contains("\"disponible\":true", StringComparison.Ordinal);
        return disponible
            ? "backend operativo y AVACOM Biblioteca disponible"
            : "backend operativo; AVACOM Biblioteca no esta abierta en este equipo";
    }
}
