from django.urls import path

from . import views

urlpatterns = [
    path("estado/", views.EstadoView.as_view(), name="biblioteca-estado"),
    path("cursos/", views.CursosView.as_view(), name="biblioteca-cursos"),
    path("cursos/<str:curso_ref>/", views.CursoView.as_view(), name="biblioteca-curso"),
    path("catalogo/", views.CatalogoView.as_view(), name="biblioteca-catalogo"),
    path("taxonomia/", views.TaxonomiaView.as_view(), name="biblioteca-taxonomia"),
    path("elementos/<str:ref>/", views.ElementoView.as_view(), name="biblioteca-elemento"),
    path("mostrar/", views.MostrarView.as_view(), name="biblioteca-mostrar"),
    path("leccion/<str:ref>/", views.LeccionView.as_view(), name="biblioteca-leccion"),
    path("evaluacion/<str:ref>/", views.EvaluacionView.as_view(), name="biblioteca-evaluacion"),
    path("medio/<str:ref>/", views.MedioView.as_view(), name="biblioteca-medio"),
    path("medio/<str:ref>/<path:ruta>", views.MedioView.as_view(), name="biblioteca-medio-interno"),
    path("voz/<str:ref>/", views.VozView.as_view(), name="biblioteca-voz"),
    path("voz/<str:ref>/<str:pregunta_ref>/", views.VozView.as_view(), name="biblioteca-voz-pregunta"),
]
