using Microsoft.Extensions.DependencyInjection;

namespace Avacom.Lms.Ops;

public partial class App : Application
{
	public App()
	{
		InitializeComponent();
		// Los fallos de reproducción del visor del aula se anotan en fallos-ops.log (ver RegistroDeFallos.Ruta).
		Avacom.Lms.Ui.Controls.AulaContenidoView.NombreApp = "ops";
	}

	protected override Window CreateWindow(IActivationState? activationState)
	{
		return new Window(new AppShell());
	}
}