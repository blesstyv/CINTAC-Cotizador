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


def obtener_permisos_usuario(
    usuario,
):
    if (
        not usuario
        or not usuario.is_authenticated
        or not usuario.is_active
    ):
        return {
            "autorizado": False,
            "puedeGestionarDatos": False,
        }

    if usuario.is_superuser:
        return {
            "autorizado": True,
            "puedeGestionarDatos": True,
        }

    perfil = (
        PerfilUsuario.objects
        .filter(
            usuario_id=usuario.id
        )
        .values(
            "autorizado",
            "puede_gestionar_datos",
        )
        .first()
    )

    if not perfil:
        return {
            "autorizado": False,
            "puedeGestionarDatos": False,
        }

    autorizado = bool(
        perfil["autorizado"]
    )

    puede_gestionar = (
        autorizado
        and
        bool(
            perfil[
                "puede_gestionar_datos"
            ]
        )
    )

    return {
        "autorizado":
            autorizado,

        "puedeGestionarDatos":
            puede_gestionar,
    }


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
                    (
                        "Debe ingresar usuario "
                        "y contraseña."
                    )
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
                    (
                        "Usuario o contraseña "
                        "incorrectos."
                    )
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    if not usuario.is_active:
        return Response(
            {
                "detail":
                    (
                        "El usuario no se "
                        "encuentra activo."
                    )
            },
            status=
                status.HTTP_403_FORBIDDEN,
        )

    permisos = (
        obtener_permisos_usuario(
            usuario
        )
    )

    if not permisos[
        "autorizado"
    ]:
        return Response(
            {
                "detail":
                    (
                        "El usuario no está "
                        "autorizado para acceder "
                        "al cotizador."
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

                "autorizado":
                    True,

                "puedeGestionarDatos":
                    permisos[
                        "puedeGestionarDatos"
                    ],
            },
        },
        status=
            status.HTTP_200_OK,
    )


@api_view(["GET"])
def sesion_actual(request):
    usuario = request.user

    permisos = (
        obtener_permisos_usuario(
            usuario
        )
    )

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
                permisos[
                    "autorizado"
                ],

            "puedeGestionarDatos":
                permisos[
                    "puedeGestionarDatos"
                ],
        },
        status=
            status.HTTP_200_OK,
    )


@api_view(["POST"])
def cerrar_sesion(request):
    if request.auth:
        request.auth.delete()

    return Response(
        {
            "detail":
                (
                    "Sesión cerrada "
                    "correctamente."
                )
        },
        status=
            status.HTTP_200_OK,
    )