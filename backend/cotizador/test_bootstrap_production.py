import os

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from cotizador.models import TipoCambio


class BootstrapProduccionTests(TestCase):
    def _entorno(self):
        return {
            "DJANGO_SUPERUSER_USERNAME":
                "admin_prueba",
            "DJANGO_SUPERUSER_PASSWORD":
                "ClaveSegura123!",
            "DJANGO_SUPERUSER_EMAIL":
                "admin@example.com",
            "USD_CLP_FALLBACK_VALUE":
                "976.82",
            "USD_CLP_FALLBACK_DATE":
                "2026-10-22",
            "USD_CLP_FALLBACK_SOURCE":
                (
                    "Banco Central de Chile "
                    "- Dolar Observado"
                ),
        }

    def test_bootstrap_crea_respaldo_y_admin(self):
        with patch.dict(
            os.environ,
            self._entorno(),
            clear=False,
        ):
            call_command(
                "bootstrap_production",
                verbosity=0,
            )

        cambio = (
            TipoCambio.objects.get(
                moneda_origen="USD",
                moneda_destino="CLP",
            )
        )

        self.assertEqual(
            cambio.valor,
            Decimal("976.8200"),
        )

        self.assertEqual(
            cambio.fecha_referencia,
            date(2026, 10, 22),
        )

        usuario = User.objects.get(
            username="admin_prueba"
        )

        self.assertTrue(
            usuario.is_active
        )

        self.assertTrue(
            usuario.is_staff
        )

        self.assertTrue(
            usuario.is_superuser
        )

    def test_bootstrap_no_sobrescribe_cambio_existente(self):
        TipoCambio.objects.create(
            moneda_origen="USD",
            moneda_destino="CLP",
            valor=Decimal("950.0000"),
            fecha_referencia=
                date(2026, 10, 20),
            fuente="Registro previo",
        )

        with patch.dict(
            os.environ,
            self._entorno(),
            clear=False,
        ):
            call_command(
                "bootstrap_production",
                verbosity=0,
            )

        self.assertEqual(
            TipoCambio.objects.count(),
            1,
        )

        cambio = (
            TipoCambio.objects.get()
        )

        self.assertEqual(
            cambio.valor,
            Decimal("950.0000"),
        )
