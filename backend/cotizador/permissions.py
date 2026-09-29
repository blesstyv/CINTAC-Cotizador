from rest_framework.permissions import BasePermission


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

        try:
            return (
                usuario
                .perfil_cintac
                .autorizado
            )

        except AttributeError:
            return False