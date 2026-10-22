import os

from datetime import date

from decimal import (
    Decimal,
    InvalidOperation,
)

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from cotizador.models import (
    PerfilUsuario,
    TipoCambio,
)


class Command(BaseCommand):
    help = (
        "Inicializa los datos de CINTAC, carga "
        "un tipo de cambio de respaldo y crea "
        "o actualiza el administrador de producción."
    )

    def _cargar_tipo_cambio_respaldo(self):
        valor_texto = os.getenv(
            "USD_CLP_FALLBACK_VALUE",
            "",
        ).strip()

        fecha_texto = os.getenv(
            "USD_CLP_FALLBACK_DATE",
            "",
        ).strip()

        fuente = os.getenv(
            "USD_CLP_FALLBACK_SOURCE",
            "Banco Central de Chile - Dolar Observado",
        ).strip()

        if not valor_texto or not fecha_texto:
            self.stdout.write(
                self.style.WARNING(
                    (
                        "Tipo de cambio de respaldo "
                        "no configurado."
                    )
                )
            )
            return

        try:
            valor = Decimal(
                valor_texto
            )

            fecha_referencia = (
                date.fromisoformat(
                    fecha_texto
                )
            )

        except (
            InvalidOperation,
            ValueError,
        ) as error:
            raise CommandError(
                (
                    "El tipo de cambio de respaldo "
                    "no tiene un formato válido."
                )
            ) from error

        if valor <= 0:
            raise CommandError(
                (
                    "El tipo de cambio de respaldo "
                    "debe ser mayor que cero."
                )
            )

        existe_respaldo = (
            TipoCambio.objects
            .filter(
                moneda_origen="USD",
                moneda_destino="CLP",
            )
            .exists()
        )

        if existe_respaldo:
            self.stdout.write(
                (
                    "Tipo de cambio de respaldo: "
                    "ya existe un registro previo."
                )
            )
            return

        TipoCambio.objects.create(
            moneda_origen="USD",
            moneda_destino="CLP",
            valor=valor,
            fecha_referencia=
                fecha_referencia,
            fuente=fuente,
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Tipo de cambio de respaldo "
                    f"creado: {valor} CLP/USD."
                )
            )
        )

    def handle(self, *args, **options):
        username = os.getenv(
            "DJANGO_SUPERUSER_USERNAME",
            ""
        ).strip()

        password = os.getenv(
            "DJANGO_SUPERUSER_PASSWORD",
            ""
        )

        email = os.getenv(
            "DJANGO_SUPERUSER_EMAIL",
            ""
        ).strip()

        if not username or not password:
            raise CommandError(
                "Debe configurar DJANGO_SUPERUSER_USERNAME "
                "y DJANGO_SUPERUSER_PASSWORD."
            )

        self.stdout.write(
            "Cargando datos iniciales..."
        )

        call_command(
            "cargar_datos"
        )

        self._cargar_tipo_cambio_respaldo()

        usuario, creado = (
            User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                },
            )
        )

        usuario.email = email
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True
        usuario.set_password(
            password
        )
        usuario.save()

        perfil, _ = (
            PerfilUsuario.objects.get_or_create(
                usuario=usuario
            )
        )

        perfil.rol = (
            PerfilUsuario.Rol.ADMINISTRADOR
        )
        perfil.autorizado = True
        perfil.puede_gestionar_datos = True
        perfil.save(
            update_fields=[
                "rol",
                "autorizado",
                "puede_gestionar_datos",
            ]
        )

        estado = (
            "creado"
            if creado
            else "actualizado"
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Administrador de producción "
                    f"{estado}: {username}"
                )
            )
        )
