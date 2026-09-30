from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from rest_framework.authentication import (
    TokenAuthentication,
)
from rest_framework.exceptions import (
    AuthenticationFailed,
)


class ExpiringTokenAuthentication(
    TokenAuthentication
):
    def authenticate_credentials(
        self,
        key,
    ):
        usuario, token = (
            super()
            .authenticate_credentials(
                key
            )
        )

        expiracion = (
            token.created
            + timedelta(
                hours=
                    settings
                    .TOKEN_EXPIRATION_HOURS
            )
        )

        if timezone.now() >= expiracion:
            token.delete()

            raise AuthenticationFailed(
                (
                    "La sesión ha expirado. "
                    "Inicie sesión nuevamente."
                )
            )

        return (
            usuario,
            token,
        )