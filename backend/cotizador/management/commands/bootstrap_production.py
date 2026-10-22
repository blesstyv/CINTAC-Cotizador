import os

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from cotizador.models import PerfilUsuario


class Command(BaseCommand):
    help = (
        "Inicializa los datos de CINTAC y crea "
        "o actualiza el administrador de producción."
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
