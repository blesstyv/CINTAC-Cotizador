from django.db.models import Prefetch
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Ruta, Tarifa, TipoContenedor
from .serializers import (
    RutaSerializer,
    TipoContenedorSerializer,
)


@api_view(["GET"])
def listar_tipos_contenedor(request):
    tipos = TipoContenedor.objects.filter(
        activo=True
    ).order_by("id")

    serializer = TipoContenedorSerializer(
        tipos,
        many=True,
    )

    return Response(serializer.data)


@api_view(["GET"])
def listar_rutas(request):
    tarifas_ordenadas = Tarifa.objects.order_by("id")

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
                queryset=tarifas_ordenadas,
            )
        )
        .order_by("id")
    )

    serializer = RutaSerializer(
        rutas,
        many=True,
    )

    return Response(serializer.data)