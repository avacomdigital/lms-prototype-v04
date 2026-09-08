namespace Avacom.Lms.Student.Pages;
public partial class CoursePage : ContentPage
{
    public CoursePage() => InitializeComponent();
    private async void OnBack(object? sender, EventArgs e) => await Shell.Current.GoToAsync("..");
    private async void OnQuiz(object? sender, EventArgs e) => await Shell.Current.GoToAsync("quiz");
}
