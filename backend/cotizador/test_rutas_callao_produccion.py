"""Pruebas del proceso idempotente que incorpora rutas del cliente a Callao.

Usa la base de datos de pruebas de Django, no PostgreSQL de producción.
"""
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import Puerto, Ruta, Tarifa, TiempoTransito


class RutasCallaoProductionBootstrapTests(TestCase):
    def setUp(self):
        self.san_antonio = Puerto.objects.create(
            nombre="San Antonio", pais="Chile"
        )
        self.valparaiso = Puerto.objects.create(
            nombre="Valparaiso", pais="Chile"
        )

    def test_crea_exactamente_dos_rutas_con_datos_confirmados(self):
        call_command("incorporar_rutas_callao", verbosity=0)
        callao = Puerto.objects.get(nombre="Callao", pais="Perú")
        self.assertEqual(Puerto.objects.count(), 3)
        rutas = Ruta.objects.filter(puerto_destino=callao)
        self.assertEqual(rutas.count(), 2)
        self.assertEqual(
            set(rutas.values_list("puerto_origen__nombre", flat=True)),
            {"San Antonio", "Valparaiso"},
        )

        for ruta in rutas:
            with self.subTest(origen=ruta.puerto_origen.nombre):
                self.assertEqual(ruta.tipo_ruta, "Directo")
                transito = TiempoTransito.objects.get(ruta=ruta)
                self.assertEqual(transito.dias_minimos, 3)
                self.assertEqual(transito.dias_maximos, 5)
                tarifas = {
                    t.tipo_contenedor: t
                    for t in Tarifa.objects.filter(ruta=ruta)
                }
                self.assertEqual(set(tarifas), {"20", "40"})
                for codigo, importe in (("20", "900"), ("40", "970")):
                    self.assertEqual(
                        tarifas[codigo].valor_minimo, Decimal(importe)
                    )
                    self.assertEqual(
                        tarifas[codigo].valor_maximo, Decimal(importe)
                    )

    def test_repetir_no_duplica_y_conserva_cambios_manual_comex(self):
        call_command("incorporar_rutas_callao", verbosity=0)
        ruta = Ruta.objects.get(puerto_origen=self.san_antonio)
        tarifa = Tarifa.objects.get(ruta=ruta, tipo_contenedor="20")
        tarifa.valor_minimo = Decimal("950.00")
        tarifa.valor_maximo = Decimal("950.00")
        tarifa.save(update_fields=["valor_minimo", "valor_maximo"])
        transito = TiempoTransito.objects.get(ruta=ruta)
        transito.dias_minimos = 4
        transito.dias_maximos = 6
        transito.save(update_fields=["dias_minimos", "dias_maximos"])

        call_command("incorporar_rutas_callao", verbosity=0)

        self.assertEqual(Ruta.objects.count(), 2)
        self.assertEqual(Tarifa.objects.count(), 4)
        self.assertEqual(Puerto.objects.count(), 3)
        tarifa.refresh_from_db()
        transito.refresh_from_db()
        self.assertEqual(tarifa.valor_minimo, Decimal("950.00"))
        self.assertEqual(transito.dias_minimos, 4)
        self.assertEqual(transito.dias_maximos, 6)

    def test_faltan_origenes_no_escribe_en_bd(self):
        Puerto.objects.filter(pk=self.valparaiso.pk).delete()
        with self.assertRaises(CommandError):
            call_command("incorporar_rutas_callao", verbosity=0)
        self.assertEqual(Puerto.objects.count(), 1)
        self.assertFalse(Ruta.objects.exists())
        self.assertFalse(Tarifa.objects.exists())
        self.assertFalse(TiempoTransito.objects.exists())
        self.assertFalse(
            Puerto.objects.filter(nombre="Callao", pais="Perú").exists()
        )

    def test_ruta_existente_no_directa_falla_sin_modificaciones(self):
        call_command("incorporar_rutas_callao", verbosity=0)
        ruta = Ruta.objects.get(puerto_origen=self.san_antonio)
        ruta.tipo_ruta = "Transbordo"
        ruta.save(update_fields=["tipo_ruta"])

        with self.assertRaises(CommandError):
            call_command("incorporar_rutas_callao", verbosity=0)

        ruta.refresh_from_db()
        self.assertEqual(ruta.tipo_ruta, "Transbordo")
        self.assertEqual(Ruta.objects.count(), 2)
        self.assertEqual(Tarifa.objects.count(), 4)
