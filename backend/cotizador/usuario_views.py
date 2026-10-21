from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework import status

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.response import Response

from .models import PerfilUsuario

from .permissions import (
    PuedeGestionarUsuarios,
)

from .usuario_serializers import (
    ActualizarUsuarioSerializer,
    CrearUsuarioSerializer,
)


def _representar_usuario(
    usuario,
):
    perfil = (
        usuario.perfil_cintac
    )

    return {
        "id":
            usuario.id,

        "username":
            usuario.username,

        "firstName":
            usuario.first_name,

        "lastName":
            usuario.last_name,

        "nombre":
            (
                usuario.get_full_name()
                or usuario.username
            ),

        "email":
            usuario.email,

        "rol":
            (
                PerfilUsuario
                .Rol
                .ADMINISTRADOR
                if usuario.is_superuser
                else perfil.rol
            ),

        "rolNombre":
            (
                "Administrador técnico"
                if usuario.is_superuser
                else perfil.get_rol_display()
            ),

        "activo":
            usuario.is_active,

        "autorizado":
            (
                True
                if usuario.is_superuser
                else perfil.autorizado
            ),

        "puedeGestionarDatos":
            (
                True
                if usuario.is_superuser
                else
                perfil.puede_gestionar_datos
            ),

        "puedeGestionarUsuarios":
            (
                usuario.is_superuser
                or
                perfil.rol
                == PerfilUsuario
                .Rol
                .ADMINISTRADOR
            ),

        "protegido":
            usuario.is_superuser,

        "ultimoAcceso":
            (
                usuario.last_login.isoformat()
                if usuario.last_login
                else None
            ),

        "fechaCreacion":
            usuario.date_joined.isoformat(),
    }


@api_view(
    [
        "GET",
        "POST",
    ]
)
@permission_classes(
    [PuedeGestionarUsuarios]
)
def usuarios(
    request,
):
    if request.method == "GET":
        consulta = (
            User.objects
            .select_related(
                "perfil_cintac"
            )
            .order_by(
                "username"
            )
        )

        busqueda = str(
            request.query_params.get(
                "q",
                "",
            )
        ).strip()

        if busqueda:
            consulta = consulta.filter(
                Q(
                    username__icontains=
                        busqueda
                )
                |
                Q(
                    first_name__icontains=
                        busqueda
                )
                |
                Q(
                    last_name__icontains=
                        busqueda
                )
                |
                Q(
                    email__icontains=
                        busqueda
                )
            )

        rol = str(
            request.query_params.get(
                "rol",
                "",
            )
        ).strip().upper()

        if rol:
            roles_validos = {
                valor
                for (
                    valor,
                    _
                )
                in PerfilUsuario
                .Rol
                .choices
            }

            if rol not in roles_validos:
                return Response(
                    {
                        "detail":
                            (
                                "El filtro de rol "
                                "no es válido."
                            )
                    },
                    status=
                        status
                        .HTTP_400_BAD_REQUEST,
                )

            consulta = (
                consulta.filter(
                    perfil_cintac__rol=
                        rol
                )
            )

        resultado = [
            _representar_usuario(
                usuario
            )
            for usuario
            in consulta
        ]

        return Response(
            {
                "cantidad":
                    len(resultado),

                "usuarios":
                    resultado,
            },
            status=
                status.HTTP_200_OK,
        )

    serializer = (
        CrearUsuarioSerializer(
            data=request.data
        )
    )

    serializer.is_valid(
        raise_exception=True
    )

    usuario = serializer.save()

    return Response(
        {
            "detail":
                (
                    "Usuario creado "
                    "correctamente."
                ),

            "usuario":
                _representar_usuario(
                    usuario
                ),
        },
        status=
            status.HTTP_201_CREATED,
    )


@api_view(
    [
        "GET",
        "PATCH",
    ]
)
@permission_classes(
    [PuedeGestionarUsuarios]
)
def usuario_detalle(
    request,
    usuario_id,
):
    try:
        usuario = (
            User.objects
            .select_related(
                "perfil_cintac"
            )
            .get(
                id=usuario_id
            )
        )

    except User.DoesNotExist:
        return Response(
            {
                "detail":
                    "El usuario no existe."
            },
            status=
                status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(
            {
                "usuario":
                    _representar_usuario(
                        usuario
                    )
            },
            status=
                status.HTTP_200_OK,
        )

    if usuario.is_superuser:
        return Response(
            {
                "detail":
                    (
                        "Los superusuarios "
                        "deben administrarse "
                        "desde la consola "
                        "técnica."
                    )
            },
            status=
                status.HTTP_400_BAD_REQUEST,
        )

    serializer = (
        ActualizarUsuarioSerializer(
            usuario,
            data=request.data,
            partial=True,
            context={
                "request":
                    request,
            },
        )
    )

    serializer.is_valid(
        raise_exception=True
    )

    usuario = serializer.save()

    return Response(
        {
            "detail":
                (
                    "Usuario actualizado "
                    "correctamente."
                ),

            "usuario":
                _representar_usuario(
                    usuario
                ),
        },
        status=
            status.HTTP_200_OK,
    )