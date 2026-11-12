import logging

from pathlib import Path
from tempfile import NamedTemporaryFile

from django.db import transaction

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import (
    FormParser,
    MultiPartParser,
)
from rest_framework.response import Response

from .models import (
    OperacionDatosMaestros,
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)

from .permissions import (
    PuedeGestionarDatos,
    PuedeGestionarUsuarios,
)

from .services.datos_maestros import (
    InstantaneaInvalida,
    calcular_sha256,
    capturar_estado,
    comparar_con_estado_actual,
    registrar_operacion,
    restaurar_estado,
    resumir_estado,
)

from .services.importador_datos import (
    ErrorImportacionExcel,
    aplicar_importacion,
    crear_respaldo_sqlite,
    validar_archivo_excel,
)


logger = logging.getLogger("cotizador.administracion")


def _nombre_seguro(archivo):
    return Path(
        str(getattr(archivo, "name", "") or "")
    ).name[:255]


TAMANO_MAXIMO_EXCEL = (
    5 * 1024 * 1024
)


def _validar_archivo_recibido(
    archivo,
):
    if archivo is None:
        return (
            "Debe seleccionar un archivo Excel."
        )

    nombre = str(
        archivo.name
    ).strip()

    if not nombre:
        return (
            "El archivo no posee un nombre válido."
        )

    if (
        Path(nombre)
        .suffix
        .lower()
        != ".xlsx"
    ):
        return (
            "Solo se permiten archivos .xlsx."
        )

    if archivo.size <= 0:
        return (
            "El archivo está vacío."
        )

    if (
        archivo.size
        > TAMANO_MAXIMO_EXCEL
    ):
        return (
            "El archivo supera el tamaño "
            "máximo permitido de 5 MB."
        )

    return None


def _guardar_archivo_temporal(
    archivo,
):
    temporal = NamedTemporaryFile(
        suffix=".xlsx",
        delete=False,
    )

    ruta = Path(
        temporal.name
    )

    try:
        for bloque in archivo.chunks():
            temporal.write(
                bloque
            )

    finally:
        temporal.close()

    return ruta


def _eliminar_temporal(
    ruta,
):
    if (
        ruta
        and ruta.exists()
    ):
        try:
            ruta.unlink()

        except OSError:
            pass


def _vista_previa(
    filas,
    limite=10,
):
    resultado = []

    for fila in filas[:limite]:
        resultado.append(
            {
                "fila":
                    fila.numero_fila,

                "origen":
                    fila.origen,

                "pais":
                    fila.pais_origen,

                "destino":
                    fila.destino,

                "tipoRuta":
                    fila.tipo_ruta,

                "tarifa20Min":
                    str(
                        fila.tarifa20_min
                    ),

                "tarifa20Max":
                    str(
                        fila.tarifa20_max
                    ),

                "tarifa40Min":
                    str(
                        fila.tarifa40_min
                    ),

                "tarifa40Max":
                    str(
                        fila.tarifa40_max
                    ),

                "transitoMin":
                    fila.transito_min,

                "transitoMax":
                    fila.transito_max,

                "fuente":
                    fila.fuente,
            }
        )

    return resultado


@api_view(["GET"])
@permission_classes(
    [PuedeGestionarDatos]
)
def resumen_datos_maestros(
    request,
):
    return Response(
        {
            "puertos":
                Puerto.objects.count(),

            "rutas":
                Ruta.objects.count(),

            "tarifas":
                Tarifa.objects.count(),

            "tiemposTransito":
                TiempoTransito.objects.count(),

            "tiposContenedor":
                TipoContenedor.objects.count(),
        },
        status=
            status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(
    [PuedeGestionarDatos]
)
@parser_classes(
    [
        MultiPartParser,
        FormParser,
    ]
)
def validar_excel(
    request,
):
    archivo = (
        request.FILES.get(
            "archivo"
        )
    )

    error_archivo = (
        _validar_archivo_recibido(
            archivo
        )
    )

    if error_archivo:
        return Response(
            {
                "valido":
                    False,

                "errores": [
                    error_archivo
                ],
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    ruta_temporal = None

    try:
        ruta_temporal = (
            _guardar_archivo_temporal(
                archivo
            )
        )

        filas = validar_archivo_excel(
            ruta_temporal
        )

        comparacion, resumen_cambios = (
            comparar_con_estado_actual(
                filas
            )
        )

        return Response(
            {
                "valido":
                    True,

                "archivoSha256":
                    calcular_sha256(
                        ruta_temporal
                    ),

                "resumenCambios":
                    resumen_cambios,

                # Solo filas con diferencias (nuevas o modificadas),
                # para revisar antes de confirmar la importación.
                "comparacion": [
                    item
                    for item in comparacion
                    if item["estado"] != "sin_cambios"
                ][:200],

                "filasValidas":
                    len(filas),

                "resumen": {
                    "rutas":
                        len(filas),

                    "tarifas":
                        len(filas) * 2,

                    "tiemposTransito":
                        len(filas),
                },

                "vistaPrevia":
                    _vista_previa(
                        filas
                    ),
            },
            status=
                status.HTTP_200_OK,
        )

    except ErrorImportacionExcel as error:
        return Response(
            {
                "valido":
                    False,

                "filasValidas":
                    0,

                "errores":
                    error.errores,
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    finally:
        _eliminar_temporal(
            ruta_temporal
        )


@api_view(["POST"])
@permission_classes(
    [PuedeGestionarDatos]
)
@parser_classes(
    [
        MultiPartParser,
        FormParser,
    ]
)
def importar_excel(
    request,
):
    archivo = (
        request.FILES.get(
            "archivo"
        )
    )

    nombre_archivo = _nombre_seguro(
        archivo
    )

    error_archivo = (
        _validar_archivo_recibido(
            archivo
        )
    )

    if error_archivo:
        return Response(
            {
                "importado":
                    False,

                "errores": [
                    error_archivo
                ],
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    ruta_temporal = None

    try:
        ruta_temporal = (
            _guardar_archivo_temporal(
                archivo
            )
        )

        filas = validar_archivo_excel(
            ruta_temporal
        )

        sha256 = calcular_sha256(
            ruta_temporal
        )

        hash_esperado = str(
            request.data.get(
                "archivo_sha256",
                "",
            )
        ).strip().lower()

        # Si el cliente informa el hash de la vista previa, se exige
        # que el archivo confirmado sea exactamente el revisado.
        if hash_esperado and hash_esperado != sha256:
            return Response(
                {
                    "importado":
                        False,

                    "errores": [
                        (
                            "El archivo no coincide con el "
                            "validado en la vista previa. "
                            "Vuelva a validarlo."
                        )
                    ],
                },
                status=
                    status.HTTP_409_CONFLICT,
            )

        # Gancho heredado (sin efecto en PostgreSQL). El respaldo real
        # es la instantánea guardada en la bitácora de operaciones.
        crear_respaldo_sqlite()

        with transaction.atomic():
            estado_previo = capturar_estado()

            resumen = aplicar_importacion(
                filas
            )

            operacion = registrar_operacion(
                OperacionDatosMaestros.Tipo.IMPORTACION_EXCEL,
                request.user,
                archivo_nombre=nombre_archivo,
                archivo_sha256=sha256,
                resumen={
                    **resumen,
                    "filas": len(filas),
                    "estadoPrevio": resumir_estado(
                        estado_previo
                    ),
                },
                estado_previo=estado_previo,
            )

        logger.info(
            "Importación Excel #%s aplicada por %s (%s filas).",
            operacion.id,
            request.user.username,
            len(filas),
        )

        return Response(
            {
                "importado":
                    True,

                "filasProcesadas":
                    len(filas),

                "respaldoCreado":
                    True,

                "operacionId":
                    operacion.id,

                "resumen":
                    resumen,

                "detail":
                    (
                        "Los datos maestros "
                        "fueron actualizados "
                        "correctamente. Se guardó "
                        "un respaldo del estado "
                        "anterior."
                    ),
            },
            status=
                status.HTTP_200_OK,
        )

    except ErrorImportacionExcel as error:
        return Response(
            {
                "importado":
                    False,

                "errores":
                    error.errores,
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    except Exception:
        logger.exception(
            "Falló la importación Excel solicitada por %s.",
            request.user.username,
        )

        try:
            registrar_operacion(
                OperacionDatosMaestros.Tipo.IMPORTACION_EXCEL,
                request.user,
                estado=OperacionDatosMaestros.Estado.FALLIDA,
                archivo_nombre=nombre_archivo,
                detalle=(
                    "Error interno al aplicar la importación; "
                    "la transacción fue revertida."
                ),
            )
        except Exception:
            logger.exception(
                "No se pudo registrar la importación fallida."
            )

        return Response(
            {
                "importado":
                    False,

                "errores": [
                    (
                        "No fue posible completar "
                        "la actualización de los "
                        "datos maestros."
                    )
                ],
            },
            status=
                status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        _eliminar_temporal(
            ruta_temporal
        )


# ----------------------------------------------------------------------
# Bitácora y recuperación de datos maestros
# ----------------------------------------------------------------------


def _representar_operacion(operacion, restaurable):
    return {
        "id": operacion.id,
        "tipo": operacion.tipo,
        "tipoNombre": operacion.get_tipo_display(),
        "estado": operacion.estado,
        "fecha": operacion.creada_en.isoformat(),
        "usuario": operacion.usuario_username,
        "archivo": operacion.archivo_nombre,
        "archivoSha256": operacion.archivo_sha256,
        "resumen": operacion.resumen,
        "restauradaDesde": operacion.restaurada_desde_id,
        "detalle": operacion.detalle,
        "restaurable": restaurable,
    }


@api_view(["GET"])
@permission_classes(
    [PuedeGestionarDatos]
)
def operaciones_datos_maestros(
    request,
):
    operaciones = (
        OperacionDatosMaestros.objects
        .defer("estado_previo")
        .order_by("-creada_en", "-id")[:50]
    )

    # estado_previo se difiere para no transferir instantáneas
    # completas; "restaurable" se calcula con una consulta liviana.
    con_respaldo = set(
        OperacionDatosMaestros.objects
        .filter(
            id__in=[op.id for op in operaciones],
            estado_previo__isnull=False,
        )
        .values_list("id", flat=True)
    )

    datos = [
        _representar_operacion(
            operacion,
            restaurable=(
                operacion.estado
                == OperacionDatosMaestros.Estado.COMPLETADA
                and operacion.id in con_respaldo
            ),
        )
        for operacion in operaciones
    ]

    return Response(
        {
            "operaciones": datos,
            "puedeRestaurar": PuedeGestionarUsuarios().has_permission(
                request,
                None,
            ),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(
    [PuedeGestionarUsuarios]
)
def restaurar_datos_maestros(
    request,
    operacion_id,
):
    """
    Restaura los datos maestros al estado previo de una operación.

    Solo ADMINISTRADOR. Exige {"confirmar": true}. Antes de restaurar
    se guarda el estado actual, por lo que la acción es reversible.
    """
    if request.data.get("confirmar") is not True:
        return Response(
            {
                "detail":
                    (
                        "Debe confirmar explícitamente la "
                        "restauración (confirmar: true)."
                    )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    operacion = (
        OperacionDatosMaestros.objects
        .filter(
            id=operacion_id,
            estado=OperacionDatosMaestros.Estado.COMPLETADA,
        )
        .first()
    )

    if operacion is None or not operacion.estado_previo:
        return Response(
            {
                "detail":
                    (
                        "La operación no existe o no tiene "
                        "un respaldo restaurable."
                    )
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        with transaction.atomic():
            estado_actual = capturar_estado()

            resumen = restaurar_estado(
                operacion.estado_previo
            )

            nueva = registrar_operacion(
                OperacionDatosMaestros.Tipo.RESTAURACION,
                request.user,
                restaurada_desde=operacion,
                resumen={
                    **resumen,
                    "estadoRestaurado": resumir_estado(
                        operacion.estado_previo
                    ),
                },
                estado_previo=estado_actual,
            )

    except InstantaneaInvalida as error:
        return Response(
            {"detail": str(error)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger.warning(
        "Datos maestros restaurados desde la operación #%s por %s "
        "(registro #%s).",
        operacion.id,
        request.user.username,
        nueva.id,
    )

    return Response(
        {
            "detail":
                (
                    "Datos maestros restaurados al estado "
                    "anterior a la operación "
                    f"#{operacion.id}. La restauración "
                    "quedó registrada y puede revertirse."
                ),
            "operacionId": nueva.id,
            "resumen": resumen,
        },
        status=status.HTTP_200_OK,
    )

