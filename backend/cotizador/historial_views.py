import csv
import io

from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import status

from rest_framework.decorators import (
    api_view,
)

from rest_framework.response import Response

from .models import (
    Cotizacion,
    PerfilUsuario,
)

from .services.calculo_cotizacion import (
    redondear_clp,
    totales_finales_de_cotizacion,
)


def _puede_ver_historial_general(
    usuario,
):
    if usuario.is_superuser:
        return True

    try:
        perfil = (
            usuario.perfil_cintac
        )

    except PerfilUsuario.DoesNotExist:
        return False

    return (
        perfil.autorizado
        and
        perfil.rol
        in {
            PerfilUsuario.Rol.ENCARGADO,
            PerfilUsuario.Rol.ADMINISTRADOR,
        }
    )


def _texto_o_nulo(valor):
    return (
        str(valor)
        if valor is not None
        else None
    )


def _totales_finales(
    cotizacion,
):
    """
    Total final (flete + valor de carga) de una cotización guardada.

    Se lee la instantánea persistida al cotizar; los registros
    anteriores a esa columna se reconstruyen con los valores del
    mismo registro, nunca con tarifas ni dólares actuales.
    """
    totales = totales_finales_de_cotizacion(
        cotizacion
    )

    return {
        "incluyeValorCarga":
            cotizacion.valor_carga_ingresado > 0,

        "valorCarga":
            str(cotizacion.valor_carga),

        "monedaValorCarga":
            cotizacion
            .valor_carga_moneda,

        "valorCargaIngresado":
            str(
                cotizacion
                .valor_carga_ingresado
            ),

        "totalFinalMin":
            str(totales.total_final_min),

        "totalFinalMax":
            str(totales.total_final_max),

        "totalFinalMinCLP":
            _texto_o_nulo(
                totales.total_final_min_clp
            ),

        "totalFinalMaxCLP":
            _texto_o_nulo(
                totales.total_final_max_clp
            ),
    }


def _serializar_cotizacion(
    cotizacion,
):
    return {
        "id":
            cotizacion.id,

        "fecha":
            cotizacion
            .creada_en
            .isoformat(),

        "usuario": {
            "id":
                cotizacion.usuario_id,

            "username":
                cotizacion
                .usuario
                .username,

            "nombre":
                (
                    cotizacion
                    .usuario
                    .get_full_name()
                    or
                    cotizacion
                    .usuario
                    .username
                ),
        },

        "origen":
            cotizacion.origen,

        "paisOrigen":
            cotizacion.pais_origen,

        "destino":
            cotizacion.destino,

        "tipoRuta":
            cotizacion.tipo_ruta,

        "pesoKg":
            str(
                cotizacion.peso_kg
            ),

        "pesoTN":
            str(
                cotizacion.peso_tn
            ),

        "tipoContenedor":
            cotizacion
            .tipo_contenedor,

        "nombreContenedor":
            cotizacion
            .nombre_contenedor,

        "capacidadTN":
            str(
                cotizacion
                .capacidad_tn
            ),

        "cantidad":
            cotizacion.cantidad,

        "tarifaMin":
            str(
                cotizacion
                .tarifa_min
            ),

        "tarifaMax":
            str(
                cotizacion
                .tarifa_max
            ),

        "totalMin":
            str(
                cotizacion
                .total_min
            ),

        "totalMax":
            str(
                cotizacion
                .total_max
            ),

        "esSugerida":
            cotizacion.es_sugerida,

        "contingencia":
            cotizacion.contingencia,

        "transitoOriginalMin":
            cotizacion
            .transito_original_min,

        "transitoOriginalMax":
            cotizacion
            .transito_original_max,

        "transitoMin":
            cotizacion.transito_min,

        "transitoMax":
            cotizacion.transito_max,

        "fuente":
            cotizacion
            .fuente_tarifa,

        "conversionDisponible":
            cotizacion
            .conversion_disponible,

        "tipoCambio":
            (
                str(
                    cotizacion
                    .tipo_cambio
                )
                if (
                    cotizacion
                    .tipo_cambio
                    is not None
                )
                else None
            ),

        "fechaTipoCambio":
            (
                cotizacion
                .fecha_tipo_cambio
                .isoformat()
                if (
                    cotizacion
                    .fecha_tipo_cambio
                    is not None
                )
                else None
            ),

        "fuenteTipoCambio":
            (
                cotizacion
                .fuente_tipo_cambio
                or None
            ),

        "modoTipoCambio":
            (
                cotizacion
                .modo_tipo_cambio
                or None
            ),

        "totalMinCLP":
            (
                str(
                    redondear_clp(
                        cotizacion
                        .total_min_clp
                    )
                )
                if (
                    cotizacion
                    .total_min_clp
                    is not None
                )
                else None
            ),

        "totalMaxCLP":
            (
                str(
                    redondear_clp(
                        cotizacion
                        .total_max_clp
                    )
                )
                if (
                    cotizacion
                    .total_max_clp
                    is not None
                )
                else None
            ),

        # Campos agregados: valor de carga y total final.
        **_totales_finales(
            cotizacion
        ),
    }


def _convertir_fecha(
    valor,
    nombre,
):
    if not valor:
        return (
            None,
            None,
        )

    try:
        fecha = (
            datetime.strptime(
                valor,
                "%Y-%m-%d",
            )
            .date()
        )

    except ValueError:
        return (
            None,
            (
                f"El filtro '{nombre}' "
                "debe utilizar formato "
                "AAAA-MM-DD."
            ),
        )

    return (
        fecha,
        None,
    )


class FiltroHistorialInvalido(Exception):
    def __init__(self, detalle, codigo=status.HTTP_400_BAD_REQUEST):
        super().__init__(detalle)
        self.detalle = detalle
        self.codigo = codigo


def _texto_param(request, nombre):
    return str(
        request.query_params.get(
            nombre,
            "",
        )
    ).strip()


def filtrar_historial(request):
    """
    Devuelve (queryset, puede_ver_todas) aplicando permisos y filtros.

    Es la única fuente de verdad para el listado y la exportación CSV:
    ambos muestran exactamente los mismos registros autorizados.
    """
    puede_ver_todas = (
        _puede_ver_historial_general(
            request.user
        )
    )

    consulta = (
        Cotizacion.objects
        .select_related(
            "usuario"
        )
        .all()
    )

    if not puede_ver_todas:
        consulta = consulta.filter(
            usuario=request.user
        )

    usuario_id = request.query_params.get(
        "usuario_id"
    )

    if usuario_id:
        if not puede_ver_todas:
            raise FiltroHistorialInvalido(
                (
                    "No tiene permiso "
                    "para consultar "
                    "cotizaciones de "
                    "otros usuarios."
                ),
                status.HTTP_403_FORBIDDEN,
            )

        try:
            usuario_id = int(usuario_id)

            if usuario_id <= 0:
                raise ValueError

        except (TypeError, ValueError):
            raise FiltroHistorialInvalido(
                "El usuario indicado no es válido."
            )

        if not User.objects.filter(
            id=usuario_id
        ).exists():
            raise FiltroHistorialInvalido(
                "El usuario indicado no existe."
            )

        consulta = consulta.filter(
            usuario_id=usuario_id
        )

    origen = _texto_param(request, "origen")

    if origen:
        consulta = consulta.filter(
            origen__icontains=origen[:100]
        )

    destino = _texto_param(request, "destino")

    if destino:
        consulta = consulta.filter(
            destino__icontains=destino[:100]
        )

    contenedor = _texto_param(request, "contenedor")

    if contenedor:
        if contenedor not in {"20", "40"}:
            raise FiltroHistorialInvalido(
                "El filtro de contenedor no es válido."
            )

        consulta = consulta.filter(
            tipo_contenedor=contenedor
        )

    fecha_desde, error = _convertir_fecha(
        request.query_params.get("desde"),
        "desde",
    )

    if error:
        raise FiltroHistorialInvalido(error)

    fecha_hasta, error = _convertir_fecha(
        request.query_params.get("hasta"),
        "hasta",
    )

    if error:
        raise FiltroHistorialInvalido(error)

    if (
        fecha_desde
        and fecha_hasta
        and fecha_desde > fecha_hasta
    ):
        raise FiltroHistorialInvalido(
            "La fecha inicial no puede ser "
            "posterior a la fecha final."
        )

    if fecha_desde:
        consulta = consulta.filter(
            creada_en__date__gte=fecha_desde
        )

    if fecha_hasta:
        consulta = consulta.filter(
            creada_en__date__lte=fecha_hasta
        )

    return consulta, puede_ver_todas


LIMITE_POR_DEFECTO = 500

LIMITE_MAXIMO_PAGINA = 500


def _entero_positivo(valor, por_defecto, maximo=None):
    if valor in (None, ""):
        return por_defecto

    try:
        numero = int(valor)

    except (TypeError, ValueError):
        raise FiltroHistorialInvalido(
            "Los parámetros de paginación deben ser enteros positivos."
        )

    if numero < 1:
        raise FiltroHistorialInvalido(
            "Los parámetros de paginación deben ser enteros positivos."
        )

    if maximo is not None:
        numero = min(numero, maximo)

    return numero


@api_view(["GET"])
def historial_cotizaciones(
    request,
):
    try:
        consulta, puede_ver_todas = filtrar_historial(
            request
        )

        por_pagina = _entero_positivo(
            request.query_params.get("por_pagina"),
            LIMITE_POR_DEFECTO,
            LIMITE_MAXIMO_PAGINA,
        )

        pagina = _entero_positivo(
            request.query_params.get("pagina"),
            1,
        )

    except FiltroHistorialInvalido as error:
        return Response(
            {"detail": error.detalle},
            status=error.codigo,
        )

    total = consulta.count()

    total_paginas = max(
        (total + por_pagina - 1) // por_pagina,
        1,
    )

    inicio = (pagina - 1) * por_pagina

    registros = list(
        consulta[inicio:inicio + por_pagina]
    )

    return Response(
        {
            "puedeVerTodas":
                puede_ver_todas,

            "total":
                total,

            "limite":
                por_pagina,

            "pagina":
                pagina,

            "totalPaginas":
                total_paginas,

            "cotizaciones": [
                _serializar_cotizacion(
                    cotizacion
                )
                for cotizacion
                in registros
            ],
        },
        status=
            status.HTTP_200_OK,
    )


# ----------------------------------------------------------------------
# Exportación CSV
# ----------------------------------------------------------------------

LIMITE_EXPORTACION = 10000

_PREFIJOS_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def celda_csv_segura(valor):
    """
    Evita la inyección de fórmulas (CSV/Formula Injection): un texto
    que comienza con =, +, -, @, tabulación o retorno se antepone con
    un apóstrofo para que Excel lo trate como texto. Los números se
    exportan sin alterar.
    """
    if valor is None:
        return ""

    if isinstance(valor, (int, Decimal)) and not isinstance(valor, bool):
        return str(valor)

    texto = str(valor)

    if texto.startswith(_PREFIJOS_FORMULA):
        return "'" + texto

    return texto


ENCABEZADOS_CSV = [
    "ID",
    "Fecha",
    "Usuario",
    "Origen",
    "País origen",
    "Destino",
    "Tipo de ruta",
    "Peso (TN)",
    "Contenedor",
    "Capacidad (TN)",
    "Cantidad",
    "Tarifa mínima USD",
    "Tarifa máxima USD",
    "Flete mínimo USD",
    "Flete máximo USD",
    "Valor de carga ingresado",
    "Moneda valor de carga",
    "Valor de carga USD",
    "Total final mínimo USD",
    "Total final máximo USD",
    "Dólar utilizado (CLP/USD)",
    "Fecha dólar",
    "Estado dólar",
    "Total final mínimo CLP",
    "Total final máximo CLP",
    "Tránsito mínimo (días)",
    "Tránsito máximo (días)",
    "Contingencia (días)",
]


def _fila_csv(cotizacion):
    totales = totales_finales_de_cotizacion(cotizacion)

    return [
        cotizacion.id,
        timezone.localtime(cotizacion.creada_en).strftime(
            "%Y-%m-%d %H:%M"
        ),
        cotizacion.usuario.username,
        cotizacion.origen,
        cotizacion.pais_origen,
        cotizacion.destino,
        cotizacion.tipo_ruta,
        cotizacion.peso_tn,
        cotizacion.nombre_contenedor,
        cotizacion.capacidad_tn,
        cotizacion.cantidad,
        cotizacion.tarifa_min,
        cotizacion.tarifa_max,
        cotizacion.total_min,
        cotizacion.total_max,
        cotizacion.valor_carga_ingresado,
        cotizacion.valor_carga_moneda,
        cotizacion.valor_carga,
        totales.total_final_min,
        totales.total_final_max,
        cotizacion.tipo_cambio,
        (
            cotizacion.fecha_tipo_cambio.isoformat()
            if cotizacion.fecha_tipo_cambio
            else ""
        ),
        cotizacion.modo_tipo_cambio,
        totales.total_final_min_clp,
        totales.total_final_max_clp,
        cotizacion.transito_min,
        cotizacion.transito_max,
        cotizacion.contingencia,
    ]


@api_view(["GET"])
def exportar_historial_csv(
    request,
):
    """
    Exporta a CSV los registros que el usuario puede ver, con los
    mismos filtros del listado. No incluye correos ni datos de
    autenticación. Separador ';' y BOM UTF-8 para Excel en español.
    """
    try:
        consulta, _ = filtrar_historial(request)

    except FiltroHistorialInvalido as error:
        return Response(
            {"detail": error.detalle},
            status=error.codigo,
        )

    salida = io.StringIO()
    salida.write("\ufeff")

    escritor = csv.writer(
        salida,
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\r\n",
    )

    escritor.writerow(ENCABEZADOS_CSV)

    for cotizacion in consulta[:LIMITE_EXPORTACION]:
        escritor.writerow(
            [
                celda_csv_segura(valor)
                for valor in _fila_csv(cotizacion)
            ]
        )

    nombre = (
        "cintac-historial-"
        + timezone.localdate().isoformat()
        + ".csv"
    )

    respuesta = HttpResponse(
        salida.getvalue(),
        content_type="text/csv; charset=utf-8",
    )
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{nombre}"'
    )
    respuesta["Cache-Control"] = "no-store"

    return respuesta


@api_view(["GET"])
def historial_cotizacion_detalle(
    request,
    cotizacion_id,
):
    puede_ver_todas = (
        _puede_ver_historial_general(
            request.user
        )
    )

    consulta = (
        Cotizacion.objects
        .select_related(
            "usuario"
        )
        .filter(
            id=cotizacion_id
        )
    )

    if not puede_ver_todas:
        consulta = consulta.filter(
            usuario=request.user
        )

    cotizacion = consulta.first()

    if not cotizacion:
        return Response(
            {
                "detail":
                    (
                        "La cotización "
                        "no existe o no "
                        "puede ser consultada."
                    )
            },
            status=
                status
                .HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "cotizacion":
                _serializar_cotizacion(
                    cotizacion
                )
        },
        status=
            status.HTTP_200_OK,
    )