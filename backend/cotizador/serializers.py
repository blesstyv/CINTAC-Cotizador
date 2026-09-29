from decimal import Decimal

from rest_framework import serializers

from .models import (
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)


class TipoContenedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoContenedor
        fields = [
            "id",
            "codigo",
            "nombre",
            "capacidad_tn",
            "activo",
        ]


class TarifaSerializer(serializers.ModelSerializer):
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


class RutaSerializer(serializers.ModelSerializer):
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

    transitoMin = serializers.SerializerMethodField()
    transitoMax = serializers.SerializerMethodField()

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

    def get_transitoMin(self, obj):
        try:
            return obj.tiempo_transito.dias_minimos
        except TiempoTransito.DoesNotExist:
            return None

    def get_transitoMax(self, obj):
        try:
            return obj.tiempo_transito.dias_maximos
        except TiempoTransito.DoesNotExist:
            return None


class OpcionesOperacionSerializer(serializers.Serializer):
    ruta_id = serializers.IntegerField(
        min_value=1,
    )

    peso_carga = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )

    unidad_peso = serializers.ChoiceField(
        choices=[
            "kg",
            "tn",
        ]
    )


class CotizacionOperacionSerializer(
    OpcionesOperacionSerializer
):
    tipo_contenedor = serializers.CharField(
        max_length=2,
    )

    contingencia = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    tipo_cambio = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        min_value=Decimal("0.0001"),
        required=False,
        allow_null=True,
    )