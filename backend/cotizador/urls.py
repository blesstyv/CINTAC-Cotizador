from django.urls import path

from .auth_views import (
    cerrar_sesion,
    iniciar_sesion,
    sesion_actual,
)

from .gestion_views import (
    importar_excel,
    operaciones_datos_maestros,
    restaurar_datos_maestros,
    resumen_datos_maestros,
    validar_excel,
)

from .historial_views import (
    exportar_historial_csv,
    historial_cotizacion_detalle,
    historial_cotizaciones,
)

from .usuario_views import (
    usuario_detalle,
    usuarios,
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
        "historial/",
        historial_cotizaciones,
        name="historial",
    ),

    path(
        "historial/exportar/",
        exportar_historial_csv,
        name="historial-exportar",
    ),

    path(
        "historial/<int:cotizacion_id>/",
        historial_cotizacion_detalle,
        name="historial-detalle",
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

    path(
        "administracion/operaciones/",
        operaciones_datos_maestros,
        name="administracion-operaciones",
    ),

    path(
        (
            "administracion/operaciones/"
            "<int:operacion_id>/restaurar/"
        ),
        restaurar_datos_maestros,
        name="administracion-operacion-restaurar",
    ),

    path(
        "administracion/usuarios/",
        usuarios,
        name="administracion-usuarios",
    ),

    path(
        (
            "administracion/usuarios/"
            "<int:usuario_id>/"
        ),
        usuario_detalle,
        name="administracion-usuario-detalle",
    ),
]