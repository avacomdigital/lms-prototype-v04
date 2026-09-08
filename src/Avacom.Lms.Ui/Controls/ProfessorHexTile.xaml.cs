using Microsoft.Maui.Controls.Shapes;

namespace Avacom.Lms.Ui.Controls;

public partial class ProfessorHexTile : ContentView
{
    public static readonly BindableProperty TextProperty = BindableProperty.Create(nameof(Text), typeof(string), typeof(ProfessorHexTile), string.Empty);
    public static readonly BindableProperty AccentColorProperty = BindableProperty.Create(nameof(AccentColor), typeof(Color), typeof(ProfessorHexTile), Colors.Black);
    public static readonly BindableProperty IconGeometryProperty = BindableProperty.Create(
        nameof(IconGeometry),
        typeof(string),
        typeof(ProfessorHexTile),
        string.Empty,
        propertyChanged: OnIconGeometryChanged);

    public ProfessorHexTile() => InitializeComponent();

    public event EventHandler? Tapped;
    public string Text { get => (string)GetValue(TextProperty); set => SetValue(TextProperty, value); }
    public Color AccentColor { get => (Color)GetValue(AccentColorProperty); set => SetValue(AccentColorProperty, value); }
    public string IconGeometry { get => (string)GetValue(IconGeometryProperty); set => SetValue(IconGeometryProperty, value); }

    private static void OnIconGeometryChanged(BindableObject bindable, object oldValue, object newValue)
    {
        if (bindable is not ProfessorHexTile tile || newValue is not string data || string.IsNullOrWhiteSpace(data)) return;
        var converter = new PathGeometryConverter();
        tile.IconPath.Data = converter.ConvertFromInvariantString(data) as Geometry;
    }

    private async void OnTapped(object? sender, TappedEventArgs e)
    {
        await TileRoot.ScaleToAsync(0.97, 60, Easing.CubicOut);
        await TileRoot.ScaleToAsync(1, 90, Easing.CubicOut);
        Tapped?.Invoke(this, EventArgs.Empty);
    }

    private async void OnPointerEntered(object? sender, PointerEventArgs e) => await TileRoot.ScaleToAsync(1.04, 120, Easing.CubicOut);
    private async void OnPointerExited(object? sender, PointerEventArgs e) => await TileRoot.ScaleToAsync(1, 120, Easing.CubicOut);
}
