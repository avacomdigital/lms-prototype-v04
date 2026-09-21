using Microsoft.Extensions.DependencyInjection;

namespace Avacom.Lms.Student;

public partial class App : Application
{
	public App()
	{
		InitializeComponent();
		// Los fallos de reproducción del visor del aula se anotan en fallos-student.log (ver RegistroDeFallos.Ruta).
		Avacom.Lms.Ui.Controls.AulaContenidoView.NombreApp = "student";
	}

	protected override Window CreateWindow(IActivationState? activationState)
	{
		return new Window(new AppShell());
	}
}