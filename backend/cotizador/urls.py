from django.urls import path

from .views import (
    listar_rutas,
    listar_tipos_contenedor,
)


urlpatterns = [
    path(
        "tipos-contenedor/",
        listar_tipos_contenedor,
        name="tipos-contenedor",
    ),

    path(
        "rutas/",
        listar_rutas,
        name="rutas",
    ),
]