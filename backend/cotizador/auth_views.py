import hashlib
import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache

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


logger = logging.getLogger("cotizador.seguridad")


def _clave_fallos(username):
    # Se usa un hash para no guardar nombres de usuario en la caché.
    resumen = hashlib.sha256(
        username.strip().lower().encode("utf-8")
    ).hexdigest()

    return f"cintac:login_fallos:{resumen}"


def _cuenta_bloqueada(username):
    return (
        cache.get(_clave_fallos(username), 0)
        >= settings.LOGIN_MAX_FALLOS
    )


def _registrar_fallo(username):
    clave = _clave_fallos(username)
    ventana = settings.LOGIN_BLOQUEO_SEGUNDOS

    if cache.add(clave, 1, ventana):
        return 1

    try:
        return cache.incr(clave)

    except ValueError:
        cache.set(clave, 1, ventana)
        return 1


def _limpiar_fallos(username):
    cache.delete(_clave_fallos(username))


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
            "puedeGestionarUsuarios": False,
            "rol": None,
            "rolNombre": None,
        }

    if usuario.is_superuser:
        return {
            "autorizado": True,
            "puedeGestionarDatos": True,
            "puedeGestionarUsuarios": True,
            "rol":
                PerfilUsuario
                .Rol
                .ADMINISTRADOR,
            "rolNombre":
                "Administrador técnico",
        }

    perfil = (
        PerfilUsuario.objects
        .filter(
            usuario_id=usuario.id
        )
        .first()
    )

    if not perfil:
        return {
            "autorizado": False,
            "puedeGestionarDatos": False,
            "puedeGestionarUsuarios": False,
            "rol": None,
            "rolNombre": None,
        }

    autorizado = bool(
        perfil.autorizado
    )

    puede_gestionar_datos = (
        autorizado
        and
        (
            bool(
                perfil
                .puede_gestionar_datos
            )
            or
            perfil.rol
            in {
                PerfilUsuario
                .Rol
                .ENCARGADO,

                PerfilUsuario
                .Rol
                .ADMINISTRADOR,
            }
        )
    )

    puede_gestionar_usuarios = (
        autorizado
        and
        perfil.rol
        == PerfilUsuario
        .Rol
        .ADMINISTRADOR
    )

    return {
        "autorizado":
            autorizado,

        "puedeGestionarDatos":
            puede_gestionar_datos,

        "puedeGestionarUsuarios":
            puede_gestionar_usuarios,

        "rol":
            perfil.rol,

        "rolNombre":
            perfil.get_rol_display(),
    }


def _datos_usuario(
    usuario,
):
    permisos = (
        obtener_permisos_usuario(
            usuario
        )
    )

    return {
        "id":
            usuario.id,

        "username":
            usuario.username,

        "nombre":
            (
                usuario.get_full_name()
                or usuario.username
            ),

        "email":
            usuario.email,

        "rol":
            permisos[
                "rol"
            ],

        "rolNombre":
            permisos[
                "rolNombre"
            ],

        "autorizado":
            permisos[
                "autorizado"
            ],

        "puedeGestionarDatos":
            permisos[
                "puedeGestionarDatos"
            ],

        "puedeGestionarUsuarios":
            permisos[
                "puedeGestionarUsuarios"
            ],
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

    if _cuenta_bloqueada(username):
        logger.warning(
            "Inicio de sesión bloqueado temporalmente por "
            "intentos fallidos consecutivos."
        )

        return Response(
            {
                "detail":
                    (
                        "Se superó el número de intentos "
                        "fallidos. Espere unos minutos e "
                        "intente nuevamente."
                    )
            },
            status=
                status.HTTP_429_TOO_MANY_REQUESTS,
        )

    usuario = authenticate(
        request=request,
        username=username,
        password=password,
    )

    if usuario is None:
        _registrar_fallo(username)

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

    _limpiar_fallos(username)

    Token.objects.filter(
        user=usuario
    ).delete()

    token = Token.objects.create(
        user=usuario
    )

    return Response(
        {
            "token":
                token.key,

            "usuario":
                _datos_usuario(
                    usuario
                ),
        },
        status=
            status.HTTP_200_OK,
    )


@api_view(["GET"])
def sesion_actual(request):
    return Response(
        _datos_usuario(
            request.user
        ),
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