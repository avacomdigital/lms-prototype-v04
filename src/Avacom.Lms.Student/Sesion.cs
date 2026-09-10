using Avacom.Lms.Core.Models;
using Avacom.Lms.Core.Services;

namespace Avacom.Lms.Student;

/// <summary>
/// La sesión del estudiante: quién es (identidad lógica del expediente), en qué
/// aula está (backend) y la fachada hacia la biblioteca a través del backend.
/// </summary>
public static class Sesion
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(15) };
    private static IBibliotecaDeContenido? _biblioteca;
    private static Uri? _baseActual;

    public static string Nombre => Preferences.Default.Get("student_name", ConnectionOptions.Default.StudentName);
    public static string PersonaId => Identidad.SlugDe(Nombre);

    public static Uri BaseUri
    {
        get
        {
            var texto = Preferences.Default.Get("student_server", ConnectionOptions.Default.ServerAddress);
            try { return ConnectionOptions.Normalize(texto); }
            catch (ArgumentException) { return ConnectionOptions.Normalize(ConnectionOptions.Default.ServerAddress); }
        }
    }

    public static IBibliotecaDeContenido Biblioteca
    {
        get
        {
            var actual = BaseUri;
            if (_biblioteca is null || _baseActual != actual)
            {
                _biblioteca = new BibliotecaDeContenido(Http, actual);
                _baseActual = actual;
            }
            return _biblioteca;
        }
    }

    public static string Dispositivo => $"student-{DeviceInfo.Current.Name}";

    public static readonly string[] Paleta = ["#E5262B", "#F3C701", "#01A4E1", "#019D60", "#A81D81", "#52525B"];

    public const string IconoLibro =
        "M232,48 H160 A40,40 0 0 0 128,64 A40,40 0 0 0 96,48 H24 A8,8 0 0 0 16,56 V200 A8,8 0 0 0 24,208 H96 A24,24 0 0 1 120,232 A8,8 0 0 0 136,232 A24,24 0 0 1 160,208 H232 A8,8 0 0 0 240,200 V56 A8,8 0 0 0 232,48 Z M96,192 H32 V64 H96 A24,24 0 0 1 120,88 V200 A39.81,39.81 0 0 0 96,192 Z M224,192 H160 A39.81,39.81 0 0 0 136,200 V88 A24,24 0 0 1 160,64 H224 Z";
}
