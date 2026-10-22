from datetime import datetime

from django.contrib.auth.models import User

from rest_framework import status

from rest_framework.decorators import (
    api_view,
)

from rest_framework.response import Response

from .models import (
    Cotizacion,
    PerfilUsuario,
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
                    cotizacion
                    .total_min_clp
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
                    cotizacion
                    .total_max_clp
                )
                if (
                    cotizacion
                    .total_max_clp
                    is not None
                )
                else None
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


@api_view(["GET"])
def historial_cotizaciones(
    request,
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
        .all()
    )

    if not puede_ver_todas:
        consulta = consulta.filter(
            usuario=request.user
        )

    usuario_id = (
        request.query_params.get(
            "usuario_id"
        )
    )

    if usuario_id:
        if not puede_ver_todas:
            return Response(
                {
                    "detail":
                        (
                            "No tiene permiso "
                            "para consultar "
                            "cotizaciones de "
                            "otros usuarios."
                        )
                },
                status=
                    status
                    .HTTP_403_FORBIDDEN,
            )

        try:
            usuario_id = int(
                usuario_id
            )

            if usuario_id <= 0:
                raise ValueError

        except (
            TypeError,
            ValueError,
        ):
            return Response(
                {
                    "detail":
                        (
                            "El usuario indicado "
                            "no es válido."
                        )
                },
                status=
                    status
                    .HTTP_400_BAD_REQUEST,
            )

        if not (
            User.objects
            .filter(
                id=usuario_id
            )
            .exists()
        ):
            return Response(
                {
                    "detail":
                        (
                            "El usuario indicado "
                            "no existe."
                        )
                },
                status=
                    status
                    .HTTP_400_BAD_REQUEST,
            )

        consulta = consulta.filter(
            usuario_id=usuario_id
        )

    origen = str(
        request.query_params.get(
            "origen",
            "",
        )
    ).strip()

    if origen:
        consulta = consulta.filter(
            origen__icontains=origen
        )

    destino = str(
        request.query_params.get(
            "destino",
            "",
        )
    ).strip()

    if destino:
        consulta = consulta.filter(
            destino__icontains=destino
        )

    contenedor = str(
        request.query_params.get(
            "contenedor",
            "",
        )
    ).strip()

    if contenedor:
        if contenedor not in {
            "20",
            "40",
        }:
            return Response(
                {
                    "detail":
                        (
                            "El filtro de "
                            "contenedor no "
                            "es válido."
                        )
                },
                status=
                    status
                    .HTTP_400_BAD_REQUEST,
            )

        consulta = consulta.filter(
            tipo_contenedor=
                contenedor
        )

    fecha_desde, error = (
        _convertir_fecha(
            request.query_params.get(
                "desde"
            ),
            "desde",
        )
    )

    if error:
        return Response(
            {
                "detail":
                    error
            },
            status=
                status
                .HTTP_400_BAD_REQUEST,
        )

    fecha_hasta, error = (
        _convertir_fecha(
            request.query_params.get(
                "hasta"
            ),
            "hasta",
        )
    )

    if error:
        return Response(
            {
                "detail":
                    error
            },
            status=
                status
                .HTTP_400_BAD_REQUEST,
        )

    if (
        fecha_desde
        and fecha_hasta
        and fecha_desde
        > fecha_hasta
    ):
        return Response(
            {
                "detail":
                    (
                        "La fecha inicial "
                        "no puede ser posterior "
                        "a la fecha final."
                    )
            },
            status=
                status
                .HTTP_400_BAD_REQUEST,
        )

    if fecha_desde:
        consulta = consulta.filter(
            creada_en__date__gte=
                fecha_desde
        )

    if fecha_hasta:
        consulta = consulta.filter(
            creada_en__date__lte=
                fecha_hasta
        )

    total = consulta.count()

    registros = list(
        consulta[:500]
    )

    return Response(
        {
            "puedeVerTodas":
                puede_ver_todas,

            "total":
                total,

            "limite":
                500,

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