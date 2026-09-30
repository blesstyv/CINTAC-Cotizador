from decimal import (
    Decimal,
    ROUND_CEILING,
    ROUND_HALF_UP,
)

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)

from .serializers import (
    CotizacionOperacionSerializer,
    OpcionesOperacionSerializer,
    RutaSerializer,
    TipoContenedorSerializer,
)

from .services.tipo_cambio import (
    TipoCambioNoDisponible,
    convertir_usd_a_clp,
    obtener_tipo_cambio,
)


def convertir_peso(
    peso_carga,
    unidad_peso,
):
    if unidad_peso == "kg":
        peso_kg = peso_carga

        peso_tn = (
            peso_carga
            / Decimal("1000")
        )

    else:
        peso_tn = peso_carga

        peso_kg = (
            peso_carga
            * Decimal("1000")
        )

    return (
        peso_kg,
        peso_tn,
    )


def obtener_opciones(
    ruta,
    peso_tn,
):
    tipos = (
        TipoContenedor.objects
        .filter(
            activo=True
        )
        .order_by("id")
    )

    tarifas = {
        tarifa.tipo_contenedor:
            tarifa

        for tarifa in (
            Tarifa.objects
            .filter(
                ruta=ruta
            )
            .order_by("id")
        )
    }

    opciones = []

    for contenedor in tipos:
        capacidad_tn = (
            contenedor.capacidad_tn
        )

        if capacidad_tn <= 0:
            continue

        tarifa = tarifas.get(
            contenedor.codigo
        )

        if not tarifa:
            continue

        cantidad = int(
            (
                peso_tn
                / capacidad_tn
            ).to_integral_value(
                rounding=ROUND_CEILING
            )
        )

        total_min = (
            tarifa.valor_minimo
            * cantidad
        )

        total_max = (
            tarifa.valor_maximo
            * cantidad
        )

        costo_promedio = (
            total_min
            + total_max
        ) / Decimal("2")

        opciones.append(
            {
                "id":
                    contenedor.id,

                "codigo":
                    contenedor.codigo,

                "nombre":
                    contenedor.nombre,

                "capacidadTN":
                    str(
                        capacidad_tn
                    ),

                "cantidad":
                    cantidad,

                "tarifaMin":
                    str(
                        tarifa.valor_minimo
                    ),

                "tarifaMax":
                    str(
                        tarifa.valor_maximo
                    ),

                "totalMin":
                    str(
                        total_min
                    ),

                "totalMax":
                    str(
                        total_max
                    ),

                "fuente":
                    tarifa.fuente,

                "_costoPromedio":
                    costo_promedio,

                "_totalMax":
                    total_max,
            }
        )

    if not opciones:
        return (
            [],
            None,
        )

    sugerida = min(
        opciones,
        key=lambda opcion: (
            opcion[
                "_costoPromedio"
            ],
            opcion[
                "_totalMax"
            ],
            opcion["id"],
        ),
    )

    codigo_sugerido = (
        sugerida["codigo"]
    )

    opciones_publicas = []

    for opcion in opciones:
        opciones_publicas.append(
            {
                clave: valor

                for clave, valor
                in opcion.items()

                if not clave.startswith(
                    "_"
                )
            }
        )

    return (
        opciones_publicas,
        codigo_sugerido,
    )


def redondear_clp(valor):
    return Decimal(valor).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )


@api_view(["GET"])
def listar_tipos_contenedor(
    request
):
    tipos = (
        TipoContenedor.objects
        .filter(
            activo=True
        )
        .order_by("id")
    )

    serializer = (
        TipoContenedorSerializer(
            tipos,
            many=True,
        )
    )

    return Response(
        serializer.data
    )


@api_view(["GET"])
def listar_rutas(
    request
):
    tarifas_ordenadas = (
        Tarifa.objects.order_by(
            "id"
        )
    )

    rutas = (
        Ruta.objects
        .select_related(
            "puerto_origen",
            "puerto_destino",
            "tiempo_transito",
        )
        .prefetch_related(
            Prefetch(
                "tarifas",
                queryset=
                    tarifas_ordenadas,
            )
        )
        .order_by("id")
    )

    serializer = RutaSerializer(
        rutas,
        many=True,
    )

    return Response(
        serializer.data
    )


@api_view(["POST"])
def obtener_opciones_contenedor(
    request
):
    serializer = (
        OpcionesOperacionSerializer(
            data=request.data
        )
    )

    serializer.is_valid(
        raise_exception=True
    )

    datos = (
        serializer.validated_data
    )

    ruta = get_object_or_404(
        Ruta.objects.select_related(
            "puerto_origen",
            "puerto_destino",
        ),
        id=datos["ruta_id"],
    )

    peso_kg, peso_tn = (
        convertir_peso(
            datos["peso_carga"],
            datos["unidad_peso"],
        )
    )

    opciones, sugerida = (
        obtener_opciones(
            ruta,
            peso_tn,
        )
    )

    if not opciones:
        return Response(
            {
                "detail":
                    (
                        "No existen opciones "
                        "de contenedor disponibles "
                        "para esta ruta."
                    )
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "pesoKg":
                str(peso_kg),

            "pesoTN":
                str(peso_tn),

            "sugerida":
                sugerida,

            "opciones":
                opciones,
        }
    )


@api_view(["POST"])
def cotizar_operacion(
    request
):
    serializer = (
        CotizacionOperacionSerializer(
            data=request.data
        )
    )

    serializer.is_valid(
        raise_exception=True
    )

    datos = (
        serializer.validated_data
    )

    ruta = get_object_or_404(
        Ruta.objects.select_related(
            "puerto_origen",
            "puerto_destino",
            "tiempo_transito",
        ),
        id=datos["ruta_id"],
    )

    peso_kg, peso_tn = (
        convertir_peso(
            datos["peso_carga"],
            datos["unidad_peso"],
        )
    )

    opciones, sugerida = (
        obtener_opciones(
            ruta,
            peso_tn,
        )
    )

    opcion_seleccionada = next(
        (
            opcion

            for opcion
            in opciones

            if opcion["codigo"]
            == datos[
                "tipo_contenedor"
            ]
        ),
        None,
    )

    if not opcion_seleccionada:
        return Response(
            {
                "detail":
                    (
                        "El tipo de contenedor "
                        "seleccionado no está "
                        "disponible para esta ruta."
                    )
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    contingencia = datos.get(
        "contingencia",
        0,
    )

    total_min = Decimal(
        opcion_seleccionada[
            "totalMin"
        ]
    )

    total_max = Decimal(
        opcion_seleccionada[
            "totalMax"
        ]
    )


    tipo_cambio = None
    fecha_tipo_cambio = None
    fuente_tipo_cambio = None
    modo_tipo_cambio = None

    total_min_clp = None
    total_max_clp = None

    conversion_disponible = False
    mensaje_conversion = None


    try:
        cambio = (
            obtener_tipo_cambio()
        )

        tipo_cambio = (
            cambio["valor"]
        )

        fecha_tipo_cambio = (
            cambio["fecha"]
        )

        fuente_tipo_cambio = (
            cambio["fuente"]
        )

        modo_tipo_cambio = (
            cambio["modo"]
        )

        total_min_clp = redondear_clp(
            convertir_usd_a_clp(
                total_min,
                tipo_cambio,
            )
        )

        total_max_clp = redondear_clp(
            convertir_usd_a_clp(
                total_max,
                tipo_cambio,
            )
        )

        conversion_disponible = True

    except TipoCambioNoDisponible:
        mensaje_conversion = (
            "La cotización en USD fue "
            "generada correctamente, pero "
            "la conversión automática a CLP "
            "no está disponible temporalmente."
        )


    transito_original_min = None
    transito_original_max = None

    transito_min = None
    transito_max = None

    try:
        tiempo = (
            ruta.tiempo_transito
        )

        transito_original_min = (
            tiempo.dias_minimos
        )

        transito_original_max = (
            tiempo.dias_maximos
        )

        transito_min = (
            transito_original_min
            + contingencia
        )

        transito_max = (
            transito_original_max
            + contingencia
        )

    except TiempoTransito.DoesNotExist:
        pass


    return Response(
        {
            "rutaId":
                ruta.id,

            "origen":
                ruta.puerto_origen.nombre,

            "destino":
                ruta.puerto_destino.nombre,

            "pais":
                ruta.puerto_origen.pais,

            "tipoRuta":
                ruta.tipo_ruta,

            "pesoKg":
                str(peso_kg),

            "pesoTN":
                str(peso_tn),

            "tipoContenedor":
                opcion_seleccionada[
                    "codigo"
                ],

            "nombreContenedor":
                opcion_seleccionada[
                    "nombre"
                ],

            "capacidadTN":
                opcion_seleccionada[
                    "capacidadTN"
                ],

            "cantidad":
                opcion_seleccionada[
                    "cantidad"
                ],

            "tarifaMin":
                opcion_seleccionada[
                    "tarifaMin"
                ],

            "tarifaMax":
                opcion_seleccionada[
                    "tarifaMax"
                ],

            "totalMin":
                opcion_seleccionada[
                    "totalMin"
                ],

            "totalMax":
                opcion_seleccionada[
                    "totalMax"
                ],

            "esSugerida":
                (
                    opcion_seleccionada[
                        "codigo"
                    ]
                    == sugerida
                ),

            "transitoOriginalMin":
                transito_original_min,

            "transitoOriginalMax":
                transito_original_max,

            "transitoMin":
                transito_min,

            "transitoMax":
                transito_max,

            "contingencia":
                contingencia,

            "fuente":
                opcion_seleccionada[
                    "fuente"
                ],

            "conversionDisponible":
                conversion_disponible,

            "tipoCambio":
                (
                    str(tipo_cambio)
                    if tipo_cambio
                    is not None
                    else None
                ),

            "fechaTipoCambio":
                (
                    fecha_tipo_cambio
                    .isoformat()
                    if fecha_tipo_cambio
                    is not None
                    else None
                ),

            "fuenteTipoCambio":
                fuente_tipo_cambio,

            "modoTipoCambio":
                modo_tipo_cambio,

            "totalMinCLP":
                (
                    str(total_min_clp)
                    if total_min_clp
                    is not None
                    else None
                ),

            "totalMaxCLP":
                (
                    str(total_max_clp)
                    if total_max_clp
                    is not None
                    else None
                ),

            "mensajeConversion":
                mensaje_conversion,
        }
    )