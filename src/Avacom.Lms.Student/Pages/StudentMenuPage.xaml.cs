namespace Avacom.Lms.Student.Pages;
public partial class StudentMenuPage : ContentPage
{
    public StudentMenuPage() { InitializeComponent(); var name = Preferences.Default.Get("student_name", "Ethan Martínez"); StudentName.Text = name.Split(' ')[0]; WelcomeLabel.Text = $"Bienvenido, {name.Split(' ')[0]}"; }
    private async void OnCourses(object? sender, EventArgs e) => await Shell.Current.GoToAsync("course");
    private async void OnLogout(object? sender, EventArgs e) => await Shell.Current.GoToAsync("//connection");
}
