import os

from io import StringIO

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from cotizador.models import (
    PerfilUsuario,
    Ruta,
    Tarifa,
    TipoCambio,
    TipoContenedor,
)


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


class BootstrapIdempotenteTests(TestCase):
    """
    BD01: un redeploy en Render no debe sobrescribir tarifas,
    capacidades ni contraseñas, ni elevar privilegios.
    """

    def _entorno(self, **extra):
        entorno = {
            "DJANGO_SUPERUSER_USERNAME": "admin_prueba",
            "DJANGO_SUPERUSER_PASSWORD": "ClaveSegura123!",
            "DJANGO_SUPERUSER_EMAIL": "admin@example.com",
            "USD_CLP_FALLBACK_VALUE": "976.82",
            "USD_CLP_FALLBACK_DATE": "2026-10-22",
            "BOOTSTRAP_RESET_ADMIN_PASSWORD": "",
        }
        entorno.update(extra)
        return entorno

    def _ejecutar(self, **extra):
        with patch.dict(os.environ, self._entorno(**extra), clear=False):
            call_command("bootstrap_production", verbosity=0, stdout=StringIO())

    def test_instalacion_nueva_carga_datos_maestros(self):
        self.assertFalse(Ruta.objects.exists())
        self._ejecutar()
        self.assertTrue(Ruta.objects.exists())
        self.assertTrue(Tarifa.objects.exists())
        self.assertEqual(TipoContenedor.objects.count(), 2)

    def test_redeploy_conserva_password_tarifas_y_capacidad(self):
        self._ejecutar()

        usuario = User.objects.get(username="admin_prueba")
        usuario.set_password("PasswordActualizada567!")
        usuario.save(update_fields=["password"])

        tarifa = Tarifa.objects.order_by("id").first()
        tarifa.valor_minimo = Decimal("1234.56")
        tarifa.valor_maximo = Decimal("4321.00")
        tarifa.save()

        contenedor = TipoContenedor.objects.get(codigo="20")
        contenedor.capacidad_tn = Decimal("24.00")
        contenedor.save(update_fields=["capacidad_tn"])

        rutas_antes = Ruta.objects.count()

        self._ejecutar(DJANGO_SUPERUSER_PASSWORD="OtraClaveDistinta999!")

        usuario.refresh_from_db()
        tarifa.refresh_from_db()
        contenedor.refresh_from_db()

        self.assertTrue(usuario.check_password("PasswordActualizada567!"))
        self.assertEqual(tarifa.valor_minimo, Decimal("1234.56"))
        self.assertEqual(tarifa.valor_maximo, Decimal("4321.00"))
        self.assertEqual(contenedor.capacidad_tn, Decimal("24.00"))
        self.assertEqual(Ruta.objects.count(), rutas_antes)
        self.assertEqual(User.objects.filter(username="admin_prueba").count(), 1)

    def test_redeploy_no_reactiva_perfil_modificado(self):
        self._ejecutar()
        perfil = PerfilUsuario.objects.get(usuario__username="admin_prueba")
        perfil.puede_gestionar_datos = False
        perfil.save(update_fields=["puede_gestionar_datos"])

        self._ejecutar()

        perfil.refresh_from_db()
        self.assertFalse(perfil.puede_gestionar_datos)

    def test_no_eleva_cuenta_comun_con_mismo_nombre(self):
        comun = User.objects.create_user(
            username="admin_prueba",
            password="ClaveUsuario123!",
        )

        self._ejecutar()

        comun.refresh_from_db()
        self.assertFalse(comun.is_superuser)
        self.assertFalse(comun.is_staff)
        self.assertTrue(comun.check_password("ClaveUsuario123!"))

    def test_restablecer_password_requiere_bandera_explicita(self):
        self._ejecutar()
        self._ejecutar(
            DJANGO_SUPERUSER_PASSWORD="NuevaClaveRecuperada789!",
            BOOTSTRAP_RESET_ADMIN_PASSWORD="true",
        )
        usuario = User.objects.get(username="admin_prueba")
        self.assertTrue(usuario.check_password("NuevaClaveRecuperada789!"))

    def test_crea_contenedores_faltantes_sin_tocar_existentes(self):
        self._ejecutar()
        TipoContenedor.objects.filter(codigo="40").delete()
        contenedor20 = TipoContenedor.objects.get(codigo="20")
        contenedor20.capacidad_tn = Decimal("22.50")
        contenedor20.save(update_fields=["capacidad_tn"])

        self._ejecutar()

        self.assertTrue(TipoContenedor.objects.filter(codigo="40").exists())
        contenedor20.refresh_from_db()
        self.assertEqual(contenedor20.capacidad_tn, Decimal("22.50"))

    def test_requiere_password_solo_para_crear(self):
        with self.assertRaises(CommandError):
            self._ejecutar(DJANGO_SUPERUSER_PASSWORD="")

    def test_requiere_username(self):
        with self.assertRaises(CommandError):
            self._ejecutar(DJANGO_SUPERUSER_USERNAME="")

