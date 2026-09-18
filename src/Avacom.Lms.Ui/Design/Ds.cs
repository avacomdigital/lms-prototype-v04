using Avacom.Lms.Core.Models;
using Microsoft.Maui.Controls.Shapes;

namespace Avacom.Lms.Ui.Design;

/// <summary>
/// Tokens y fábricas del Avacom LMS UI Kit v2 para las pantallas del aula (MOD-007).
///
/// Tres materiales: <b>content surface</b> (blanco 96 %, sin desenfoque, sombra doble
/// suave) para todo lo que se lee; <b>glass chrome</b> (blanco 70 %) sólo para barras y
/// navegación; <b>dark glass</b> (casi negro 82 %) para la barra de controles multimedia.
/// MAUI no ofrece desenfoque de fondo en WinUI/Android sin código de plataforma, así que el
/// vidrio se aproxima con la transparencia y un filo de 1 px; los párrafos nunca van sobre él.
///
/// Botones: 64 px de alto, radio 16, etiqueta 20/600. Un solo Primary por pantalla.
/// Neumorfismo: luz arriba-izquierda; el control se hunde (escala + desplazamiento) al pulsar.
/// </summary>
public static class Ds
{
    // ------------------------------------------------------------------ color
    public static readonly Color Rojo = Color.FromArgb("#E5262B");        // marca · Primary · Audio
    public static readonly Color Tinta = Color.FromArgb("#18181B");
    public static readonly Color TintaSuave = Color.FromArgb("#52525B");
    public static readonly Color TintaMedia = Color.FromArgb("#3F3F46");
    public static readonly Color Lienzo = Color.FromArgb("#F1F1F1");
    public static readonly Color Filo = Color.FromArgb("#17000000");       // hairline 9 % negro
    public static readonly Color Exito = Color.FromArgb("#019D60");
    public static readonly Color Info = Color.FromArgb("#01A4E1");
    public static readonly Color Alerta = Color.FromArgb("#F3C701");
    public static readonly Color Peligro = Color.FromArgb("#C82230");
    public static readonly Color ExitoSuave = Color.FromArgb("#E6F5EE");
    public static readonly Color InfoSuave = Color.FromArgb("#E6F6FC");
    public static readonly Color AlertaSuave = Color.FromArgb("#FEF9E6");
    public static readonly Color PeligroSuave = Color.FromArgb("#FDECEC");
    public static readonly Color VioletaSuave = Color.FromArgb("#F5E8F1");

    /// <summary>Categorías de contenido del cubo del logo. Identifican; nunca rellenan un CTA.</summary>
    public static readonly Color CatVideo = Color.FromArgb("#01A4E1");     // cyan / azul
    public static readonly Color CatClaseEnVivo = Color.FromArgb("#A81D81"); // magenta / púrpura
    public static readonly Color CatQuiz = Color.FromArgb("#019D60");      // verde
    public static readonly Color CatLectura = Color.FromArgb("#F3C701");   // amarillo
    public static readonly Color CatAudio = Color.FromArgb("#E5262B");     // rojo

    public static readonly Color SuperficieContenido = Color.FromArgb("#F5FFFFFF"); // blanco 96 %
    public static readonly Color GlassChrome = Color.FromArgb("#B3FFFFFF");         // blanco 70 %
    public static readonly Color GlassOscuro = Color.FromArgb("#D1141417");          // casi negro 82 %

    // ----------------------------------------------------------------- radios
    public const int RadioControl = 12, RadioInterno = 14, RadioBoton = 16, RadioTarjeta = 20, RadioBarra = 22, RadioGrande = 24, RadioPildora = 999;

    // ------------------------------------------------------------- categorías
    /// <summary>Color de categoría de un objeto o bloque, por su <c>componente</c>.</summary>
    public static Color Categoria(string? componente) => componente switch
    {
        "presentacion" => CatClaseEnVivo,
        "lectura" or "texto" or "titulo" or "lista" or "pdf" => CatLectura,
        "laboratorio_web" or "webview" or "video" or "imagen" => CatVideo,
        "actividad" or "opcion_multiple" or "verdadero_falso" or "completar" or "relacionar" or "ordenar" or "abierta" => CatQuiz,
        "audio" => CatAudio,
        "examen" => TintaSuave,
        _ => TintaSuave,
    };

    /// <summary>La categoría amarilla necesita tinta oscura encima; las demás, blanca.</summary>
    public static Color TintaSobre(Color fondo) => fondo == CatLectura || fondo == Alerta ? Tinta : Colors.White;

    public static string Icono(string? componente) => componente switch
    {
        "presentacion" => "▣",
        "lectura" or "pdf" => "▤",
        "laboratorio_web" or "webview" => "⌗",
        "actividad" => "✎",
        "examen" => "✓",
        "video" => "▶",
        "audio" => "♪",
        "imagen" => "▧",
        _ => "•",
    };

    // ---------------------------------------------------------------- sombras
    public static Shadow SombraTarjeta() => new() { Brush = new SolidColorBrush(Tinta), Offset = new Point(0, 10), Radius = 26, Opacity = 0.07f };
    public static Shadow SombraElevada() => new() { Brush = new SolidColorBrush(Tinta), Offset = new Point(6, 8), Radius = 14, Opacity = 0.14f };
    public static Shadow SombraLuz() => new() { Brush = new SolidColorBrush(Colors.White), Offset = new Point(-5, -5), Radius = 12, Opacity = 0.9f };

    // ------------------------------------------------------------- superficies
    /// <summary>Content surface: blanco 96 %, filo de 9 % y sombra doble suave. Aquí va todo lo que se lee.</summary>
    public static Border Tarjeta(View contenido, int radio = RadioTarjeta, Thickness? relleno = null, Color? fondo = null)
    {
        var borde = new Border
        {
            BackgroundColor = fondo ?? SuperficieContenido,
            Stroke = new SolidColorBrush(Filo),
            StrokeThickness = 1,
            StrokeShape = new RoundRectangle { CornerRadius = radio },
            Padding = relleno ?? new Thickness(20),
            Content = contenido,
            Shadow = SombraTarjeta(),
        };
        return borde;
    }

    /// <summary>Glass chrome: sólo barras y navegación, etiquetas cortas.</summary>
    public static Border BarraClara(View contenido, Thickness? relleno = null) => new()
    {
        BackgroundColor = GlassChrome,
        Stroke = new SolidColorBrush(Filo),
        StrokeThickness = 1,
        StrokeShape = new RoundRectangle { CornerRadius = RadioBarra },
        Padding = relleno ?? new Thickness(18, 10),
        Content = contenido,
        Shadow = new Shadow { Brush = new SolidColorBrush(Tinta), Offset = new Point(0, 4), Radius = 16, Opacity = 0.08f },
    };

    /// <summary>Dark glass: la barra de controles de la clase y los mandos multimedia.</summary>
    public static Border BarraOscura(View contenido, Thickness? relleno = null) => new()
    {
        BackgroundColor = GlassOscuro,
        StrokeThickness = 0,
        StrokeShape = new RoundRectangle { CornerRadius = RadioBarra },
        Padding = relleno ?? new Thickness(16, 10),
        Content = contenido,
        Shadow = new Shadow { Brush = new SolidColorBrush(Tinta), Offset = new Point(0, 8), Radius = 20, Opacity = 0.22f },
    };

    // ---------------------------------------------------------------- botones
    public enum Rango { Primary, Secondary, Quiet, Destructive }

    /// <summary>Botón del kit: 64 px, radio 16, 20/600, relieve neumórfico y hundimiento al pulsar.</summary>
    public static Button Boton(string texto, Rango rango, EventHandler? alPulsar = null, double alto = 64, double? ancho = null)
    {
        var boton = new Button
        {
            Text = texto,
            HeightRequest = alto,
            MinimumHeightRequest = alto,
            CornerRadius = RadioBoton,
            FontSize = alto >= 64 ? 20 : 17,
            FontAttributes = FontAttributes.Bold,
            Padding = new Thickness(22, 0),
            BorderWidth = rango == Rango.Secondary ? 1 : 0,
            BorderColor = Filo,
        };
        if (ancho is not null) boton.WidthRequest = ancho.Value;
        switch (rango)
        {
            case Rango.Primary:
                boton.BackgroundColor = Rojo; boton.TextColor = Colors.White; boton.Shadow = SombraElevada(); break;
            case Rango.Secondary:
                boton.BackgroundColor = Colors.White; boton.TextColor = Tinta; boton.Shadow = SombraElevada(); break;
            case Rango.Quiet:
                boton.BackgroundColor = Colors.Transparent; boton.TextColor = Color.FromArgb("#27272A"); break;
            case Rango.Destructive:
                boton.BackgroundColor = Peligro; boton.TextColor = Colors.White; boton.Shadow = SombraElevada(); break;
        }
        Hundir(boton);
        if (alPulsar is not null) boton.Clicked += alPulsar;
        return boton;
    }

    /// <summary>El botón no «baja»: se hunde en la superficie (escala 0,96 y la sombra se recoge) en menos de 120 ms.</summary>
    public static void Hundir(Button boton)
    {
        var sombra = boton.Shadow;
        boton.Pressed += async (_, _) =>
        {
            if (sombra is not null) boton.Shadow = new Shadow { Brush = sombra.Brush, Offset = new Point(2, 3), Radius = 6, Opacity = 0.18f };
            await boton.ScaleToAsync(0.96, 90, Easing.CubicOut);
        };
        boton.Released += async (_, _) =>
        {
            await boton.ScaleToAsync(1, 140, Easing.CubicOut);
            if (sombra is not null) boton.Shadow = sombra;
        };
    }

    /// <summary>Interruptor grande tocable para la barra de controles (dark glass): dos estados con color semántico.</summary>
    public static Button Interruptor(string texto, bool activo, Color activoColor, EventHandler alPulsar)
    {
        var b = new Button
        {
            Text = texto,
            HeightRequest = 64,
            MinimumHeightRequest = 64,
            CornerRadius = RadioBoton,
            FontSize = 17,
            FontAttributes = FontAttributes.Bold,
            Padding = new Thickness(18, 0),
        };
        PintarInterruptor(b, activo, activoColor);
        Hundir(b);
        b.Clicked += alPulsar;
        return b;
    }

    public static void PintarInterruptor(Button b, bool activo, Color activoColor)
    {
        b.BackgroundColor = activo ? activoColor : Color.FromArgb("#33FFFFFF");
        b.TextColor = activo ? TintaSobre(activoColor) : Colors.White;
    }

    // ----------------------------------------------------------------- textos
    public static Label Titulo(string texto, double tamano = 26, Color? color = null) => new()
    {
        Text = texto, FontSize = tamano, FontAttributes = FontAttributes.Bold, TextColor = color ?? Tinta, LineBreakMode = LineBreakMode.WordWrap,
    };

    public static Label Cuerpo(string texto, double tamano = 18, Color? color = null) => new()
    {
        Text = texto, FontSize = tamano, TextColor = color ?? Tinta, LineBreakMode = LineBreakMode.WordWrap,
    };

    public static Label Secundario(string texto, double tamano = 16) => new()
    {
        Text = texto, FontSize = tamano, TextColor = TintaSuave, LineBreakMode = LineBreakMode.WordWrap,
    };

    /// <summary>Los tramos (`**negrita**`) del manifiesto → FormattedString. Sin Markdown en la tableta.</summary>
    public static FormattedString Formateado(IReadOnlyList<Tramo>? tramos, string? plano)
    {
        var fs = new FormattedString();
        if (tramos is null || tramos.Count == 0)
        {
            fs.Spans.Add(new Span { Text = plano ?? string.Empty });
            return fs;
        }
        foreach (var t in tramos)
            fs.Spans.Add(new Span { Text = t.Texto, FontAttributes = t.Negrita ? FontAttributes.Bold : FontAttributes.None });
        return fs;
    }

    public static Label ConTramos(IReadOnlyList<Tramo>? tramos, string? plano, double tamano = 18, Color? color = null) => new()
    {
        FormattedText = Formateado(tramos, plano), FontSize = tamano, TextColor = color ?? Tinta, LineBreakMode = LineBreakMode.WordWrap,
    };

    // ---------------------------------------------------------------- píldoras
    /// <summary>Badge de categoría o estado: identifica, no llama a la acción.</summary>
    public static Border Pildora(string texto, Color fondo, Color? tinta = null, double tamano = 13) => new()
    {
        BackgroundColor = fondo,
        StrokeThickness = 0,
        StrokeShape = new RoundRectangle { CornerRadius = RadioPildora },
        Padding = new Thickness(12, 6),
        Content = new Label { Text = texto, FontSize = tamano, FontAttributes = FontAttributes.Bold, TextColor = tinta ?? TintaSobre(fondo) },
        VerticalOptions = LayoutOptions.Center,
    };

    /// <summary>Punto de estado de conexión (CMP-001): conectado, reconectando o sin señal. Sin porcentajes.</summary>
    public static Border PuntoEstado(string texto, Color color) => Pildora($"●  {texto}", Color.FromArgb("#1AFFFFFF"), color, 13);

    /// <summary>Icono de categoría en un cuadrado redondeado (26–34 px).</summary>
    public static Border IconoCategoria(string? componente, double lado = 44)
    {
        var color = Categoria(componente);
        return new Border
        {
            BackgroundColor = color,
            StrokeThickness = 0,
            WidthRequest = lado, HeightRequest = lado,
            StrokeShape = new RoundRectangle { CornerRadius = RadioControl },
            Content = new Label
            {
                Text = Icono(componente), FontSize = lado * 0.5, TextColor = TintaSobre(color), FontAttributes = FontAttributes.Bold,
                HorizontalOptions = LayoutOptions.Center, VerticalOptions = LayoutOptions.Center,
            },
            VerticalOptions = LayoutOptions.Center,
        };
    }

    /// <summary>Alerta no bloqueante (CMP-005): informa, no interrumpe.</summary>
    public static Border Alerta_(string titulo, string? detalle, Color fondo, Color tinta)
    {
        var pila = new VerticalStackLayout { Spacing = 4 };
        pila.Add(new Label { Text = titulo, FontAttributes = FontAttributes.Bold, FontSize = 17, TextColor = tinta, LineBreakMode = LineBreakMode.WordWrap });
        if (!string.IsNullOrWhiteSpace(detalle))
            pila.Add(new Label { Text = detalle, FontSize = 15, TextColor = tinta, LineBreakMode = LineBreakMode.WordWrap });
        return new Border
        {
            BackgroundColor = fondo, StrokeThickness = 0, Padding = new Thickness(18, 14),
            StrokeShape = new RoundRectangle { CornerRadius = RadioInterno }, Content = pila,
        };
    }

    public static Border Separador() => new() { HeightRequest = 1, BackgroundColor = Filo, StrokeThickness = 0 };

    public static void Tocable(View vista, Func<Task> accion)
    {
        var tap = new TapGestureRecognizer();
        tap.Tapped += async (_, _) =>
        {
            await vista.ScaleToAsync(0.97, 70, Easing.CubicOut);
            await vista.ScaleToAsync(1, 110, Easing.CubicOut);
            await accion();
        };
        vista.GestureRecognizers.Add(tap);
    }
}
