from rest_framework import serializers

from .models import Ruta, Tarifa, TiempoTransito, TipoContenedor


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