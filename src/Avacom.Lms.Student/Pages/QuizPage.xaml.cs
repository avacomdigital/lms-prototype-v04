using Avacom.Lms.Core.Services;
namespace Avacom.Lms.Student.Pages;
public partial class QuizPage : ContentPage
{
    private readonly QuizSession session = new(DemoCatalog.MexicoQuiz);
    private string? selectedOptionId;
    public QuizPage() { InitializeComponent(); RenderQuestion(); }
    private void RenderQuestion()
    {
        selectedOptionId = null; ValidationLabel.IsVisible = false; var question = session.Current;
        ProgressLabel.Text = $"Pregunta {session.CurrentIndex + 1} de {session.Questions.Count}"; QuizProgress.Progress = (double)(session.CurrentIndex + 1) / session.Questions.Count; QuestionLabel.Text = question.Text; NextButton.Text = session.IsLast ? "Finalizar actividad" : "Siguiente pregunta"; OptionsContainer.Clear();
        foreach (var option in question.Options)
        {
            var button = new Button { Text = option.Text, BackgroundColor = Color.FromArgb("#F5F5F5"), TextColor = Color.FromArgb("#18181B"), CornerRadius = 14, HeightRequest = 54, HorizontalOptions = LayoutOptions.Fill };
            button.Clicked += (_, _) => SelectOption(option.Id, button); OptionsContainer.Add(button);
        }
    }
    private void SelectOption(string id, Button selected)
    {
        selectedOptionId = id; ValidationLabel.IsVisible = false;
        foreach (var child in OptionsContainer.Children.OfType<Button>()) { child.BackgroundColor = Color.FromArgb("#F5F5F5"); child.TextColor = Color.FromArgb("#18181B"); }
        selected.BackgroundColor = Color.FromArgb("#18181B"); selected.TextColor = Colors.White;
    }
    private async void OnNext(object? sender, EventArgs e)
    {
        if (selectedOptionId is null) { ValidationLabel.IsVisible = true; return; }
        session.Answer(selectedOptionId); session.MoveNext();
        if (session.IsLast && session.CurrentIndex == session.Questions.Count - 1 && ProgressLabel.Text.Contains("5 de 5"))
        {
            var result = session.Finish(); await DisplayAlertAsync("¡Actividad finalizada!", $"Tu nota es {result.Score:0.#}/100 · {result.CorrectAnswers} de {result.TotalQuestions} respuestas correctas.", "Volver al curso"); await Shell.Current.GoToAsync(".."); return;
        }
        RenderQuestion();
    }
    private async void OnBack(object? sender, EventArgs e) => await Shell.Current.GoToAsync("..");
}
