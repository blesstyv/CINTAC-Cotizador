"""
Manejo uniforme de errores de la API.

* Los errores conocidos de DRF (validación, autenticación, permisos,
  límites de solicitudes) conservan su formato y código original.
* Cualquier excepción no controlada se registra en el log del servidor
  con su traza y se responde con un JSON 500 genérico, sin exponer
  detalles internos (rutas, SQL, tracebacks) al cliente.
"""

import logging

from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger("cotizador.api")


def manejar_excepcion_api(exc, context):
    respuesta = exception_handler(exc, context)

    if respuesta is not None:
        return respuesta

    vista = context.get("view")
    nombre_vista = getattr(
        getattr(vista, "__class__", None),
        "__name__",
        "desconocida",
    )

    logger.exception(
        "Error no controlado en la vista %s",
        nombre_vista,
        exc_info=exc,
    )

    if isinstance(exc, DatabaseError):
        detalle = (
            "La base de datos no pudo completar la operación. "
            "Intente nuevamente en unos minutos."
        )
        codigo = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        detalle = (
            "Ocurrió un error interno. La operación no se completó."
        )
        codigo = status.HTTP_500_INTERNAL_SERVER_ERROR

    return Response(
        {"detail": detalle},
        status=codigo,
    )
