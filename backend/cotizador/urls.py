from django.urls import path

from .auth_views import (
    cerrar_sesion,
    iniciar_sesion,
    sesion_actual,
)

from .gestion_views import (
    importar_excel,
    resumen_datos_maestros,
    validar_excel,
)

from .views import (
    cotizar_operacion,
    listar_rutas,
    listar_tipos_contenedor,
    obtener_opciones_contenedor,
)


urlpatterns = [
    path(
        "login/",
        iniciar_sesion,
        name="login",
    ),

    path(
        "sesion/",
        sesion_actual,
        name="sesion",
    ),

    path(
        "logout/",
        cerrar_sesion,
        name="logout",
    ),

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

    path(
        "administracion/resumen/",
        resumen_datos_maestros,
        name="administracion-resumen",
    ),

    path(
        "administracion/validar-excel/",
        validar_excel,
        name="administracion-validar-excel",
    ),

    path(
        "administracion/importar-excel/",
        importar_excel,
        name="administracion-importar-excel",
    ),
]