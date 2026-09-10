using System.Text.Json.Serialization;

namespace Avacom.Lms.Core.Models;

// Contratos del backend del LMS sobre AVACOM Biblioteca y el expediente.
// Los nombres JSON son los del backend (snake_case); los del contrato de la
// biblioteca se conservan tal cual llegan. Ningún tipo de aquí guarda una clave.

public sealed record EstadoBiblioteca(
    [property: JsonPropertyName("disponible")] bool Disponible,
    [property: JsonPropertyName("motivo")] string? Motivo,
    [property: JsonPropertyName("sugerencia")] string? Sugerencia,
    [property: JsonPropertyName("contrato")] int? Contrato,
    [property: JsonPropertyName("huella_catalogo")] string? HuellaCatalogo,
    [property: JsonPropertyName("capacidades")] IReadOnlyList<string>? Capacidades,
    [property: JsonPropertyName("conteos")] ConteosBiblioteca? Conteos)
{
    public static EstadoBiblioteca SinBackend(string motivo) => new(false, motivo, null, null, null, [], null);
    public bool Tiene(string capacidad) => Capacidades?.Contains(capacidad) == true;
}

public sealed record ConteosBiblioteca(
    [property: JsonPropertyName("elementos")] int Elementos,
    [property: JsonPropertyName("paquetes")] int Paquetes,
    [property: JsonPropertyName("politicas")] int Politicas,
    [property: JsonPropertyName("cursos")] int Cursos);

public sealed record CursoResumen(
    [property: JsonPropertyName("curso_ref")] string CursoRef,
    [property: JsonPropertyName("titulo")] string Titulo,
    [property: JsonPropertyName("version_vigente")] string? VersionVigente,
    [property: JsonPropertyName("pais")] string? Pais,
    [property: JsonPropertyName("nivel")] string? Nivel,
    [property: JsonPropertyName("grado")] string? Grado,
    [property: JsonPropertyName("asignatura")] string? Asignatura,
    [property: JsonPropertyName("idioma")] string? Idioma,
    [property: JsonPropertyName("lecciones")] int Lecciones,
    [property: JsonPropertyName("elementos")] int Elementos,
    [property: JsonPropertyName("actualizado_en")] long ActualizadoEn,
    [property: JsonPropertyName("disponible")] bool? Disponible,
    [property: JsonPropertyName("inscrito")] bool Inscrito,
    [property: JsonPropertyName("progreso")] double? Progreso,
    [property: JsonPropertyName("aviso")] string? Aviso)
{
    public string Subtitulo => string.Join(" · ", new[] { Asignatura, NivelLegible, Grado is null ? null : $"Grado {Grado}" }
        .Where(x => !string.IsNullOrWhiteSpace(x)));

    public string NivelLegible => Nivel switch
    {
        "preescolar" => "Preescolar",
        "primaria" => "Primaria",
        "secundaria" => "Secundaria",
        "media" => "Media",
        _ => Nivel ?? string.Empty,
    };

    public string Detalle => $"{Elementos} materiales · {Lecciones} lección(es) · versión {VersionVigente ?? "?"}";
    public double ProgresoFraccion => Math.Clamp((Progreso ?? 0) / 100d, 0, 1);
    public string ProgresoTexto => Progreso is null ? string.Empty : $"{Progreso:0}%";
}

public sealed record RespuestaCursos(
    [property: JsonPropertyName("disponible")] bool Disponible,
    [property: JsonPropertyName("aviso")] string? Aviso,
    [property: JsonPropertyName("huella_catalogo")] string? HuellaCatalogo,
    [property: JsonPropertyName("capacidades")] IReadOnlyList<string>? Capacidades,
    [property: JsonPropertyName("cursos")] IReadOnlyList<CursoResumen> Cursos)
{
    public static RespuestaCursos Vacia(string aviso) => new(false, aviso, null, [], []);
}

public sealed record ItemCurso(
    [property: JsonPropertyName("orden")] int Orden,
    [property: JsonPropertyName("tipo")] string Tipo,
    [property: JsonPropertyName("elemento_ref")] string ElementoRef,
    [property: JsonPropertyName("titulo")] string Titulo,
    [property: JsonPropertyName("version")] string? Version,
    [property: JsonPropertyName("duracion_seg")] int? DuracionSeg,
    [property: JsonPropertyName("visible")] bool Visible,
    [property: JsonPropertyName("abierto")] bool Abierto,
    [property: JsonPropertyName("completado")] bool Completado,
    [property: JsonPropertyName("estado_intento")] string? EstadoIntento,
    [property: JsonPropertyName("puntaje")] double? Puntaje,
    [property: JsonPropertyName("intento_id")] long? IntentoId)
{
    public bool EsEvaluable => Tipo is "evaluacion" or "actividad";
    public string TipoLegible => Tipo switch
    {
        "leccion" => "Lección",
        "video" => "Video",
        "audio" => "Audio",
        "imagen" => "Lámina",
        "documento" => "Documento",
        "interactivo" => "Interactivo",
        "actividad" => "Actividad",
        "evaluacion" => "Evaluación",
        "banco" => "Banco de preguntas",
        "scorm" => "SCORM",
        _ => Tipo,
    };
    public string Icono => Tipo switch
    {
        "leccion" => "≣",
        "video" => "▶",
        "audio" => "♪",
        "imagen" => "▣",
        "documento" => "▤",
        "interactivo" => "⌗",
        "actividad" => "✎",
        "evaluacion" => "✓",
        _ => "•",
    };
    public string EstadoTexto => !Visible ? "No se da en el aula"
        : EsEvaluable && EstadoIntento is "finalizado" ? $"Nota {Puntaje:0}/100"
        : EsEvaluable && EstadoIntento is "pendiente_correccion" ? (Puntaje is null ? "Pendiente de corrección" : $"Nota parcial {Puntaje:0}/100")
        : Completado ? "Completado"
        : Abierto ? "Visto"
        : DuracionSeg is > 0 ? $"{DuracionSeg / 60} min" : string.Empty;
}

public sealed record SeccionCurso(
    [property: JsonPropertyName("codigo")] string Codigo,
    [property: JsonPropertyName("titulo")] string Titulo,
    [property: JsonPropertyName("tipo")] string? Tipo,
    [property: JsonPropertyName("orden")] int Orden,
    [property: JsonPropertyName("items")] IReadOnlyList<ItemCurso> Items,
    [property: JsonPropertyName("progreso")] double Progreso,
    [property: JsonPropertyName("estado")] string? Estado)
{
    public string TipoLegible => string.IsNullOrWhiteSpace(Tipo) ? string.Empty : char.ToUpperInvariant(Tipo[0]) + Tipo[1..];
    public double ProgresoFraccion => Math.Clamp(Progreso / 100d, 0, 1);
    public string ProgresoTexto => $"{Progreso:0}%";
    public IReadOnlyList<ItemCurso> ItemsVisibles => Items.Where(i => i.Visible).ToList();
}

public sealed record CursoDetalle(
    [property: JsonPropertyName("curso_ref")] string CursoRef,
    [property: JsonPropertyName("titulo")] string Titulo,
    [property: JsonPropertyName("version")] string? Version,
    [property: JsonPropertyName("nivel")] string? Nivel,
    [property: JsonPropertyName("grado")] string? Grado,
    [property: JsonPropertyName("asignatura")] string? Asignatura,
    [property: JsonPropertyName("idioma")] string? Idioma,
    [property: JsonPropertyName("huella")] string? Huella,
    [property: JsonPropertyName("secciones")] IReadOnlyList<SeccionCurso> Secciones,
    [property: JsonPropertyName("progreso")] double Progreso,
    [property: JsonPropertyName("capacidades")] IReadOnlyList<string>? Capacidades)
{
    public bool Tiene(string capacidad) => Capacidades?.Contains(capacidad) == true;
    public int TotalItems => Secciones.Sum(s => s.ItemsVisibles.Count);
    public string Subtitulo => string.Join(" · ", new[] { Asignatura, Grado is null ? null : $"Grado {Grado}", Version is null ? null : $"versión {Version}" }
        .Where(x => !string.IsNullOrWhiteSpace(x)));
}

public sealed record PasoLeccion(
    [property: JsonPropertyName("orden")] int Orden,
    [property: JsonPropertyName("elemento_ref")] string ElementoRef,
    [property: JsonPropertyName("titulo")] string? Titulo,
    [property: JsonPropertyName("tipo")] string? Tipo,
    [property: JsonPropertyName("nota")] string? Nota,
    [property: JsonPropertyName("disponible")] bool Disponible);

public sealed record LeccionDetalle(
    [property: JsonPropertyName("elemento_ref")] string ElementoRef,
    [property: JsonPropertyName("titulo")] string Titulo,
    [property: JsonPropertyName("version")] string? Version,
    [property: JsonPropertyName("pasos")] IReadOnlyList<PasoLeccion> Pasos);

public sealed record PreguntaEvaluacion(
    [property: JsonPropertyName("ref")] string Ref,
    [property: JsonPropertyName("orden")] int Orden,
    [property: JsonPropertyName("tipo")] string? Tipo,
    [property: JsonPropertyName("enunciado")] string Enunciado,
    [property: JsonPropertyName("peso")] double Peso,
    [property: JsonPropertyName("dificultad")] string? Dificultad,
    [property: JsonPropertyName("corregible")] bool Corregible,
    [property: JsonPropertyName("voz")] bool Voz,
    [property: JsonPropertyName("respondida")] bool Respondida,
    [property: JsonPropertyName("acierta")] bool? Acierta,
    [property: JsonPropertyName("retroalimentacion")] string? Retroalimentacion);

public sealed record IntentoIniciado(
    [property: JsonPropertyName("id")] long Id,
    [property: JsonPropertyName("evaluacion_ref")] string EvaluacionRef,
    [property: JsonPropertyName("titulo")] string? Titulo,
    [property: JsonPropertyName("tipo")] string? Tipo,
    [property: JsonPropertyName("estado")] string Estado,
    [property: JsonPropertyName("creado")] bool Creado,
    [property: JsonPropertyName("puede_corregir")] bool PuedeCorregir,
    [property: JsonPropertyName("pregunta_actual")] int PreguntaActual,
    [property: JsonPropertyName("total_preguntas")] int TotalPreguntas,
    [property: JsonPropertyName("preguntas")] IReadOnlyList<PreguntaEvaluacion> Preguntas);

public sealed record VeredictoRespuesta(
    [property: JsonPropertyName("intento_id")] long IntentoId,
    [property: JsonPropertyName("pregunta_ref")] string PreguntaRef,
    [property: JsonPropertyName("acierta")] bool? Acierta,
    [property: JsonPropertyName("retroalimentacion")] string? Retroalimentacion,
    [property: JsonPropertyName("corregida")] bool Corregida,
    [property: JsonPropertyName("motivo")] string? Motivo);

public sealed record ResultadoIntento(
    [property: JsonPropertyName("id")] long Id,
    [property: JsonPropertyName("estado")] string Estado,
    [property: JsonPropertyName("puntaje")] double? Puntaje,
    [property: JsonPropertyName("aciertos")] int Aciertos,
    [property: JsonPropertyName("total_preguntas")] int TotalPreguntas,
    [property: JsonPropertyName("pendientes")] int Pendientes,
    [property: JsonPropertyName("progreso_curso")] double? ProgresoCurso);

public sealed record AperturaRegistrada(
    [property: JsonPropertyName("id")] long Id,
    [property: JsonPropertyName("estructura_disponible")] bool EstructuraDisponible,
    [property: JsonPropertyName("progreso_seccion")] double ProgresoSeccion,
    [property: JsonPropertyName("progreso_curso")] double ProgresoCurso);

public sealed record NotaEstudiante(
    [property: JsonPropertyName("evaluacion_ref")] string EvaluacionRef,
    [property: JsonPropertyName("evaluacion_rotulo")] string? EvaluacionRotulo,
    [property: JsonPropertyName("estado")] string Estado,
    [property: JsonPropertyName("puntaje")] double? Puntaje);

public sealed record EstudianteConsolidado(
    [property: JsonPropertyName("persona_id")] string PersonaId,
    [property: JsonPropertyName("persona_rotulo")] string PersonaRotulo,
    [property: JsonPropertyName("progreso")] double Progreso,
    [property: JsonPropertyName("aperturas")] int Aperturas,
    [property: JsonPropertyName("segundos")] int Segundos,
    [property: JsonPropertyName("ultima_actividad")] long? UltimaActividad,
    [property: JsonPropertyName("notas")] IReadOnlyList<NotaEstudiante> Notas)
{
    public string Iniciales
    {
        get
        {
            var partes = PersonaRotulo.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            return partes.Length == 0 ? "?" : string.Concat(partes.Take(2).Select(p => char.ToUpperInvariant(p[0])));
        }
    }
    public double ProgresoFraccion => Math.Clamp(Progreso / 100d, 0, 1);
    public string ProgresoTexto => $"{Progreso:0}%";
    public string TiempoTexto => Segundos < 60 ? $"{Segundos} s" : $"{Segundos / 60} min";
    public string NotasTexto => Notas.Count == 0 ? "Sin evaluaciones" :
        string.Join(" · ", Notas.Select(n => n.Puntaje is null ? $"{n.EvaluacionRotulo ?? n.EvaluacionRef}: pendiente" : $"{n.EvaluacionRotulo ?? n.EvaluacionRef}: {n.Puntaje:0}/100"));
    public string UltimaActividadTexto => UltimaActividad is null ? "Sin actividad" :
        DateTimeOffset.FromUnixTimeMilliseconds(UltimaActividad.Value).ToLocalTime().ToString("dd/MM HH:mm");
}

public sealed record ResumenConsolidado(
    [property: JsonPropertyName("estudiantes")] int Estudiantes,
    [property: JsonPropertyName("promedio_progreso")] double PromedioProgreso,
    [property: JsonPropertyName("aperturas")] int Aperturas,
    [property: JsonPropertyName("intentos_finalizados")] int IntentosFinalizados);

public sealed record ConsolidadoCurso(
    [property: JsonPropertyName("curso_ref")] string CursoRef,
    [property: JsonPropertyName("titulo")] string? Titulo,
    [property: JsonPropertyName("estructura_disponible")] bool EstructuraDisponible,
    [property: JsonPropertyName("resumen")] ResumenConsolidado Resumen,
    [property: JsonPropertyName("estudiantes")] IReadOnlyList<EstudianteConsolidado> Estudiantes);
