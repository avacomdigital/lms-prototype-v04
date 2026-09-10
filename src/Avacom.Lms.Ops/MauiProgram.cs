using Microsoft.Extensions.Logging;

namespace Avacom.Lms.Ops;

public static class MauiProgram
{
	public static MauiApp CreateMauiApp()
	{
		Avacom.Lms.Core.Services.RegistroDeFallos.Observar("ops");
		var builder = MauiApp.CreateBuilder();
		builder
			.UseMauiApp<App>()
			.ConfigureFonts(fonts =>
			{
				fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
				fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
			});

#if DEBUG
		builder.Logging.AddDebug();
#endif

		return builder.Build();
	}
}
