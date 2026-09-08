using Avacom.Lms.Core.Services;
namespace Avacom.Lms.Ops.Pages;
public partial class ActivityMonitorPage : ContentPage
{
    public IEnumerable<StudentRow> Students { get; } = DemoCatalog.Students.Select(s => new StudentRow(s.Initials, s.Name, s.Status, s.CurrentQuestion, s.TotalQuestions == 0 ? 0 : (double)s.CurrentQuestion / s.TotalQuestions, s.Score is null ? "—" : $"{s.Score:0}/100"));
    public ActivityMonitorPage() { InitializeComponent(); BindingContext = this; }
    private async void OnBack(object? sender, EventArgs e) => await Shell.Current.GoToAsync("..");
    public sealed record StudentRow(string Initials, string Name, string Status, int CurrentQuestion, double Progress, string ScoreLabel);
}
