from django.urls import path

from .views import listar_tipos_contenedor


urlpatterns = [
    path(
        "tipos-contenedor/",
        listar_tipos_contenedor,
        name="tipos-contenedor",
    ),
]