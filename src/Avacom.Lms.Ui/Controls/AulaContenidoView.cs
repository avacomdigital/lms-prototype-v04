using System.Net;
using Avacom.Lms.Core.Models;
using Avacom.Lms.Ui.Design;
using Microsoft.Maui.Controls.Shapes;

namespace Avacom.Lms.Ui.Controls;

/// <summary>
/// El visor de la clase: pinta un <see cref="ObjetoAula"/> según su <c>componente</c>.
///
/// <list type="bullet">
/// <item><c>presentacion</c> · la lámina en foco con sus bloques y «Lámina N de M».</item>
/// <item><c>lectura</c> · la página en foco (texto, audio, pdf).</item>
/// <item><c>laboratorio_web</c> · cabecera pedagógica + <see cref="WebView"/> acotada al host del backend.</item>
/// <item><c>actividad</c> · instrucciones, ajustes y las preguntas en vista previa (sin claves).</item>
/// <item><c>examen</c> · tarjeta atenuada: lo aplica MOD-010.</item>
/// </list>
///
/// No conoce HTTP: recibe el objeto y una función que convierte las rutas relativas del
/// backend en URL absolutas. En modo docente (o con el seguimiento liberado) muestra los
/// mandos anterior/siguiente y avisa con <see cref="UnidadPedida"/>; en seguimiento sólo pinta
/// lo que le dicta el foco. Una sola WebView viva a la vez.
/// </summary>
public sealed class AulaContenidoView : ContentView
{
    private readonly Grid _raiz = new() { RowDefinitions = [new RowDefinition(GridLength.Star), new RowDefinition(GridLength.Auto)] };
    private readonly ContentView _cuerpo = new();
    private readonly Grid _mandos = new() { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 12, Padding = new Thickness(0, 12, 0, 0) };
    private WebView? _web;
    private string? _hostPermitido;

    public AulaContenidoView()
    {
        _raiz.Add(_cuerpo, 0, 0);
        _raiz.Add(_mandos, 0, 1);
        Content = _raiz;
        MostrarVacio();
    }

    /// <summary>Convierte una ruta relativa del backend (`/api/aula/…`) en URL absoluta.</summary>
    public Func<string, Uri>? Absoluta { get; set; }

    /// <summary>Docente o estudiante con navegación libre: se muestran anterior/siguiente.</summary>
    public bool PuedeNavegar { get; set; }

    /// <summary>Tamaño base del texto: 18 en tableta, 24 en la pantalla del aula.</summary>
    public double Escala { get; set; } = 1.0;

    public ObjetoAula? Objeto { get; private set; }
    public string? UnidadRef { get; private set; }

    /// <summary>El usuario pidió otra unidad (lámina o página): quien escucha declara el foco.</summary>
    public event EventHandler<string>? UnidadPedida;

    public void MostrarVacio(string titulo = "Nada proyectado todavía", string detalle = "Toca un objeto de la secuencia para proyectarlo.")
    {
        Objeto = null;
        UnidadRef = null;
        LimpiarWeb();
        var pila = new VerticalStackLayout { Spacing = 8, HorizontalOptions = LayoutOptions.Center, VerticalOptions = LayoutOptions.Center, Padding = 32 };
        pila.Add(new Label { Text = "⬡", FontSize = 54, TextColor = Ds.Rojo, HorizontalTextAlignment = TextAlignment.Center });
        pila.Add(Ds.Titulo(titulo, 22 * Escala));
        pila.Add(Ds.Secundario(detalle, 16 * Escala));
        ((Label)pila.Children[1]).HorizontalTextAlignment = TextAlignment.Center;
        ((Label)pila.Children[2]).HorizontalTextAlignment = TextAlignment.Center;
        _cuerpo.Content = pila;
        _mandos.Clear();
        _mandos.IsVisible = false;
    }

    public void Mostrar(ObjetoAula objeto, string? unidadRef)
    {
        Objeto = objeto;
        LimpiarWeb();
        switch (objeto.Componente)
        {
            case "presentacion":
            case "lectura":
                MostrarUnidades(objeto, unidadRef);
                break;
            case "laboratorio_web":
                UnidadRef = null;
                _cuerpo.Content = Laboratorio(objeto);
                _mandos.IsVisible = false;
                break;
            case "actividad":
                UnidadRef = null;
                _cuerpo.Content = new ScrollView { Content = Actividad(objeto) };
                _mandos.IsVisible = false;
                break;
            case "examen":
                UnidadRef = null;
                _cuerpo.Content = FueraDeAlcance(objeto);
                _mandos.IsVisible = false;
                break;
            default:
                UnidadRef = null;
                _cuerpo.Content = Ds.Tarjeta(new VerticalStackLayout
                {
                    Spacing = 6,
                    Children = { Ds.Titulo("Este contenido todavía no tiene visor", 22 * Escala), Ds.Secundario($"Tipo «{objeto.Tipo}» · componente «{objeto.Componente}».") },
                });
                _mandos.IsVisible = false;
                break;
        }
    }

    // ----------------------------------------------------------- láminas / páginas

    private void MostrarUnidades(ObjetoAula objeto, string? unidadRef)
    {
        var unidades = objeto.Unidades;
        if (unidades.Count == 0)
        {
            _cuerpo.Content = Ds.Tarjeta(Ds.Secundario("Esta presentación no tiene láminas."));
            _mandos.IsVisible = false;
            return;
        }
        var indice = Math.Max(0, unidades.ToList().FindIndex(u => u.UnidadRef == unidadRef));
        var unidad = unidades[indice];
        UnidadRef = unidad.UnidadRef;

        var pila = new VerticalStackLayout { Spacing = 18 * Escala, Padding = new Thickness(28 * Escala, 24 * Escala) };
        var cabecera = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 12 };
        cabecera.Add(Ds.Secundario($"{objeto.ComponenteLegible} · {objeto.Titulo}", 15 * Escala), 0, 0);
        cabecera.Add(Ds.Pildora(objeto.Componente == "presentacion" ? $"Lámina {indice + 1} de {unidades.Count}" : $"Página {indice + 1} de {unidades.Count}", Ds.Categoria(objeto.Componente)), 1, 0);
        pila.Add(cabecera);
        if (!string.IsNullOrWhiteSpace(unidad.Titulo)) pila.Add(Ds.Titulo(unidad.Titulo!, 30 * Escala));
        foreach (var bloque in unidad.Bloques) pila.Add(Bloque(bloque));
        if (unidad.DuracionSeg is > 0) pila.Add(Ds.Secundario($"Referencia: ~{Math.Max(1, unidad.DuracionSeg.Value / 60)} min", 14 * Escala));

        _cuerpo.Content = new ScrollView { Content = Ds.Tarjeta(pila, Ds.RadioGrande, new Thickness(0)) };
        PintarMandos(unidades, indice);
    }

    private void PintarMandos(IReadOnlyList<UnidadAula> unidades, int indice)
    {
        _mandos.Clear();
        _mandos.IsVisible = PuedeNavegar;
        if (!PuedeNavegar) return;
        var anterior = Ds.Boton("◀  Anterior", Ds.Rango.Secondary, (_, _) => { if (indice > 0) UnidadPedida?.Invoke(this, unidades[indice - 1].UnidadRef); });
        var siguiente = Ds.Boton("Siguiente  ▶", Ds.Rango.Secondary, (_, _) => { if (indice < unidades.Count - 1) UnidadPedida?.Invoke(this, unidades[indice + 1].UnidadRef); });
        anterior.IsEnabled = indice > 0;
        siguiente.IsEnabled = indice < unidades.Count - 1;
        anterior.Opacity = anterior.IsEnabled ? 1 : 0.45;
        siguiente.Opacity = siguiente.IsEnabled ? 1 : 0.45;
        var puntos = new HorizontalStackLayout { Spacing = 8, HorizontalOptions = LayoutOptions.Center, VerticalOptions = LayoutOptions.Center };
        for (var i = 0; i < unidades.Count; i++)
            puntos.Add(new BoxView { WidthRequest = i == indice ? 26 : 10, HeightRequest = 10, CornerRadius = 5, Color = i == indice ? Ds.Rojo : Color.FromArgb("#C7C4BE") });
        _mandos.Add(anterior, 0, 0);
        _mandos.Add(puntos, 1, 0);
        _mandos.Add(siguiente, 2, 0);
    }

    // ------------------------------------------------------------------ bloques

    private View Bloque(BloqueAula b)
    {
        switch (b.Componente)
        {
            case "titulo":
                return Ds.ConTramos(b.Tramos, b.Texto, (b.Nivel switch { 1 => 32, 2 => 24, _ => 20 }) * Escala);
            case "texto":
            {
                var label = Ds.ConTramos(b.Tramos, b.Texto, 20 * Escala);
                if (b.Estilo == "definition")
                    return new Border
                    {
                        BackgroundColor = Ds.PeligroSuave, StrokeThickness = 0, Padding = new Thickness(20, 16),
                        StrokeShape = new RoundRectangle { CornerRadius = Ds.RadioInterno },
                        Content = new Grid { ColumnDefinitions = [new ColumnDefinition(6), new ColumnDefinition(GridLength.Star)], ColumnSpacing = 16,
                            Children = { new BoxView { Color = Ds.Rojo, CornerRadius = 3 }, label } },
                    };
                if (b.Estilo == "highlight")
                    return new Border { BackgroundColor = Ds.AlertaSuave, StrokeThickness = 0, Padding = new Thickness(20, 16), StrokeShape = new RoundRectangle { CornerRadius = Ds.RadioInterno }, Content = label };
                return label;
            }
            case "lista":
            {
                var pila = new VerticalStackLayout { Spacing = 10 };
                var items = b.Items ?? [];
                for (var i = 0; i < items.Count; i++)
                {
                    var fila = new Grid { ColumnDefinitions = [new ColumnDefinition(36), new ColumnDefinition(GridLength.Star)], ColumnSpacing = 8 };
                    fila.Add(new Label { Text = b.Ordenada == true ? $"{i + 1}." : "•", FontSize = 20 * Escala, FontAttributes = FontAttributes.Bold, TextColor = Ds.Rojo }, 0, 0);
                    fila.Add(Ds.ConTramos(b.ItemsTramos is not null && i < b.ItemsTramos.Count ? b.ItemsTramos[i] : null, items[i], 20 * Escala), 1, 0);
                    pila.Add(fila);
                }
                return pila;
            }
            case "formula":
            {
                // Sin motor matemático en la tableta: el backend entrega una lectura del LaTeX («1/3 × 2») en `texto`.
                var pila = new VerticalStackLayout { Spacing = 6 };
                pila.Add(new Border
                {
                    BackgroundColor = Ds.Lienzo, StrokeThickness = 0, Padding = new Thickness(24, 14), HorizontalOptions = LayoutOptions.Center,
                    StrokeShape = new RoundRectangle { CornerRadius = Ds.RadioInterno },
                    Content = new Label { Text = b.Texto, FontSize = 28 * Escala, FontAttributes = FontAttributes.Italic, TextColor = Ds.Tinta, HorizontalTextAlignment = TextAlignment.Center },
                });
                if (!string.IsNullOrWhiteSpace(b.Pie)) pila.Add(Ds.Secundario(b.Pie!, 15 * Escala));
                return pila;
            }
            case "imagen":
                return Imagen(b);
            case "video":
                return Video(b);
            case "audio":
                return Audio(b);
            case "pdf":
                return Pdf(b);
            default:
                return Ds.Alerta_("Bloque sin visor", $"Tipo «{b.Tipo}».", Ds.AlertaSuave, Ds.Tinta);
        }
    }

    private View Imagen(BloqueAula b)
    {
        var pila = new VerticalStackLayout { Spacing = 8 };
        var marco = new Border
        {
            StrokeThickness = 0, BackgroundColor = Ds.Lienzo, StrokeShape = new RoundRectangle { CornerRadius = Ds.RadioTarjeta },
            HeightRequest = 360 * Escala,
        };
        if (Absoluta is not null && !string.IsNullOrWhiteSpace(b.Url))
        {
            var imagen = new Image { Aspect = Aspect.AspectFit, Source = new UriImageSource { Uri = Absoluta(b.Url!), CachingEnabled = false } };
            if (!string.IsNullOrWhiteSpace(b.TextoAlternativo)) SemanticProperties.SetDescription(imagen, b.TextoAlternativo);
            marco.Content = imagen;
        }
        pila.Add(marco);
        if (!string.IsNullOrWhiteSpace(b.Pie)) pila.Add(Ds.Secundario(b.Pie!, 16 * Escala));
        return pila;
    }

    private View Video(BloqueAula b)
    {
        var pila = new VerticalStackLayout { Spacing = 8 };
        if (Absoluta is null || string.IsNullOrWhiteSpace(b.Url))
            return Ds.Alerta_("Video no disponible", b.Pie, Ds.InfoSuave, Ds.Tinta);
        var url = Absoluta(b.Url!).AbsoluteUri;
        var fragmento = b.DesdeSeg is not null || b.HastaSeg is not null ? $"#t={b.DesdeSeg ?? 0},{(b.HastaSeg is null ? string.Empty : b.HastaSeg.Value.ToString(System.Globalization.CultureInfo.InvariantCulture))}" : string.Empty;
        var pista = !string.IsNullOrWhiteSpace(b.SubtitulosUrl) ? $"<track kind=\"subtitles\" srclang=\"es\" label=\"Español\" src=\"{Absoluta(b.SubtitulosUrl!).AbsoluteUri}\" default>" : string.Empty;
        var html = $$$"""
            <!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
            <style>html,body{margin:0;height:100%;background:#111;color:#fff;font-family:Segoe UI,Arial,sans-serif;display:flex;flex-direction:column}
            video{flex:1;width:100%;background:#000;outline:none}.aviso{display:none;flex:1;align-items:center;justify-content:center;padding:24px;text-align:center;font-size:20px}</style></head>
            <body><video id="v" controls {{{(b.Autoplay == true ? "autoplay" : "")}}} playsinline preload="metadata" src="{{{url}}}{{{fragmento}}}">{{{pista}}}</video>
            <div class="aviso" id="a">Este video no está en el equipo del aula todavía.<br>Lo servirá AVACOM Biblioteca.</div>
            <script>var v=document.getElementById('v');var fin={{{(b.HastaSeg is null ? "null" : b.HastaSeg.Value.ToString(System.Globalization.CultureInfo.InvariantCulture))}}};
            v.addEventListener('error',function(){v.style.display='none';document.getElementById('a').style.display='flex';});
            v.addEventListener('timeupdate',function(){if(fin!==null&&v.currentTime>=fin){v.pause();}});</script></body></html>
            """;
        pila.Add(Web(html, 320 * Escala));
        if (!string.IsNullOrWhiteSpace(b.Pie)) pila.Add(Ds.Secundario(b.Pie!, 16 * Escala));
        var detalle = string.Join(" · ", new[]
        {
            b.DesdeSeg is not null ? $"desde {Mmss(b.DesdeSeg.Value)}" : null,
            b.HastaSeg is not null ? $"hasta {Mmss(b.HastaSeg.Value)}" : null,
            !string.IsNullOrWhiteSpace(b.SubtitulosUrl) ? "con subtítulos" : null,
        }.Where(x => x is not null));
        if (detalle.Length > 0) pila.Add(Ds.Pildora(detalle, Ds.CatVideo));
        return pila;
    }

    private View Audio(BloqueAula b)
    {
        var pila = new VerticalStackLayout { Spacing = 8 };
        if (Absoluta is null || string.IsNullOrWhiteSpace(b.Url))
            return Ds.Alerta_("Audio no disponible", b.Pie, Ds.PeligroSuave, Ds.Tinta);
        var html = $$"""
            <!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;background:#FAFAFA;display:flex;align-items:center;justify-content:center}
            audio{width:96%;height:56px}</style></head><body><audio controls preload="metadata" src="{{Absoluta(b.Url!).AbsoluteUri}}"></audio></body></html>
            """;
        var fila = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star)], ColumnSpacing = 14 };
        fila.Add(Ds.IconoCategoria("audio", 56), 0, 0);
        fila.Add(Web(html, 72), 1, 0);
        pila.Add(Ds.Tarjeta(fila, Ds.RadioInterno, new Thickness(14)));
        if (!string.IsNullOrWhiteSpace(b.Pie)) pila.Add(Ds.Secundario(b.Pie!, 16 * Escala));
        if (b.DuracionSeg is > 0) pila.Add(Ds.Pildora($"Audio · {Mmss(b.DuracionSeg.Value)}", Ds.CatAudio));
        return pila;
    }

    private View Pdf(BloqueAula b)
    {
        var pila = new VerticalStackLayout { Spacing = 8 };
        var rango = b.DesdePagina is not null ? $"Páginas {b.DesdePagina}–{b.HastaPagina ?? b.Paginas}{(b.Paginas is not null ? $" de {b.Paginas}" : string.Empty)}" : "Documento";
        var cabecera = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 12 };
        cabecera.Add(Ds.IconoCategoria("pdf", 44), 0, 0);
        cabecera.Add(new VerticalStackLayout { Children = { Ds.Cuerpo(b.Titulo ?? "Documento", 17 * Escala), Ds.Secundario(rango, 14 * Escala) }, VerticalOptions = LayoutOptions.Center }, 1, 0);
        pila.Add(cabecera);
        if (Absoluta is not null && !string.IsNullOrWhiteSpace(b.Url))
        {
            var destino = Absoluta(b.UrlPaginaInicial ?? b.Url!);
            if (DeviceInfo.Platform == DevicePlatform.Android)
            {
                var abrir = Ds.Boton("Abrir el documento", Ds.Rango.Secondary, async (_, _) => await Launcher.Default.OpenAsync(destino));
                cabecera.Add(abrir, 2, 0);
            }
            else
            {
                pila.Add(Web(destino, 520 * Escala));
            }
        }
        if (!string.IsNullOrWhiteSpace(b.Pie)) pila.Add(Ds.Secundario(b.Pie!, 16 * Escala));
        return pila;
    }

    // ------------------------------------------------------------- laboratorio

    private View Laboratorio(ObjetoAula o)
    {
        var raiz = new Grid { RowDefinitions = [new RowDefinition(GridLength.Auto), new RowDefinition(GridLength.Star)], RowSpacing = 12 };
        var cab = new VerticalStackLayout { Spacing = 8 };
        var titulo = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 12 };
        titulo.Add(Ds.IconoCategoria("laboratorio_web", 44), 0, 0);
        titulo.Add(new VerticalStackLayout { VerticalOptions = LayoutOptions.Center, Children = { Ds.Titulo(o.Titulo, 22 * Escala), Ds.Secundario(o.ObjetivoAprendizaje ?? string.Empty, 15 * Escala) } }, 1, 0);
        titulo.Add(Ds.Pildora("Laboratorio", Ds.CatVideo), 2, 0);
        cab.Add(titulo);
        if (!string.IsNullOrWhiteSpace(o.Instrucciones)) cab.Add(Ds.ConTramos(o.InstruccionesTramos, o.Instrucciones, 17 * Escala));
        if (o.Pasos is { Count: > 0 })
        {
            var pasos = new HorizontalStackLayout { Spacing = 8 };
            for (var i = 0; i < o.Pasos.Count; i++) pasos.Add(Ds.Pildora($"{i + 1}. {o.Pasos[i]}", Ds.Lienzo, Ds.Tinta, 13));
            cab.Add(new ScrollView { Orientation = ScrollOrientation.Horizontal, HorizontalScrollBarVisibility = ScrollBarVisibility.Never, Content = pasos });
        }
        raiz.Add(Ds.Tarjeta(cab, Ds.RadioTarjeta, new Thickness(18, 14)), 0, 0);

        var sim = o.Simulacion?.Simulacion;
        if (Absoluta is null || string.IsNullOrWhiteSpace(o.UrlLanzamiento))
            raiz.Add(Ds.Alerta_("La simulación no tiene dirección de lanzamiento", null, Ds.AlertaSuave, Ds.Tinta), 0, 1);
        else if (sim is not null && !sim.SirveEnTableta && DeviceInfo.Idiom != DeviceIdiom.Desktop)
            raiz.Add(Ds.Alerta_("Esta simulación se ve en la pantalla del aula", "El paquete no la publica para tableta.", Ds.InfoSuave, Ds.Tinta), 0, 1);
        else
        {
            var marco = new Border
            {
                StrokeThickness = 0, BackgroundColor = Color.FromArgb("#101014"), StrokeShape = new RoundRectangle { CornerRadius = Ds.RadioTarjeta },
                Content = Web(Absoluta(o.UrlLanzamiento!), null),
            };
            raiz.Add(marco, 0, 1);
        }
        var licencia = o.Simulacion?.Licencia;
        if (licencia is not null && !string.IsNullOrWhiteSpace(licencia.Atribucion))
        {
            raiz.RowDefinitions.Add(new RowDefinition(GridLength.Auto));
            raiz.Add(Ds.Secundario(licencia.Atribucion!, 12), 0, 2);
        }
        return raiz;
    }

    // ---------------------------------------------------------------- actividad

    private View Actividad(ObjetoAula o)
    {
        var pila = new VerticalStackLayout { Spacing = 14, Padding = new Thickness(0, 0, 0, 24) };
        var cab = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 12 };
        cab.Add(Ds.IconoCategoria("actividad", 44), 0, 0);
        cab.Add(new VerticalStackLayout { VerticalOptions = LayoutOptions.Center, Children = { Ds.Titulo(o.Titulo, 22 * Escala), Ds.Secundario(o.Instrucciones ?? string.Empty, 15 * Escala) } }, 1, 0);
        cab.Add(Ds.Pildora($"{o.Preguntas?.Count ?? 0} preguntas · {o.PuntosTotales ?? 0} pts", Ds.CatQuiz), 2, 0);
        pila.Add(Ds.Tarjeta(cab, Ds.RadioTarjeta, new Thickness(18, 14)));
        if (o.Ajustes is not null)
        {
            var chips = new HorizontalStackLayout { Spacing = 8 };
            chips.Add(Ds.Pildora(o.Ajustes.Retroalimentacion == "immediate" ? "Retroalimentación inmediata" : "Retroalimentación al final", Ds.Lienzo, Ds.Tinta));
            if (o.Ajustes.IntentosPermitidos is > 0) chips.Add(Ds.Pildora($"{o.Ajustes.IntentosPermitidos} intento(s)", Ds.Lienzo, Ds.Tinta));
            if (o.Ajustes.BarajarOpciones) chips.Add(Ds.Pildora("Opciones barajadas", Ds.Lienzo, Ds.Tinta));
            pila.Add(chips);
        }
        var n = 0;
        foreach (var p in o.Preguntas ?? [])
        {
            n++;
            var contenido = new VerticalStackLayout { Spacing = 10 };
            var fila = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 10 };
            fila.Add(Ds.Pildora(n.ToString(), Ds.CatQuiz), 0, 0);
            fila.Add(Ds.ConTramos(p.EnunciadoTramos, p.Enunciado, 19 * Escala), 1, 0);
            fila.Add(Ds.Secundario($"{p.TipoLegible} · {p.Puntos ?? 0} pt", 13), 2, 0);
            contenido.Add(fila);
            contenido.Add(Pregunta(p));
            pila.Add(Ds.Tarjeta(contenido, Ds.RadioTarjeta, new Thickness(18, 16)));
        }
        pila.Add(Ds.Secundario("Vista previa: las respuestas se envían desde la tableta del alumno y las corrige la biblioteca. Aquí no hay claves.", 13));
        return pila;
    }

    private View Pregunta(PreguntaAula p)
    {
        switch (p.Componente)
        {
            case "opcion_multiple":
            case "verdadero_falso":
            {
                var pila = new VerticalStackLayout { Spacing = 8 };
                foreach (var op in p.Opciones ?? [])
                {
                    var fila = new Grid { ColumnDefinitions = [new ColumnDefinition(28), new ColumnDefinition(GridLength.Star)], ColumnSpacing = 10, Padding = new Thickness(6, 4) };
                    fila.Add(new BoxView { WidthRequest = 22, HeightRequest = 22, CornerRadius = p.PermiteVarias == true ? 6 : 11, Color = Colors.Transparent, }, 0, 0);
                    ((BoxView)fila.Children[0]).Color = Ds.Lienzo;
                    fila.Add(Ds.ConTramos(op.Tramos, op.Texto, 17 * Escala), 1, 0);
                    pila.Add(fila);
                }
                return pila;
            }
            case "completar":
            {
                var texto = p.Plantilla ?? string.Empty;
                foreach (var e in p.Espacios ?? [])
                    texto = texto.Replace("{{" + e.EspacioRef + "}}", e.Opciones is { Count: > 0 } ? $"[ {string.Join(" / ", e.Opciones)} ]" : "[ ______ ]");
                return Ds.Cuerpo(texto, 17 * Escala);
            }
            case "relacionar":
            {
                var g = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Star)], ColumnSpacing = 16 };
                var izq = new VerticalStackLayout { Spacing = 6 }; var der = new VerticalStackLayout { Spacing = 6 };
                foreach (var e in p.Izquierda ?? []) izq.Add(Ds.Pildora(e.Texto ?? e.Ref, Ds.Lienzo, Ds.Tinta, 15));
                foreach (var e in p.Derecha ?? []) der.Add(Ds.Pildora(e.Texto ?? e.Ref, Ds.InfoSuave, Ds.Tinta, 15));
                g.Add(izq, 0, 0); g.Add(der, 1, 0);
                return g;
            }
            case "ordenar":
            {
                var pila = new VerticalStackLayout { Spacing = 6 };
                foreach (var e in p.Elementos ?? []) pila.Add(Ds.Pildora($"↕  {e.Texto ?? e.Ref}", Ds.Lienzo, Ds.Tinta, 15));
                return pila;
            }
            case "abierta":
                return new Border
                {
                    BackgroundColor = Ds.Lienzo, StrokeThickness = 0, StrokeShape = new RoundRectangle { CornerRadius = Ds.RadioInterno }, Padding = new Thickness(16, 20),
                    Content = Ds.Secundario($"Respuesta escrita{(p.LongitudMaxima is > 0 ? $" · hasta {p.LongitudMaxima} caracteres" : string.Empty)} · la califica el docente", 14),
                };
            default:
                return Ds.Secundario($"Tipo de pregunta «{p.Tipo}» sin visor.", 14);
        }
    }

    private View FueraDeAlcance(ObjetoAula o)
    {
        var pila = new VerticalStackLayout { Spacing = 10, Opacity = 0.75 };
        var cab = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star)], ColumnSpacing = 12 };
        cab.Add(Ds.IconoCategoria("examen", 44), 0, 0);
        cab.Add(new VerticalStackLayout { VerticalOptions = LayoutOptions.Center, Children = { Ds.Titulo(o.Titulo, 22 * Escala), Ds.Secundario($"Lo aplica el módulo de evaluación ({o.Modulo ?? "MOD-010"}). El aula lo muestra, no lo ejecuta.", 15 * Escala) } }, 1, 0);
        pila.Add(cab);
        if (o.TotalPreguntasBanco is > 0) pila.Add(Ds.Pildora($"Banco de {o.TotalPreguntasBanco} preguntas", Ds.Lienzo, Ds.Tinta));
        if (!string.IsNullOrWhiteSpace(o.Instrucciones)) pila.Add(Ds.Secundario(o.Instrucciones!, 15 * Escala));
        return Ds.Tarjeta(pila);
    }

    // ------------------------------------------------------------------ webview

    private WebView Web(string html, double? alto)
    {
        var web = NuevaWeb(alto);
        _hostPermitido = null; // HTML propio: sólo se permite el host del backend, que se fija al conocer la primera URL absoluta
        if (Absoluta is not null) _hostPermitido = Absoluta("/").GetLeftPart(UriPartial.Authority);
        web.Source = new HtmlWebViewSource { Html = html };
        return web;
    }

    private WebView Web(Uri url, double? alto)
    {
        var web = NuevaWeb(alto);
        _hostPermitido = url.GetLeftPart(UriPartial.Authority);
        web.Source = new UrlWebViewSource { Url = url.AbsoluteUri };
        return web;
    }

    private WebView NuevaWeb(double? alto)
    {
        LimpiarWeb();
        var web = new WebView();
        if (alto is not null) web.HeightRequest = alto.Value;
        web.Navigating += (_, e) =>
        {
            // block_network: la WebView sólo navega al host del backend del LMS. El aula no tiene internet
            // y una simulación que intente salir simplemente no navega.
            if (_hostPermitido is null || !Uri.TryCreate(e.Url, UriKind.Absolute, out var uri)) return;
            if (uri.Scheme is "about" or "data" or "blob") return;
            if (!string.Equals(uri.GetLeftPart(UriPartial.Authority), _hostPermitido, StringComparison.OrdinalIgnoreCase)) e.Cancel = true;
        };
        _web = web;
        return web;
    }

    private void LimpiarWeb()
    {
        if (_web is null) return;
        try { _web.Source = new HtmlWebViewSource { Html = "<html><body></body></html>" }; } catch { }
        _web = null;
    }

    private static string Mmss(double seg) => $"{(int)seg / 60}:{(int)seg % 60:00}";

    public static string HtmlEscapar(string s) => WebUtility.HtmlEncode(s);
}
