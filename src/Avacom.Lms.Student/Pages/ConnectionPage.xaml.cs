using Avacom.Lms.Core.Models;
using Avacom.Lms.Core.Services;
namespace Avacom.Lms.Student.Pages;
public partial class ConnectionPage : ContentPage
{
    private readonly ILmsApiClient apiClient = new LmsApiClient(new HttpClient { Timeout = TimeSpan.FromSeconds(3) });
    public ConnectionPage() => InitializeComponent();
    private async void OnCheck(object? sender, EventArgs e)
    {
        CheckButton.IsEnabled = false; StatusLabel.Text = "●  Buscando el aula…";
        try { var ok = await apiClient.CheckHealthAsync(ConnectionOptions.Normalize(ServerEntry.Text ?? string.Empty)); StatusCard.BackgroundColor = Color.FromArgb(ok ? "#E6F5EE" : "#FDECEC"); StatusLabel.TextColor = Color.FromArgb(ok ? "#019D60" : "#E5262B"); StatusLabel.Text = ok ? "●  Conectado al aula correctamente" : "●  No encontramos el aula · revisa la dirección"; }
        catch (ArgumentException ex) { StatusLabel.Text = ex.Message; }
        finally { CheckButton.IsEnabled = true; }
    }
    private async void OnEnter(object? sender, EventArgs e)
    {
        if (string.IsNullOrWhiteSpace(NameEntry.Text)) { await DisplayAlertAsync("Falta tu nombre", "Escribe tu nombre para continuar.", "Entendido"); return; }
        Preferences.Default.Set("student_name", NameEntry.Text); Preferences.Default.Set("student_server", ServerEntry.Text ?? ConnectionOptions.Default.ServerAddress); await Shell.Current.GoToAsync("menu");
    }
}
