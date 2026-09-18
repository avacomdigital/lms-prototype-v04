using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Avacom.Lms.Core.Models;

namespace Avacom.Lms.Core.Services;

/// <summary>
/// Cliente de <c>/api/aula/</c> (MOD-007 · Classroom Engine) para OPS y Student.
///
/// Mismas reglas que <see cref="BibliotecaDeContenido"/>: habla con el backend del
/// LMS (nunca con la biblioteca), toda URL nace de <see cref="BaseUri"/>, un 503 no es
/// una excepción de negocio (devuelve null y deja el motivo en <see cref="UltimoMotivo"/>)
/// y los cuerpos viajan con Content-Length. Además expone <see cref="UltimoError"/> con el
/// <c>codigo</c> del backend para que la pantalla decida (por ejemplo
/// <c>sesion_activa_existente</c> → «Continuar esa clase»).
/// </summary>
public interface IAulaApi
{
    Uri BaseUri { get; }
    string Fuente { get; }
    string? UltimoMotivo { get; }
    ErrorAula? UltimoError { get; }
    Uri Absoluta(string rutaRelativa);

    Task<CatalogoAula?> CursosAsync(CancellationToken ct = default);
    Task<VistaCurso?> CursoAsync(string cursoRef, bool docente, CancellationToken ct = default);
    Task<ObjetoSuelto?> ObjetoAsync(string cursoRef, string objetoRef, bool docente, CancellationToken ct = default);

    Task<SesionDeClase?> IniciarAsync(IniciarSesionSolicitud solicitud, CancellationToken ct = default);
    Task<SesionDeClase?> SesionAsync(string sesionId, CancellationToken ct = default);
    Task<FocoAula?> ProyectarAsync(string sesionId, string actor, string objetoRef, string? unidadRef, CancellationToken ct = default);
    Task<bool> ControlAsync(string sesionId, string actor, string tipo, bool activo, CancellationToken ct = default);
    Task<DistribucionAula?> DistribuirAsync(string sesionId, string actor, DistribuirSolicitud solicitud, CancellationToken ct = default);
    Task<DistribucionAula?> CerrarDistribucionAsync(string sesionId, string actor, string distribucionId, CancellationToken ct = default);
    Task<bool> AvisarAsync(string sesionId, string actor, string texto, string? participanteId, CancellationToken ct = default);
    Task<ParticipanteAula?> ParticipanteAsync(string sesionId, string actor, string participanteId, string accion, CancellationToken ct = default);
    Task<SesionDeClase?> CerrarAsync(string sesionId, string actor, bool forzar, CancellationToken ct = default);

    Task<EstadoTableta?> UnirseAsync(string codigo, string personaId, string personaRotulo, string dispositivo, string? participanteId, CancellationToken ct = default);
    Task<EstadoTableta?> EstadoAsync(string sesionId, string participanteId, CancellationToken ct = default);
    Task<EstadoTableta?> PresenciaAsync(string sesionId, string participanteId, string? estado, string dispositivo, CancellationToken ct = default);
    Task<bool> ConfirmarEntregaAsync(string sesionId, string distribucionId, string participanteId, CancellationToken ct = default);
}

public sealed class AulaApi(HttpClient http, Uri baseUri, string fuente = "ejemplo") : IAulaApi
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public Uri BaseUri { get; } = baseUri;
    public string Fuente { get; } = fuente;
    public string? UltimoMotivo { get; private set; }
    public ErrorAula? UltimoError { get; private set; }

    public Uri Absoluta(string rutaRelativa) => new(BaseUri, rutaRelativa.TrimStart('/'));

    private string ConFuente(string ruta) => ruta.Contains('?') ? $"{ruta}&fuente={Fuente}" : $"{ruta}?fuente={Fuente}";

    // ------------------------------------------------------------------ curso

    public Task<CatalogoAula?> CursosAsync(CancellationToken ct = default) =>
        ObtenerAsync<CatalogoAula>(ConFuente("api/aula/cursos/"), ct);

    public Task<VistaCurso?> CursoAsync(string cursoRef, bool docente, CancellationToken ct = default) =>
        ObtenerAsync<VistaCurso>(ConFuente($"api/aula/cursos/{Uri.EscapeDataString(cursoRef)}/?rol={(docente ? "docente" : "estudiante")}"), ct);

    public Task<ObjetoSuelto?> ObjetoAsync(string cursoRef, string objetoRef, bool docente, CancellationToken ct = default) =>
        ObtenerAsync<ObjetoSuelto>(ConFuente($"api/aula/cursos/{Uri.EscapeDataString(cursoRef)}/objetos/{Uri.EscapeDataString(objetoRef)}/?rol={(docente ? "docente" : "estudiante")}"), ct);

    // ----------------------------------------------------------------- docente

    public Task<SesionDeClase?> IniciarAsync(IniciarSesionSolicitud s, CancellationToken ct = default) =>
        EnviarAsync<SesionDeClase>("api/aula/sesiones/", new
        {
            via = s.Via, curso_ref = s.CursoRef, leccion_ref = s.LeccionRef, objeto_ref = s.ObjetoRef, fuente = s.Fuente,
            profesor_id = s.ProfesorId, profesor_rotulo = s.ProfesorRotulo, superficie = s.Superficie,
        }, ct);

    public Task<SesionDeClase?> SesionAsync(string sesionId, CancellationToken ct = default) =>
        ObtenerAsync<SesionDeClase>($"api/aula/sesiones/{sesionId}/", ct);

    public Task<FocoAula?> ProyectarAsync(string sesionId, string actor, string objetoRef, string? unidadRef, CancellationToken ct = default) =>
        EnviarAsync<FocoAula>($"api/aula/sesiones/{sesionId}/foco/", new { objeto_ref = objetoRef, unidad_ref = unidadRef, profesor_id = actor }, ct);

    public async Task<bool> ControlAsync(string sesionId, string actor, string tipo, bool activo, CancellationToken ct = default) =>
        await EnviarAsync<JsonElement?>($"api/aula/sesiones/{sesionId}/controles/", new { tipo, activo, profesor_id = actor }, ct) is not null;

    public Task<DistribucionAula?> DistribuirAsync(string sesionId, string actor, DistribuirSolicitud s, CancellationToken ct = default) =>
        EnviarAsync<DistribucionAula>($"api/aula/sesiones/{sesionId}/distribuciones/", new
        {
            clase = s.Clase, objeto_ref = s.ObjetoRef, media_ref = s.MediaRef, rotulo = s.Rotulo,
            disponible_estudio = s.DisponibleEstudio, profesor_id = actor,
        }, ct);

    public Task<DistribucionAula?> CerrarDistribucionAsync(string sesionId, string actor, string distribucionId, CancellationToken ct = default) =>
        EnviarAsync<DistribucionAula>($"api/aula/sesiones/{sesionId}/distribuciones/{distribucionId}/cerrar/", new { profesor_id = actor }, ct);

    public async Task<bool> AvisarAsync(string sesionId, string actor, string texto, string? participanteId, CancellationToken ct = default) =>
        await EnviarAsync<AvisoAula>($"api/aula/sesiones/{sesionId}/avisos/", new { texto, participante_id = participanteId, profesor_id = actor }, ct) is not null;

    public Task<ParticipanteAula?> ParticipanteAsync(string sesionId, string actor, string participanteId, string accion, CancellationToken ct = default) =>
        EnviarAsync<ParticipanteAula>($"api/aula/sesiones/{sesionId}/participantes/{participanteId}/{accion}/", new { profesor_id = actor }, ct);

    public Task<SesionDeClase?> CerrarAsync(string sesionId, string actor, bool forzar, CancellationToken ct = default) =>
        EnviarAsync<SesionDeClase>($"api/aula/sesiones/{sesionId}/cerrar/", new { forzar, profesor_id = actor }, ct);

    // -------------------------------------------------------------- estudiante

    public Task<EstadoTableta?> UnirseAsync(string codigo, string personaId, string personaRotulo, string dispositivo, string? participanteId, CancellationToken ct = default) =>
        EnviarAsync<EstadoTableta>("api/aula/sesiones/unirse/", new
        {
            codigo_union = codigo, persona_id = personaId, persona_rotulo = personaRotulo, dispositivo, participante_id = participanteId,
        }, ct);

    public Task<EstadoTableta?> EstadoAsync(string sesionId, string participanteId, CancellationToken ct = default) =>
        ObtenerAsync<EstadoTableta>($"api/aula/sesiones/{sesionId}/estado/?participante={Uri.EscapeDataString(participanteId)}", ct);

    public Task<EstadoTableta?> PresenciaAsync(string sesionId, string participanteId, string? estado, string dispositivo, CancellationToken ct = default) =>
        EnviarAsync<EstadoTableta>($"api/aula/sesiones/{sesionId}/participantes/{participanteId}/presencia/", new { estado, dispositivo }, ct);

    public async Task<bool> ConfirmarEntregaAsync(string sesionId, string distribucionId, string participanteId, CancellationToken ct = default) =>
        await EnviarAsync<JsonElement?>($"api/aula/sesiones/{sesionId}/distribuciones/{distribucionId}/confirmar/", new { participante_id = participanteId }, ct) is not null;

    // ------------------------------------------------------------------ ayudas

    private async Task<T?> ObtenerAsync<T>(string ruta, CancellationToken ct)
    {
        try
        {
            using var respuesta = await http.GetAsync(Absoluta(ruta), ct);
            if (!respuesta.IsSuccessStatusCode)
            {
                await RegistrarErrorAsync(respuesta, ct);
                return default;
            }
            Limpiar();
            return await respuesta.Content.ReadFromJsonAsync<T>(Json, ct);
        }
        catch (Exception ex) when (EsDeRed(ex))
        {
            SinRed();
            return default;
        }
    }

    private async Task<T?> EnviarAsync<T>(string ruta, object cuerpo, CancellationToken ct)
    {
        try
        {
            // Serializado a texto para viajar con Content-Length (el servidor de desarrollo
            // de Django no lee cuerpos troceados; misma decisión que BibliotecaDeContenido).
            var contenido = new StringContent(JsonSerializer.Serialize(cuerpo, Json), Encoding.UTF8, "application/json");
            using var respuesta = await http.PostAsync(Absoluta(ruta), contenido, ct);
            if (!respuesta.IsSuccessStatusCode)
            {
                await RegistrarErrorAsync(respuesta, ct);
                return default;
            }
            Limpiar();
            return await respuesta.Content.ReadFromJsonAsync<T>(Json, ct);
        }
        catch (Exception ex) when (EsDeRed(ex))
        {
            SinRed();
            return default;
        }
    }

    private void Limpiar()
    {
        UltimoMotivo = null;
        UltimoError = null;
    }

    private void SinRed()
    {
        UltimoMotivo = "No hay conexión con el aula.";
        UltimoError = new ErrorAula(0, "sin_conexion", UltimoMotivo, "Revisa que el equipo del aula esté encendido y en la misma red.", null);
    }

    private async Task RegistrarErrorAsync(HttpResponseMessage respuesta, CancellationToken ct)
    {
        var estado = (int)respuesta.StatusCode;
        string? codigo = null, detalle = null, sugerencia = null;
        JsonElement? extra = null;
        try
        {
            var texto = await respuesta.Content.ReadAsStringAsync(ct);
            if (!string.IsNullOrWhiteSpace(texto))
            {
                using var doc = JsonDocument.Parse(texto);
                var raiz = doc.RootElement.Clone();
                extra = raiz;
                if (raiz.ValueKind == JsonValueKind.Object)
                {
                    if (raiz.TryGetProperty("detail", out var d) && d.ValueKind == JsonValueKind.String) detalle = d.GetString();
                    if (raiz.TryGetProperty("codigo", out var c) && c.ValueKind == JsonValueKind.String) codigo = c.GetString();
                    if (raiz.TryGetProperty("sugerencia", out var s) && s.ValueKind == JsonValueKind.String) sugerencia = s.GetString();
                }
            }
        }
        catch (JsonException) { }
        detalle ??= estado switch
        {
            (int)HttpStatusCode.ServiceUnavailable => "El aula no puede leer el curso en este momento.",
            (int)HttpStatusCode.NotFound => "No se encontró lo que se pedía.",
            _ => $"El backend respondió {estado}.",
        };
        UltimoMotivo = detalle;
        UltimoError = new ErrorAula(estado, codigo, detalle, sugerencia, extra);
    }

    private static bool EsDeRed(Exception ex) =>
        ex is HttpRequestException or TaskCanceledException or JsonException or IOException;
}
