"""
Inicialización segura e idempotente del entorno de producción.

Se ejecuta en cada despliegue de Render (``build.sh``). Por eso debe
poder repetirse cualquier número de veces sin alterar información que
ya existe en PostgreSQL:

* Los datos maestros (rutas, tarifas, tránsitos) se cargan SOLO en una
  instalación nueva, es decir, cuando la base no tiene rutas.
* Los tipos de contenedor se crean si faltan, pero nunca se
  sobrescribe una capacidad ya registrada.
* El tipo de cambio de respaldo solo se crea si no existe ningún
  registro USD/CLP.
* El administrador técnico se crea si no existe. Si ya existe, NO se
  cambia su contraseña ni se elevan privilegios de una cuenta común.
  Restablecer la contraseña requiere activar explícitamente
  ``BOOTSTRAP_RESET_ADMIN_PASSWORD=true`` durante un único despliegue.
"""

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
from django.db import transaction

from cotizador.models import (
    PerfilUsuario,
    Ruta,
    TipoCambio,
    TipoContenedor,
)


CONTENEDORES_BASE = (
    ("20", "Contenedor 20'", Decimal("23.00")),
    ("40", "Contenedor 40'", Decimal("25.00")),
)

VALORES_VERDADEROS = {
    "1",
    "true",
    "si",
    "sí",
    "yes",
}


def _bandera_activa(nombre):
    return (
        os.getenv(nombre, "")
        .strip()
        .lower()
        in VALORES_VERDADEROS
    )


class Command(BaseCommand):
    help = (
        "Inicializa CINTAC de forma idempotente: carga datos "
        "maestros solo en una instalación nueva, conserva tarifas, "
        "capacidades y contraseñas existentes y crea el "
        "administrador técnico únicamente si no existe."
    )

    # ------------------------------------------------------------------
    # Datos maestros
    # ------------------------------------------------------------------

    def _inicializar_datos_maestros(self):
        if Ruta.objects.exists():
            self.stdout.write(
                "Datos maestros existentes conservados "
                "(no se sobrescriben tarifas ni tránsitos)."
            )

            creados = 0

            for codigo, nombre, capacidad in CONTENEDORES_BASE:
                _, creado = TipoContenedor.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "capacidad_tn": capacidad,
                        "activo": True,
                    },
                )

                creados += int(creado)

            if creados:
                self.stdout.write(
                    f"Tipos de contenedor faltantes creados: {creados}."
                )

            return

        self.stdout.write(
            "Instalación nueva detectada: cargando datos maestros..."
        )

        call_command(
            "cargar_datos",
            verbosity=0,
        )

    # ------------------------------------------------------------------
    # Tipo de cambio de respaldo
    # ------------------------------------------------------------------

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
                    "Tipo de cambio de respaldo no configurado."
                )
            )
            return

        try:
            valor = Decimal(valor_texto)
            fecha_referencia = date.fromisoformat(fecha_texto)

        except (InvalidOperation, ValueError) as error:
            raise CommandError(
                "El tipo de cambio de respaldo no tiene "
                "un formato válido."
            ) from error

        if not valor.is_finite() or valor <= 0:
            raise CommandError(
                "El tipo de cambio de respaldo debe ser "
                "mayor que cero."
            )

        existe_respaldo = TipoCambio.objects.filter(
            moneda_origen="USD",
            moneda_destino="CLP",
        ).exists()

        if existe_respaldo:
            self.stdout.write(
                "Tipo de cambio de respaldo: ya existe "
                "un registro previo (conservado)."
            )
            return

        TipoCambio.objects.create(
            moneda_origen="USD",
            moneda_destino="CLP",
            valor=valor,
            fecha_referencia=fecha_referencia,
            fuente=fuente,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Tipo de cambio de respaldo creado: "
                f"{valor} CLP/USD."
            )
        )

    # ------------------------------------------------------------------
    # Administrador técnico
    # ------------------------------------------------------------------

    def _asegurar_administrador(
        self,
        username,
        password,
        email,
    ):
        usuario = User.objects.filter(
            username=username
        ).first()

        if usuario is None:
            if not password:
                raise CommandError(
                    "Debe configurar DJANGO_SUPERUSER_PASSWORD "
                    "para crear el administrador inicial."
                )

            usuario = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )

            perfil, _ = PerfilUsuario.objects.get_or_create(
                usuario=usuario
            )
            perfil.rol = PerfilUsuario.Rol.ADMINISTRADOR
            perfil.autorizado = True
            perfil.puede_gestionar_datos = True
            perfil.save(
                update_fields=[
                    "rol",
                    "autorizado",
                    "puede_gestionar_datos",
                ]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Administrador de producción creado: {username}"
                )
            )
            return

        if not usuario.is_superuser:
            # Nunca se elevan privilegios de una cuenta existente
            # por el solo hecho de compartir el nombre configurado.
            self.stdout.write(
                self.style.WARNING(
                    f"La cuenta '{username}' existe pero no es "
                    "superusuario. Se conserva sin cambios y NO se "
                    "elevan sus privilegios."
                )
            )
            return

        PerfilUsuario.objects.get_or_create(
            usuario=usuario,
            defaults={
                "rol": PerfilUsuario.Rol.ADMINISTRADOR,
                "autorizado": True,
                "puede_gestionar_datos": True,
            },
        )

        if _bandera_activa("BOOTSTRAP_RESET_ADMIN_PASSWORD"):
            if not password:
                raise CommandError(
                    "BOOTSTRAP_RESET_ADMIN_PASSWORD está activo, "
                    "pero DJANGO_SUPERUSER_PASSWORD está vacío."
                )

            usuario.set_password(password)
            usuario.save(update_fields=["password"])

            self.stdout.write(
                self.style.WARNING(
                    "Contraseña del administrador restablecida por "
                    "solicitud explícita. Desactive "
                    "BOOTSTRAP_RESET_ADMIN_PASSWORD después de este "
                    "despliegue."
                )
            )
            return

        self.stdout.write(
            "Cuenta administrativa existente conservada "
            "(contraseña y permisos sin modificar)."
        )

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        username = os.getenv(
            "DJANGO_SUPERUSER_USERNAME",
            "",
        ).strip()

        password = os.getenv(
            "DJANGO_SUPERUSER_PASSWORD",
            "",
        )

        email = os.getenv(
            "DJANGO_SUPERUSER_EMAIL",
            "",
        ).strip()

        if not username:
            raise CommandError(
                "Debe configurar DJANGO_SUPERUSER_USERNAME."
            )

        with transaction.atomic():
            self._inicializar_datos_maestros()
            self._cargar_tipo_cambio_respaldo()
            self._asegurar_administrador(
                username,
                password,
                email,
            )
