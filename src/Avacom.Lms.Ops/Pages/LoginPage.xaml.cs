using Avacom.Lms.Core.Models;
using Avacom.Lms.Core.Services;
namespace Avacom.Lms.Ops.Pages;
public partial class LoginPage : ContentPage
{
    private readonly ILmsApiClient apiClient = new LmsApiClient(new HttpClient { Timeout = TimeSpan.FromSeconds(3) });
    public LoginPage() => InitializeComponent();
    private async void OnCheckConnection(object? sender, EventArgs e)
    {
        CheckButton.IsEnabled = false; StatusLabel.Text = "Comprobando el servicio local…";
        try
        {
            var healthy = await apiClient.CheckHealthAsync(ConnectionOptions.Normalize(ServerEntry.Text ?? string.Empty));
            StatusCard.BackgroundColor = Color.FromArgb(healthy ? "#E6F5EE" : "#FDECEC"); StatusDot.TextColor = Color.FromArgb(healthy ? "#019D60" : "#E5262B");
            StatusLabel.Text = healthy ? "Conexión exitosa · API disponible" : "No fue posible conectar · revisa red, IP y puerto";
        }
        catch (ArgumentException ex) { StatusLabel.Text = ex.Message; }
        finally { CheckButton.IsEnabled = true; }
    }
    private async void OnEnterDemo(object? sender, EventArgs e) { Preferences.Default.Set("ops_server", ServerEntry.Text ?? "http://127.0.0.1:8000"); await Shell.Current.GoToAsync("dashboard"); }
}
