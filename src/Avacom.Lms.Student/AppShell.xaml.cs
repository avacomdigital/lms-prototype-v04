namespace Avacom.Lms.Student;
public partial class AppShell : Shell
{
    public AppShell()
    {
        InitializeComponent();
        Routing.RegisterRoute("menu", typeof(Pages.StudentMenuPage));
        Routing.RegisterRoute("course", typeof(Pages.CoursePage));
        Routing.RegisterRoute("quiz", typeof(Pages.QuizPage));
        Routing.RegisterRoute("asignaturas", typeof(Pages.AsignaturasPage));
        Routing.RegisterRoute("curso-biblioteca", typeof(Pages.CursoBibliotecaPage));
    }
}
