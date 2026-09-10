using Avacom.Lms.Core.Models;
using Microsoft.Maui.Controls.Shapes;

namespace Avacom.Lms.Ops.Pages;

/// <summary>
/// Un curso de AVACOM Biblioteca visto por el docente: el contenido completo
/// (reproducible aquí o proyectable en el aula) y el consolidado de progreso de
/// los estudiantes, que es lo único que este LMS posee.
/// </summary>
[QueryProperty(nameof(CursoRef), "curso")]
[QueryProperty(nameof(Titulo), "titulo")]
public partial class CursoBibliotecaPage : ContentPage
{
    public string CursoRef { get; set; } = string.Empty;
    public string Titulo { get; set; } = string.Empty;

    public CursoBibliotecaPage() => InitializeComponent();

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        TituloLabel.Text = string.IsNullOrWhiteSpace(Titulo) ? CursoRef : Titulo;
        Contenido.Configurar(Sesion.Biblioteca, CursoRef, personaId: null, personaRotulo: null, dispositivo: Sesion.Dispositivo);
        Contenido.CursoCargado += (_, curso) =>
        {
            TituloLabel.Text = curso.Titulo;
            ResumenLabel.Text = $"{curso.Secciones.Count} secciones · {curso.TotalItems} materiales · versión {curso.Version}";
        };
        await Contenido.CargarAsync();
    }

    protected override async void OnDisappearing()
    {
        base.OnDisappearing();
        await Contenido.CerrarTodoAsync();
    }

    private void OnTabContenido(object? sender, EventArgs e) => MostrarTab(contenido: true);

    private async void OnTabEstudiantes(object? sender, EventArgs e)
    {
        MostrarTab(contenido: false);
        await CargarEstudiantesAsync();
    }

    private void MostrarTab(bool contenido)
    {
        Contenido.IsVisible = contenido;
        PanelEstudiantes.IsVisible = !contenido;
        TabContenido.BackgroundColor = Color.FromArgb(contenido ? "#18181B" : "#FFFFFF");
        TabContenido.TextColor = Color.FromArgb(contenido ? "#FFFFFF" : "#18181B");
        TabEstudiantes.BackgroundColor = Color.FromArgb(contenido ? "#FFFFFF" : "#18181B");
        TabEstudiantes.TextColor = Color.FromArgb(contenido ? "#18181B" : "#FFFFFF");
    }

    private async void OnActualizarEstudiantes(object? sender, EventArgs e) => await CargarEstudiantesAsync();

    private async Task CargarEstudiantesAsync()
    {
        var consolidado = await Sesion.Biblioteca.ConsolidadoAsync(CursoRef);
        EstudiantesHost.Clear();
        if (consolidado is null)
        {
            SinEstudiantes.IsVisible = true;
            SinEstudiantes.Text = Sesion.Biblioteca.UltimoMotivo ?? "No se pudo leer el consolidado.";
            return;
        }
        KpiEstudiantes.Text = consolidado.Resumen.Estudiantes.ToString();
        KpiProgreso.Text = $"{consolidado.Resumen.PromedioProgreso:0}%";
        KpiAperturas.Text = consolidado.Resumen.Aperturas.ToString();
        KpiIntentos.Text = consolidado.Resumen.IntentosFinalizados.ToString();
        SinEstudiantes.IsVisible = consolidado.Estudiantes.Count == 0;
        SinEstudiantes.Text = "Todavía ningún estudiante ha abierto este curso.";
        foreach (var estudiante in consolidado.Estudiantes)
            EstudiantesHost.Add(FilaEstudiante(estudiante));
    }

    private View FilaEstudiante(EstudianteConsolidado e)
    {
        var grid = new Grid
        {
            ColumnDefinitions = [new ColumnDefinition(54), new ColumnDefinition(new GridLength(2, GridUnitType.Star)), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)],
            ColumnSpacing = 14,
        };
        grid.Add(new Border
        {
            BackgroundColor = Color.FromArgb("#3F3F46"), WidthRequest = 44, HeightRequest = 44, StrokeThickness = 0,
            StrokeShape = new RoundRectangle { CornerRadius = 22 },
            Content = new Label { Text = e.Iniciales, TextColor = Colors.White, FontAttributes = FontAttributes.Bold, HorizontalOptions = LayoutOptions.Center, VerticalOptions = LayoutOptions.Center },
        }, 0, 0);
        var nombre = new VerticalStackLayout { VerticalOptions = LayoutOptions.Center };
        nombre.Add(new Label { Text = e.PersonaRotulo, FontAttributes = FontAttributes.Bold });
        nombre.Add(new Label { Text = $"Última actividad {e.UltimaActividadTexto} · {e.Aperturas} materiales · {e.TiempoTexto}", Style = Estilo("Muted") });
        grid.Add(nombre, 1, 0);
        var progreso = new VerticalStackLayout { VerticalOptions = LayoutOptions.Center, Spacing = 4 };
        progreso.Add(new Label { Text = $"Progreso {e.ProgresoTexto}", Style = Estilo("Muted") });
        progreso.Add(new ProgressBar { Progress = e.ProgresoFraccion, ProgressColor = Color.FromArgb("#E5262B") });
        grid.Add(progreso, 2, 0);
        grid.Add(new Label { Text = e.NotasTexto, Style = Estilo("Muted"), VerticalOptions = LayoutOptions.Center, LineBreakMode = LineBreakMode.WordWrap }, 3, 0);
        grid.Add(new Label { Text = e.Notas.FirstOrDefault(n => n.Puntaje is not null) is { } n ? $"{n.Puntaje:0}/100" : "—", FontAttributes = FontAttributes.Bold, TextColor = Color.FromArgb("#019D60"), VerticalTextAlignment = TextAlignment.Center }, 4, 0);
        return new Border { Padding = 18, Content = grid };
    }

    private async void OnBack(object? sender, EventArgs e) => await Shell.Current.GoToAsync("..");

    /// <summary>Los estilos viven en Application.Resources; Resources de la página no los ve desde código.</summary>
    private static Style Estilo(string clave) =>
        Application.Current?.Resources.TryGetValue(clave, out var valor) == true && valor is Style estilo ? estilo : new Style(typeof(View));
}
