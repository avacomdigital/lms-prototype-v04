namespace Avacom.Lms.Student.Pages;

/// <summary>
/// Un curso de AVACOM Biblioteca visto por el estudiante: toda su jerarquía y su
/// contenido reproducible, con el avance registrado en el backend del LMS.
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
        Contenido.Configurar(Sesion.Biblioteca, CursoRef, Sesion.PersonaId, Sesion.Nombre, Sesion.Dispositivo);
        Contenido.CursoCargado += (_, curso) => TituloLabel.Text = curso.Titulo;
        Contenido.ProgresoCambiado += (_, progreso) => ProgresoChip.Text = $"{progreso:0}% completado";
        await Contenido.CargarAsync();
    }

    protected override async void OnDisappearing()
    {
        base.OnDisappearing();
        await Contenido.CerrarTodoAsync();
    }

    private async void OnBack(object? sender, EventArgs e) => await Shell.Current.GoToAsync("..");
}
