from decimal import Decimal

from rest_framework import serializers

from .models import (
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)


class StrictSerializer(serializers.Serializer):
    """
    Rechaza cualquier campo que no forme parte
    del contrato definido para la API.
    """

    def to_internal_value(self, data):
        if not hasattr(data, "keys"):
            raise serializers.ValidationError(
                {
                    "detail":
                        "El formato de la solicitud no es válido."
                }
            )

        campos_recibidos = set(data.keys())
        campos_permitidos = set(self.fields.keys())

        campos_no_permitidos = (
            campos_recibidos
            - campos_permitidos
        )

        if campos_no_permitidos:
            lista_campos = sorted(
                campos_no_permitidos
            )

            raise serializers.ValidationError(
                {
                    "campos_no_permitidos": [
                        (
                            "La solicitud contiene campos "
                            "no permitidos: "
                            + ", ".join(lista_campos)
                        )
                    ]
                }
            )

        return super().to_internal_value(data)


class TipoContenedorSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = TipoContenedor

        fields = [
            "id",
            "codigo",
            "nombre",
            "capacidad_tn",
            "activo",
        ]


class TarifaSerializer(
    serializers.ModelSerializer
):
    tipoContenedor = serializers.CharField(
        source="tipo_contenedor",
        read_only=True,
    )

    valorMinimo = serializers.DecimalField(
        source="valor_minimo",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    valorMaximo = serializers.DecimalField(
        source="valor_maximo",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Tarifa

        fields = [
            "id",
            "tipoContenedor",
            "valorMinimo",
            "valorMaximo",
            "fuente",
        ]


class RutaSerializer(
    serializers.ModelSerializer
):
    origen = serializers.CharField(
        source="puerto_origen.nombre",
        read_only=True,
    )

    pais = serializers.CharField(
        source="puerto_origen.pais",
        read_only=True,
    )

    destino = serializers.CharField(
        source="puerto_destino.nombre",
        read_only=True,
    )

    tipoRuta = serializers.CharField(
        source="tipo_ruta",
        read_only=True,
    )

    transitoMin = (
        serializers.SerializerMethodField()
    )

    transitoMax = (
        serializers.SerializerMethodField()
    )

    tarifas = TarifaSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Ruta

        fields = [
            "id",
            "origen",
            "pais",
            "destino",
            "tipoRuta",
            "transitoMin",
            "transitoMax",
            "tarifas",
        ]

    def get_transitoMin(
        self,
        obj,
    ):
        try:
            return (
                obj
                .tiempo_transito
                .dias_minimos
            )

        except TiempoTransito.DoesNotExist:
            return None

    def get_transitoMax(
        self,
        obj,
    ):
        try:
            return (
                obj
                .tiempo_transito
                .dias_maximos
            )

        except TiempoTransito.DoesNotExist:
            return None


class OpcionesOperacionSerializer(
    StrictSerializer
):
    ruta_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required":
                "Debe indicar una ruta.",

            "invalid":
                "La ruta indicada no es válida.",

            "min_value":
                "La ruta indicada no es válida.",
        },
    )

    peso_carga = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=Decimal("0.001"),
        error_messages={
            "required":
                "Debe ingresar el peso de la carga.",

            "invalid":
                "El peso de la carga debe ser un valor numérico.",

            "min_value":
                "El peso de la carga debe ser mayor que cero.",

            "max_digits":
                "El peso ingresado excede el formato permitido.",

            "max_decimal_places":
                (
                    "El peso puede contener "
                    "como máximo tres decimales."
                ),
        },
    )

    unidad_peso = serializers.ChoiceField(
        choices=[
            "kg",
            "tn",
        ],
        error_messages={
            "required":
                "Debe indicar la unidad del peso.",

            "invalid_choice":
                "La unidad de peso debe ser kg o TN.",
        },
    )

    def validate_ruta_id(
        self,
        value,
    ):
        if not Ruta.objects.filter(
            id=value
        ).exists():
            raise serializers.ValidationError(
                "La ruta indicada no existe."
            )

        return value


class CotizacionOperacionSerializer(
    OpcionesOperacionSerializer
):
    tipo_contenedor = serializers.CharField(
        max_length=2,
        trim_whitespace=True,
        error_messages={
            "required":
                (
                    "Debe seleccionar un "
                    "tipo de contenedor."
                ),

            "blank":
                (
                    "Debe seleccionar un "
                    "tipo de contenedor."
                ),

            "max_length":
                (
                    "El tipo de contenedor "
                    "no es válido."
                ),
        },
    )

    contingencia = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
        error_messages={
            "invalid":
                (
                    "Los días de contingencia "
                    "deben ser un número entero."
                ),

            "min_value":
                (
                    "Los días de contingencia "
                    "no pueden ser negativos."
                ),
        },
    )

    def validate_tipo_contenedor(
        self,
        value,
    ):
        existe = (
            TipoContenedor.objects
            .filter(
                codigo=value,
                activo=True,
            )
            .exists()
        )

        if not existe:
            raise serializers.ValidationError(
                (
                    "El tipo de contenedor "
                    "no existe o se encuentra inactivo."
                )
            )

        return value

    def validate(
        self,
        attrs,
    ):
        attrs = super().validate(
            attrs
        )

        ruta_id = attrs.get(
            "ruta_id"
        )

        tipo_contenedor = attrs.get(
            "tipo_contenedor"
        )

        if (
            ruta_id is not None
            and tipo_contenedor
        ):
            tarifa_disponible = (
                Tarifa.objects
                .filter(
                    ruta_id=ruta_id,
                    tipo_contenedor=
                        tipo_contenedor,
                )
                .exists()
            )

            if not tarifa_disponible:
                raise serializers.ValidationError(
                    {
                        "tipo_contenedor": [
                            (
                                "No existe una tarifa "
                                "registrada para este "
                                "tipo de contenedor en "
                                "la ruta seleccionada."
                            )
                        ]
                    }
                )

        return attrs