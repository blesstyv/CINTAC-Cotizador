from django.urls import path

from .views import (
    cotizar_operacion,
    listar_rutas,
    listar_tipos_contenedor,
    obtener_opciones_contenedor,
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

    path(
        "opciones-contenedores/",
        obtener_opciones_contenedor,
        name="opciones-contenedores",
    ),

    path(
        "cotizar/",
        cotizar_operacion,
        name="cotizar",
    ),
]