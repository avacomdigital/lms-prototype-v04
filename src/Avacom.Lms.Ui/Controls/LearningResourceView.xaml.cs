using System.Windows.Input;

namespace Avacom.Lms.Ui.Controls;

public partial class LearningResourceView : ContentView
{
    public static readonly BindableProperty SourceProperty = BindableProperty.Create(nameof(Source), typeof(string), typeof(LearningResourceView), string.Empty);
    public static readonly BindableProperty AllowedHostProperty = BindableProperty.Create(nameof(AllowedHost), typeof(string), typeof(LearningResourceView), string.Empty);

    public LearningResourceView()
    {
        InitializeComponent();
        OpenExternalCommand = new Command(async () =>
        {
            if (Uri.TryCreate(Source, UriKind.Absolute, out var uri)) await Launcher.Default.OpenAsync(uri);
        });
    }

    public string Source { get => (string)GetValue(SourceProperty); set => SetValue(SourceProperty, value); }
    public string AllowedHost { get => (string)GetValue(AllowedHostProperty); set => SetValue(AllowedHostProperty, value); }
    public ICommand OpenExternalCommand { get; }

    private void OnNavigating(object? sender, WebNavigatingEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(AllowedHost) || !Uri.TryCreate(e.Url, UriKind.Absolute, out var uri)) return;
        if (!string.Equals(uri.Host, AllowedHost, StringComparison.OrdinalIgnoreCase)) e.Cancel = true;
    }
}
