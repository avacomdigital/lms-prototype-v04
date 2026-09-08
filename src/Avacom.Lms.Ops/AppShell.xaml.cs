namespace Avacom.Lms.Ops;
public partial class AppShell : Shell
{
    public AppShell()
    {
        InitializeComponent();
        Routing.RegisterRoute("dashboard", typeof(Pages.DashboardPage));
        Routing.RegisterRoute("course-editor", typeof(Pages.CourseEditorPage));
        Routing.RegisterRoute("activity-monitor", typeof(Pages.ActivityMonitorPage));
    }
}
