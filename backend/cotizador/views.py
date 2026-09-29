from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import TipoContenedor
from .serializers import TipoContenedorSerializer


@api_view(["GET"])
def listar_tipos_contenedor(request):
    tipos = TipoContenedor.objects.filter(
        activo=True
    ).order_by("codigo")

    serializer = TipoContenedorSerializer(
        tipos,
        many=True,
    )

    return Response(serializer.data)