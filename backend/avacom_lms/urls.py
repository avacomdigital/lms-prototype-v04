from django.urls import include, path

from expediente.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/acceso/", include("acceso.interfaces.urls")),
    path("api/biblioteca/", include("biblioteca.urls")),
    path("api/aula/", include("aula.interfaces.urls")),
    path("api/", include("expediente.urls")),
]
