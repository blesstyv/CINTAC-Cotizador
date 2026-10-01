from rest_framework.permissions import BasePermission

from .models import PerfilUsuario


def obtener_perfil_vigente(usuario):
    if (
        not usuario
        or not usuario.is_authenticated
        or not usuario.is_active
    ):
        return None

    return (
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


class EsUsuarioAutorizado(BasePermission):
    message = (
        "El usuario no está autorizado "
        "para acceder al cotizador."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        usuario = request.user

        if (
            not usuario
            or not usuario.is_authenticated
            or not usuario.is_active
        ):
            return False

        if usuario.is_superuser:
            return True

        perfil = obtener_perfil_vigente(
            usuario
        )

        if not perfil:
            return False

        return bool(
            perfil["autorizado"]
        )


class PuedeGestionarDatos(BasePermission):
    message = (
        "El usuario no tiene permiso "
        "para gestionar los datos maestros."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        usuario = request.user

        if (
            not usuario
            or not usuario.is_authenticated
            or not usuario.is_active
        ):
            return False

        if usuario.is_superuser:
            return True

        perfil = obtener_perfil_vigente(
            usuario
        )

        if not perfil:
            return False

        return (
            bool(
                perfil["autorizado"]
            )
            and
            bool(
                perfil[
                    "puede_gestionar_datos"
                ]
            )
        )