from rest_framework import serializers

from .models import TipoContenedor


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