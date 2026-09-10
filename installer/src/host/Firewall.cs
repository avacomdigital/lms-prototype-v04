using System.Diagnostics;

namespace Avacom.Ops.Host;

/// <summary>
/// Regla de Windows Defender Firewall para la API del aula.
///
/// El backend escucha en 0.0.0.0:8000 porque las tabletas llegan por la IP del
/// equipo maestro. Sin regla, Windows bloquea esas conexiones entrantes y el
/// sintoma que ve el aula es "las tabletas no ven el curso", que no se parece
/// nada a la causa. Por eso la regla se crea en la instalacion.
///
/// Se limita a perfiles privado y de dominio: la LAN del aula es una red
/// privada y la API no tiene autenticacion (es un prototipo de aula cerrada),
/// asi que no se abre en redes publicas.
/// </summary>
internal static class Firewall
{
    public const string NombreRegla = "AVACOM OPS Master Backend";

    public static int Abrir(Registro registro, int puerto)
    {
        // Idempotente: se borra la anterior para no acumular reglas iguales
        // en cada reinstalacion.
        Netsh(registro, ["advfirewall", "firewall", "delete", "rule", $"name={NombreRegla}"]);

        var codigo = Netsh(registro,
        [
            "advfirewall", "firewall", "add", "rule",
            $"name={NombreRegla}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            $"localport={puerto}",
            "profile=private,domain",
            "enable=yes",
            $"program={Rutas.PythonExe}",
            "description=Permite que las tabletas del aula consulten la API local de AVACOM OPS Master.",
        ]);

        registro.Escribir(codigo == 0
            ? $"Regla de firewall creada para TCP {puerto} en redes privadas y de dominio."
            : $"No se pudo crear la regla de firewall (codigo {codigo}). " +
              "La API funciona en este equipo; puede que las tabletas no la alcancen.");
        return codigo;
    }

    public static void Cerrar(Registro registro)
    {
        var codigo = Netsh(registro, ["advfirewall", "firewall", "delete", "rule", $"name={NombreRegla}"]);
        registro.Escribir(codigo == 0
            ? "Regla de firewall eliminada."
            : "No habia regla de firewall que eliminar.");
    }

    private static int Netsh(Registro registro, IEnumerable<string> argumentos)
    {
        var inicio = new ProcessStartInfo
        {
            FileName = Path.Combine(Environment.SystemDirectory, "netsh.exe"),
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        foreach (var argumento in argumentos) inicio.ArgumentList.Add(argumento);

        try
        {
            using var proceso = Process.Start(inicio);
            if (proceso is null) return -1;
            var salida = proceso.StandardOutput.ReadToEnd() + proceso.StandardError.ReadToEnd();
            proceso.WaitForExit(60_000);
            registro.Escribir($"netsh {string.Join(" ", argumentos.Take(4))} -> {proceso.ExitCode} " +
                              salida.Replace("\r", " ").Replace("\n", " ").Trim());
            return proceso.ExitCode;
        }
        catch (Exception error)
        {
            registro.Escribir("No se pudo ejecutar netsh.exe", error);
            return -1;
        }
    }
}
