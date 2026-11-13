"""
Gestión manual de rutas, puertos, tarifas y tiempos de tránsito.

Permite al ENCARGADO o ADMINISTRADOR mantener los datos maestros sin
depender del Excel: agregar una ruta (creando el puerto si no existe)
y actualizar tarifas o tránsito. Cada cambio:

* se valida con las mismas reglas del modelo (montos > 0, máximo >=
  mínimo, origen distinto de destino);
* se ejecuta en una transacción;
* queda en la bitácora con una instantánea del estado anterior, por lo
  que un administrador puede restaurarlo.

Las cotizaciones del historial no cambian: conservan sus propios valores.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Prefetch

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import (
    OperacionDatosMaestros,
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
)
from .permissions import PuedeGestionarDatos
from .serializers import StrictSerializer
from .services.datos_maestros import (
    capturar_estado,
    registrar_operacion,
    resumir_estado,
)


FUENTE_MANUAL = "Actualización manual"

PAIS_DESTINO_POR_DEFECTO = "Chile"

TIPOS_RUTA = [opcion[0] for opcion in Ruta.TIPO_RUTA_CHOICES]


def _texto(etiqueta, maximo=100):
    return serializers.CharField(
        max_length=maximo,
        trim_whitespace=True,
        error_messages={
            "required": f"Debe indicar {etiqueta}.",
            "blank": f"Debe indicar {etiqueta}.",
            "max_length": f"El texto de {etiqueta} es demasiado largo.",
        },
    )


def _tarifa(etiqueta, required=True):
    return serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=required,
        error_messages={
            "required": f"Debe ingresar la {etiqueta}.",
            "invalid": f"La {etiqueta} debe ser un valor numérico.",
            "min_value": f"La {etiqueta} debe ser mayor que cero.",
            "max_digits": f"La {etiqueta} excede el formato permitido.",
            "max_whole_digits": f"La {etiqueta} excede el formato permitido.",
            "max_decimal_places": (
                f"La {etiqueta} admite como máximo dos decimales."
            ),
        },
    )


def _dias(etiqueta, required=True):
    return serializers.IntegerField(
        min_value=1,
        max_value=365,
        required=required,
        error_messages={
            "required": f"Debe ingresar el {etiqueta}.",
            "invalid": f"El {etiqueta} debe ser un número entero de días.",
            "min_value": f"El {etiqueta} debe ser de al menos 1 día.",
            "max_value": f"El {etiqueta} no puede superar 365 días.",
        },
    )


def _validar_rangos(datos):
    errores = {}

    for codigo in ("20", "40"):
        minimo = datos.get(f"tarifa{codigo}_min")
        maximo = datos.get(f"tarifa{codigo}_max")

        if minimo is not None and maximo is not None and maximo < minimo:
            errores[f"tarifa{codigo}_max"] = [
                f"La tarifa máxima de {codigo}' no puede ser "
                "menor que la mínima."
            ]

    transito_min = datos.get("transito_min")
    transito_max = datos.get("transito_max")

    if (
        transito_min is not None
        and transito_max is not None
        and transito_max < transito_min
    ):
        errores["transito_max"] = [
            "El tránsito máximo no puede ser menor que el mínimo."
        ]

    if errores:
        raise serializers.ValidationError(errores)


def _sin_formula(valor, etiqueta):
    if valor.startswith(("=", "+", "-", "@")):
        raise serializers.ValidationError(
            f"El texto de {etiqueta} no puede comenzar con = + - @."
        )

    return valor


class CrearRutaSerializer(StrictSerializer):
    origen = _texto("el puerto de origen")
    pais_origen = _texto("el país de origen")
    destino = _texto("el puerto de destino")
    pais_destino = serializers.CharField(
        max_length=100,
        trim_whitespace=True,
        required=False,
        default=PAIS_DESTINO_POR_DEFECTO,
    )
    tipo_ruta = serializers.ChoiceField(
        choices=TIPOS_RUTA,
        error_messages={
            "required": "Debe indicar el tipo de ruta.",
            "invalid_choice": "El tipo de ruta no es válido.",
        },
    )
    tarifa20_min = _tarifa("tarifa mínima de 20'")
    tarifa20_max = _tarifa("tarifa máxima de 20'")
    tarifa40_min = _tarifa("tarifa mínima de 40'")
    tarifa40_max = _tarifa("tarifa máxima de 40'")
    transito_min = _dias("tránsito mínimo")
    transito_max = _dias("tránsito máximo")

    def validate_origen(self, value):
        return _sin_formula(value, "el puerto de origen")

    def validate_pais_origen(self, value):
        return _sin_formula(value, "el país de origen")

    def validate_destino(self, value):
        return _sin_formula(value, "el puerto de destino")

    def validate_pais_destino(self, value):
        return _sin_formula(
            value or PAIS_DESTINO_POR_DEFECTO,
            "el país de destino",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validar_rangos(attrs)

        mismo_puerto = (
            attrs["origen"].casefold() == attrs["destino"].casefold()
            and attrs["pais_origen"].casefold()
            == attrs["pais_destino"].casefold()
        )

        if mismo_puerto:
            raise serializers.ValidationError(
                {
                    "destino": [
                        "El puerto de destino debe ser distinto "
                        "al puerto de origen."
                    ]
                }
            )

        return attrs


class ActualizarRutaSerializer(StrictSerializer):
    tipo_ruta = serializers.ChoiceField(
        choices=TIPOS_RUTA,
        required=False,
        error_messages={
            "invalid_choice": "El tipo de ruta no es válido.",
        },
    )
    tarifa20_min = _tarifa("tarifa mínima de 20'", required=False)
    tarifa20_max = _tarifa("tarifa máxima de 20'", required=False)
    tarifa40_min = _tarifa("tarifa mínima de 40'", required=False)
    tarifa40_max = _tarifa("tarifa máxima de 40'", required=False)
    transito_min = _dias("tránsito mínimo", required=False)
    transito_max = _dias("tránsito máximo", required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if not attrs:
            raise serializers.ValidationError(
                {"detail": "No se indicó ningún cambio."}
            )

        return attrs


def _rutas_con_detalle():
    return (
        Ruta.objects
        .select_related(
            "puerto_origen",
            "puerto_destino",
            "tiempo_transito",
        )
        .prefetch_related(
            Prefetch(
                "tarifas",
                queryset=Tarifa.objects.order_by("tipo_contenedor"),
            )
        )
        .order_by(
            "puerto_origen__nombre",
            "puerto_destino__nombre",
        )
    )


def _representar_ruta(ruta):
    tarifas = {
        tarifa.tipo_contenedor: tarifa
        for tarifa in ruta.tarifas.all()
    }

    def _valor(codigo, atributo):
        tarifa = tarifas.get(codigo)
        return str(getattr(tarifa, atributo)) if tarifa else None

    try:
        transito = ruta.tiempo_transito
    except TiempoTransito.DoesNotExist:
        transito = None

    return {
        "id": ruta.id,
        "origen": ruta.puerto_origen.nombre,
        "paisOrigen": ruta.puerto_origen.pais,
        "destino": ruta.puerto_destino.nombre,
        "paisDestino": ruta.puerto_destino.pais,
        "tipoRuta": ruta.tipo_ruta,
        "tarifa20Min": _valor("20", "valor_minimo"),
        "tarifa20Max": _valor("20", "valor_maximo"),
        "tarifa40Min": _valor("40", "valor_minimo"),
        "tarifa40Max": _valor("40", "valor_maximo"),
        "transitoMin": transito.dias_minimos if transito else None,
        "transitoMax": transito.dias_maximos if transito else None,
    }


def _obtener_puerto(nombre, pais):
    """Reutiliza un puerto existente sin distinguir mayúsculas."""
    puerto = Puerto.objects.filter(
        nombre__iexact=nombre,
        pais__iexact=pais,
    ).first()

    if puerto is not None:
        return puerto, False

    return Puerto.objects.create(nombre=nombre, pais=pais), True


def _guardar_tarifa(ruta, codigo, minimo, maximo):
    Tarifa.objects.update_or_create(
        ruta=ruta,
        tipo_contenedor=codigo,
        defaults={
            "valor_minimo": minimo,
            "valor_maximo": maximo,
            "fuente": FUENTE_MANUAL,
        },
    )


@api_view(["GET", "POST"])
@permission_classes([PuedeGestionarDatos])
def rutas_admin(request):
    if request.method == "GET":
        return Response(
            {
                "tiposRuta": TIPOS_RUTA,
                "rutas": [
                    _representar_ruta(ruta)
                    for ruta in _rutas_con_detalle()
                ],
            },
            status=status.HTTP_200_OK,
        )

    serializer = CrearRutaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        return _crear_ruta(request, serializer.validated_data)

    except IntegrityError:
        # Dos personas crearon la misma ruta al mismo tiempo: la
        # restricción UNIQUE de PostgreSQL rechaza la segunda.
        return Response(
            {
                "detail": (
                    "La ruta o el puerto ya fue creado por otra "
                    "persona. Actualice la página."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )


def _crear_ruta(request, datos):
    with transaction.atomic():
        estado_previo = capturar_estado()

        origen, origen_creado = _obtener_puerto(
            datos["origen"],
            datos["pais_origen"],
        )
        destino, destino_creado = _obtener_puerto(
            datos["destino"],
            datos["pais_destino"],
        )

        if Ruta.objects.filter(
            puerto_origen=origen,
            puerto_destino=destino,
        ).exists():
            # Revierte los puertos que se hubieran creado.
            transaction.set_rollback(True)

            return Response(
                {
                    "detail": (
                        "Ya existe una ruta entre esos puertos. "
                        "Edítela para actualizar sus tarifas."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        ruta = Ruta.objects.create(
            puerto_origen=origen,
            puerto_destino=destino,
            tipo_ruta=datos["tipo_ruta"],
        )

        _guardar_tarifa(
            ruta, "20", datos["tarifa20_min"], datos["tarifa20_max"]
        )
        _guardar_tarifa(
            ruta, "40", datos["tarifa40_min"], datos["tarifa40_max"]
        )

        TiempoTransito.objects.create(
            ruta=ruta,
            dias_minimos=datos["transito_min"],
            dias_maximos=datos["transito_max"],
        )

        operacion = registrar_operacion(
            OperacionDatosMaestros.Tipo.EDICION_MANUAL,
            request.user,
            resumen={
                "accion": "ruta_creada",
                "ruta": f"{origen.nombre} → {destino.nombre}",
                "puertosCreados": int(origen_creado) + int(destino_creado),
                "estadoPrevio": resumir_estado(estado_previo),
            },
            estado_previo=estado_previo,
            detalle=f"Ruta creada: {origen.nombre} → {destino.nombre}",
        )

    ruta = _rutas_con_detalle().get(pk=ruta.pk)

    return Response(
        {
            "detail": (
                "Ruta creada correctamente. Ya está disponible "
                "en el cotizador."
            ),
            "operacionId": operacion.id,
            "ruta": _representar_ruta(ruta),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes([PuedeGestionarDatos])
def ruta_admin_detalle(request, ruta_id):
    ruta = _rutas_con_detalle().filter(pk=ruta_id).first()

    if ruta is None:
        return Response(
            {"detail": "La ruta no existe."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ActualizarRutaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    datos = serializer.validated_data

    actual = _representar_ruta(ruta)

    # Valores finales = actuales + cambios, para validar los rangos
    # aunque solo se envíe el mínimo o el máximo.
    finales = {
        "tipo_ruta": datos.get("tipo_ruta", ruta.tipo_ruta),
    }

    for campo, clave in (
        ("tarifa20_min", "tarifa20Min"),
        ("tarifa20_max", "tarifa20Max"),
        ("tarifa40_min", "tarifa40Min"),
        ("tarifa40_max", "tarifa40Max"),
    ):
        valor_actual = actual[clave]
        finales[campo] = datos.get(
            campo,
            Decimal(valor_actual) if valor_actual is not None else None,
        )

    finales["transito_min"] = datos.get(
        "transito_min", actual["transitoMin"]
    )
    finales["transito_max"] = datos.get(
        "transito_max", actual["transitoMax"]
    )

    incompletos = {}

    for codigo in ("20", "40"):
        par = (
            finales[f"tarifa{codigo}_min"],
            finales[f"tarifa{codigo}_max"],
        )
        if (par[0] is None) != (par[1] is None):
            incompletos[f"tarifa{codigo}_max"] = [
                f"Debe indicar la tarifa mínima y máxima de {codigo}'."
            ]

    if (finales["transito_min"] is None) != (
        finales["transito_max"] is None
    ):
        incompletos["transito_max"] = [
            "Debe indicar el tránsito mínimo y máximo."
        ]

    if incompletos:
        return Response(
            incompletos,
            status=status.HTTP_400_BAD_REQUEST,
        )

    _validar_rangos(finales)

    with transaction.atomic():
        estado_previo = capturar_estado()

        if finales["tipo_ruta"] != ruta.tipo_ruta:
            ruta.tipo_ruta = finales["tipo_ruta"]
            ruta.save(update_fields=["tipo_ruta"])

        for codigo in ("20", "40"):
            minimo = finales[f"tarifa{codigo}_min"]
            maximo = finales[f"tarifa{codigo}_max"]

            cambia = (
                f"tarifa{codigo}_min" in datos
                or f"tarifa{codigo}_max" in datos
            )

            if cambia and minimo is not None:
                _guardar_tarifa(ruta, codigo, minimo, maximo)

        if (
            ("transito_min" in datos or "transito_max" in datos)
            and finales["transito_min"] is not None
        ):
            TiempoTransito.objects.update_or_create(
                ruta=ruta,
                defaults={
                    "dias_minimos": finales["transito_min"],
                    "dias_maximos": finales["transito_max"],
                },
            )

        ruta = _rutas_con_detalle().get(pk=ruta.pk)
        nuevo = _representar_ruta(ruta)

        cambios = {
            clave: {"antes": actual[clave], "despues": nuevo[clave]}
            for clave in nuevo
            if nuevo[clave] != actual[clave]
        }

        if not cambios:
            transaction.set_rollback(True)

            return Response(
                {
                    "detail": "Los valores son iguales a los actuales.",
                    "ruta": nuevo,
                },
                status=status.HTTP_200_OK,
            )

        operacion = registrar_operacion(
            OperacionDatosMaestros.Tipo.EDICION_MANUAL,
            request.user,
            resumen={
                "accion": "ruta_actualizada",
                "ruta": f"{nuevo['origen']} → {nuevo['destino']}",
                "cambios": cambios,
                "estadoPrevio": resumir_estado(estado_previo),
            },
            estado_previo=estado_previo,
            detalle=(
                f"Ruta actualizada: {nuevo['origen']} → "
                f"{nuevo['destino']}"
            ),
        )

    return Response(
        {
            "detail": "Ruta actualizada correctamente.",
            "operacionId": operacion.id,
            "ruta": nuevo,
        },
        status=status.HTTP_200_OK,
    )
