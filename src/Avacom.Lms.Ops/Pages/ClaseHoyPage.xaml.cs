using Avacom.Lms.Core.Models;
using Avacom.Lms.Ui.Controls;
using Avacom.Lms.Ui.Design;

namespace Avacom.Lms.Ops.Pages;

/// <summary>
/// P1 · Materias de hoy. Un hexágono por asignatura y, debajo, sus cursos como tarjetas.
/// Con la fuente de ejemplo hay una sola materia: Ciencias naturales. Todo el journey de
/// MOD-007 empieza aquí; nada se escribe en esta pantalla.
/// </summary>
public partial class ClaseHoyPage : ContentPage
{
    private bool _cargando;

    public ClaseHoyPage() => InitializeComponent();

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        await CargarAsync();
    }

    private async Task CargarAsync()
    {
        if (_cargando) return;
        _cargando = true;
        try
        {
            var aula = Sesion.Aula;
            AvisoHost.Clear();
            HexHost.Children.Clear();
            ListaHost.Clear();

            // Una clase quedó abierta en este equipo: ofrecer continuarla antes que nada (BR-051).
            if (Sesion.ClaseAbiertaId is { } abierta)
            {
                var sesion = await aula.SesionAsync(abierta);
                if (sesion is { Activa: true }) AvisoHost.Add(TarjetaContinuar(sesion));
                else if (sesion is not null) Sesion.ClaseAbiertaId = null;
            }

            var catalogo = await aula.CursosAsync();
            if (catalogo is null)
            {
                PintarFuente(false, aula.UltimoMotivo);
                var error = aula.UltimoError;
                var pila = new VerticalStackLayout { Spacing = 12 };
                pila.Add(Ds.Alerta_("No se pudieron leer las materias", string.Join(" ", new[] { error?.Detalle, error?.Sugerencia }.Where(x => !string.IsNullOrWhiteSpace(x))), Ds.PeligroSuave, Color.FromArgb("#8A1C1F")));
                pila.Add(Ds.Boton("Reintentar", Ds.Rango.Secondary, async (_, _) => await CargarAsync(), 64, 220));
                AvisoHost.Add(pila);
                return;
            }

            PintarFuente(true, catalogo.Fuente);
            SubtituloLabel.Text = catalogo.Asignaturas.Count == 1 ? "1 materia asignada" : $"{catalogo.Asignaturas.Count} materias asignadas";
            if (catalogo.Asignaturas.Count == 0)
            {
                ListaHost.Add(Ds.Tarjeta(new VerticalStackLayout
                {
                    Spacing = 6, HorizontalOptions = LayoutOptions.Center,
                    Children = { Ds.Titulo("Nada por aquí todavía", 22), Ds.Secundario("Cuando la escuela asigne una materia en AVACOM Biblioteca, aparecerá aquí.") },
                }));
                return;
            }

            var indice = 0;
            foreach (var asignatura in catalogo.Asignaturas)
            {
                var color = Ds.CatClaseEnVivo;
                var tile = new ProfessorHexTile
                {
                    Text = asignatura.Nombre, AccentColor = color, IconGeometry = Sesion.IconoLibro, Margin = new Thickness(8, 6),
                };
                var seccion = SeccionAsignatura(asignatura, color, indice++);
                tile.Tapped += async (_, _) => await ((ScrollView)ListaHost.Parent.Parent).ScrollToAsync(seccion, ScrollToPosition.Start, true);
                HexHost.Children.Add(tile);
                ListaHost.Add(seccion);
            }
        }
        finally { _cargando = false; }
    }

    private View SeccionAsignatura(AsignaturaAula asignatura, Color color, int indice)
    {
        var pila = new VerticalStackLayout { Spacing = 12 };
        var cabecera = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Auto), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 12 };
        cabecera.Add(Ds.Pildora(asignatura.Nombre, color), 0, 0);
        cabecera.Add(Ds.Secundario(asignatura.Cursos.Count == 1 ? "1 curso" : $"{asignatura.Cursos.Count} cursos", 15), 2, 0);
        pila.Add(cabecera);
        foreach (var curso in asignatura.Cursos) pila.Add(TarjetaCurso(curso, color));
        return pila;
    }

    private View TarjetaCurso(FichaCurso curso, Color color)
    {
        var grid = new Grid
        {
            ColumnDefinitions = [new ColumnDefinition(64), new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)],
            ColumnSpacing = 18,
        };
        grid.Add(Ds.IconoCategoria("presentacion", 64), 0, 0);
        var textos = new VerticalStackLayout { Spacing = 4, VerticalOptions = LayoutOptions.Center };
        textos.Add(Ds.Titulo(curso.Titulo, 22));
        if (!string.IsNullOrWhiteSpace(curso.Subtitulo)) textos.Add(Ds.Secundario(curso.Subtitulo!, 16));
        textos.Add(Ds.Secundario(curso.Detalle, 14));
        grid.Add(textos, 1, 0);
        var abrir = Ds.Boton("Ver lecciones  ›", Ds.Rango.Secondary, async (_, _) => await AbrirAsync(curso), 64, 220);
        abrir.VerticalOptions = LayoutOptions.Center;
        grid.Add(abrir, 2, 0);
        var tarjeta = Ds.Tarjeta(grid, Ds.RadioTarjeta, new Thickness(22, 20));
        Ds.Tocable(tarjeta, () => AbrirAsync(curso));
        return tarjeta;
    }

    private View TarjetaContinuar(SesionDeClase sesion)
    {
        var grid = new Grid { ColumnDefinitions = [new ColumnDefinition(GridLength.Star), new ColumnDefinition(GridLength.Auto)], ColumnSpacing = 16 };
        var textos = new VerticalStackLayout { Spacing = 4, VerticalOptions = LayoutOptions.Center };
        textos.Add(Ds.Pildora(sesion.Estado == "suspendida" ? "Clase suspendida · mismo código" : "Clase abierta", sesion.Estado == "suspendida" ? Ds.Alerta : Ds.CatClaseEnVivo));
        textos.Add(Ds.Titulo(sesion.LeccionRotulo ?? sesion.CursoRotulo ?? "Clase libre", 22));
        textos.Add(Ds.Secundario($"Código {sesion.CodigoUnion} · {sesion.Conteo?.Conectados ?? 0} conectados", 15));
        grid.Add(textos, 0, 0);
        var continuar = Ds.Boton("Continuar la clase", Ds.Rango.Primary, async (_, _) => await Shell.Current.GoToAsync($"clase-sesion?sesion={Uri.EscapeDataString(sesion.Id)}"), 64, 240);
        continuar.VerticalOptions = LayoutOptions.Center;
        grid.Add(continuar, 1, 0);
        return Ds.Tarjeta(grid, Ds.RadioTarjeta, new Thickness(22, 18), Ds.VioletaSuave);
    }

    private void PintarFuente(bool ok, string? detalle)
    {
        FuenteChip.BackgroundColor = ok ? (detalle == "ejemplo" ? Ds.AlertaSuave : Ds.ExitoSuave) : Ds.PeligroSuave;
        FuenteChipLabel.TextColor = ok ? (detalle == "ejemplo" ? Color.FromArgb("#6B5800") : Ds.Exito) : Ds.Peligro;
        FuenteChipLabel.Text = ok
            ? (detalle == "ejemplo" ? "●  Curso de ejemplo · Biblioteca pendiente" : "●  Biblioteca conectada")
            : "●  Sin conexión con el aula";
    }

    private static Task AbrirAsync(FichaCurso curso) =>
        Shell.Current.GoToAsync($"clase-curso?curso={Uri.EscapeDataString(curso.CursoRef)}&titulo={Uri.EscapeDataString(curso.Titulo)}");

    private async void OnVolver(object? sender, EventArgs e) => await Shell.Current.GoToAsync("..");
}
