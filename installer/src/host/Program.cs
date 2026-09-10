using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Hosting.WindowsServices;
using Microsoft.Extensions.Logging;

namespace Avacom.Ops.Host;

/// <summary>
/// Un solo ejecutable con varios verbos. Lo usa el instalador durante la
/// instalacion y la desinstalacion, y lo usa el equipo del aula cada dia como
/// servicio y como lanzador.
///
/// Todos los verbos son no interactivos salvo <c>iniciar</c>, y ninguno pide
/// que se escriba nada: el nodo principal se maneja solo con toques.
/// </summary>
internal static class Program
{
    private static int Main(string[] argumentos)
    {
        var verbo = argumentos.Length > 0 ? argumentos[0].ToLowerInvariant() : "iniciar";

        return verbo switch
        {
            "servicio" => Servir(),
            "iniciar" => Lanzador.Ejecutar(),
            "preparar" => Preparar.Ejecutar(),
            "salud" => Comprobar(argumentos),
            "puerto-libre" => PuertoLibre(),
            "instalar-servicio" => Servicio.Instalar(new Registro("instalacion.log")),
            "quitar-servicio" => Con(Servicio.Quitar),
            "iniciar-servicio" => Servicio.Iniciar(new Registro("instalacion.log")) ? 0 : 10,
            "detener-servicio" => Con(r => Servicio.Detener(r)),
            "abrir-firewall" => Firewall.Abrir(new Registro("instalacion.log"), Configuracion.PuertoConfigurado()),
            "cerrar-firewall" => Con(Firewall.Cerrar),
            _ => Ayuda(verbo),
        };
    }

    /// <summary>Punto de entrada del servicio Windows AVACOMOPSBackend.</summary>
    private static int Servir()
    {
        // Nombre completo: en este ensamblado "Host" es el espacio de nombres propio.
        var constructor = Microsoft.Extensions.Hosting.Host.CreateApplicationBuilder();
        constructor.Services.AddHostedService<ServicioBackend>();
        constructor.Services.AddWindowsService(opciones => opciones.ServiceName = Servicio.Nombre);

        // El diagnostico va a los archivos de Logs del nodo: escribir en el
        // registro de eventos exigiria registrar un origen y no aporta nada
        // que no este ya en servicio.log.
        constructor.Logging.ClearProviders();

        constructor.Build().Run();
        return 0;
    }

    private static int Comprobar(string[] argumentos)
    {
        var segundos = argumentos.Length > 1 && int.TryParse(argumentos[1], out var valor) ? valor : 45;
        var puerto = Configuracion.PuertoConfigurado();
        var resultado = Salud.EsperarAsync(puerto, segundos).GetAwaiter().GetResult();

        var registro = new Registro("instalacion.log");
        registro.Escribir($"Comprobacion de salud en {Salud.UrlSalud(puerto)}: {resultado.Detalle}");
        return resultado.Correcto ? 0 : 11;
    }

    private static int PuertoLibre()
    {
        var puerto = Configuracion.PuertoConfigurado();
        if (Salud.PuertoLibre(puerto)) return 0;
        // 12 = ocupado por nuestro propio backend (una reinstalacion, no un conflicto).
        // 13 = ocupado por otro programa.
        return Salud.EsNuestroBackendAsync(puerto).GetAwaiter().GetResult() ? 12 : 13;
    }

    private static int Con(Action<Registro> accion)
    {
        accion(new Registro("instalacion.log"));
        return 0;
    }

    private static int Ayuda(string verbo)
    {
        Lanzador.Avisar(
            "AVACOM OPS Master",
            $"La orden \"{verbo}\" no existe.\n\n" +
            "Este componente lo usa el instalador de AVACOM OPS Master.");
        return 64;
    }
}
