from django.contrib.auth import authenticate

from rest_framework import status

from rest_framework.authtoken.models import Token

from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)

from rest_framework.permissions import AllowAny

from rest_framework.response import Response


from .models import PerfilUsuario

from .throttles import (
    LoginRateThrottle,
)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes(
    [LoginRateThrottle]
)
def iniciar_sesion(request):
    username = str(
        request.data.get(
            "username",
            "",
        )
    ).strip()

    password = str(
        request.data.get(
            "password",
            "",
        )
    )

    if (
        not username
        or not password
    ):
        return Response(
            {
                "detail":
                    "Debe ingresar usuario y contraseña."
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )


    usuario = authenticate(
        request=request,
        username=username,
        password=password,
    )


    if usuario is None:
        return Response(
            {
                "detail":
                    "Usuario o contraseña incorrectos."
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )


    if not usuario.is_active:
        return Response(
            {
                "detail":
                    "El usuario no se encuentra activo."
            },
            status=
                status.HTTP_403_FORBIDDEN,
        )


    if not usuario.is_superuser:
        autorizado = (
            PerfilUsuario.objects
            .filter(
                usuario=usuario,
                autorizado=True,
            )
            .exists()
        )

        if not autorizado:
            return Response(
                {
                    "detail":
                        (
                            "El usuario no está autorizado "
                            "para acceder al cotizador."
                        )
                },
                status=
                    status.HTTP_403_FORBIDDEN,
            )


    Token.objects.filter(
        user=usuario
    ).delete()


    token = Token.objects.create(
        user=usuario
    )


    nombre = (
        usuario.get_full_name()
        or usuario.username
    )


    return Response(
        {
            "token":
                token.key,

            "usuario": {
                "id":
                    usuario.id,

                "username":
                    usuario.username,

                "nombre":
                    nombre,
            },
        },
        status=
            status.HTTP_200_OK,
    )


@api_view(["GET"])
def sesion_actual(request):
    usuario = request.user

    return Response(
        {
            "id":
                usuario.id,

            "username":
                usuario.username,

            "nombre":
                (
                    usuario.get_full_name()
                    or usuario.username
                ),

            "autorizado":
                True,
        }
    )


@api_view(["POST"])
def cerrar_sesion(request):
    if request.auth:
        request.auth.delete()

    return Response(
        {
            "detail":
                "Sesión cerrada correctamente."
        },
        status=
            status.HTTP_200_OK,
    )