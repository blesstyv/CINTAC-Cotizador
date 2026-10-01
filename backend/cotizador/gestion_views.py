from pathlib import Path
from tempfile import NamedTemporaryFile

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
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)

from .permissions import (
    PuedeGestionarDatos,
)

from .services.importador_datos import (
    ErrorImportacionExcel,
    aplicar_importacion,
    crear_respaldo_sqlite,
    validar_archivo_excel,
)


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

        return Response(
            {
                "valido":
                    True,

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

        respaldo = (
            crear_respaldo_sqlite()
        )

        resumen = (
            aplicar_importacion(
                filas
            )
        )

        return Response(
            {
                "importado":
                    True,

                "filasProcesadas":
                    len(filas),

                "respaldoCreado":
                    respaldo is not None,

                "resumen":
                    resumen,

                "detail":
                    (
                        "Los datos maestros "
                        "fueron actualizados "
                        "correctamente."
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