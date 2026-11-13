"""
Pruebas de la finalización EVA3.

Cubren:
* C01: control explícito ``incluir_valor_carga``.
* C02/C03: instantánea persistida del total final y que el historial
  NO se recalcula con tipos de cambio posteriores.
* Servicio central de cálculo (funciones puras).
* Migración 0012: completa registros existentes con sus propios datos.
* Tipo de cambio: antigüedad, respaldo que no se confunde con caché y
  suspensión temporal de reintentos tras una falla.
"""

from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from unittest.mock import patch

from django.apps import apps as django_apps
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from .models import Cotizacion, TipoCambio
from .services.calculo_cotizacion import (
    ConversionNoDisponible,
    ValorCarga,
    calcular_totales_finales,
    normalizar_valor_carga,
)
from .services.tipo_cambio import (
    TipoCambioNoDisponible,
    obtener_tipo_cambio,
)
from .tests import BaseCotizadorTestCase


TC = Decimal("970.46")


def _cambio(valor=TC, fecha=None, modo="en_linea"):
    return {
        "valor": valor,
        "fecha": fecha or timezone.localdate(),
        "fuente": "Fuente prueba",
        "modo": modo,
        "antiguedadDias": 0,
        "desactualizado": False,
    }


# ----------------------------------------------------------------------
# Servicio de cálculo
# ----------------------------------------------------------------------


class CalculoCotizacionServicioTests(SimpleTestCase):

    def test_inactivo_es_cero_aunque_exista_monto(self):
        valor = normalizar_valor_carga(
            Decimal("5000"), "USD", incluir=False
        )
        self.assertEqual(valor.usd, Decimal("0.00"))
        self.assertEqual(valor.ingresado, Decimal("0.00"))
        self.assertFalse(valor.incluido)

    def test_vacio_y_nulo_son_cero(self):
        for monto in (None, "", 0, Decimal("0")):
            with self.subTest(monto=monto):
                valor = normalizar_valor_carga(monto, "USD")
                self.assertEqual(valor.usd, Decimal("0.00"))

    def test_usd_no_se_convierte(self):
        valor = normalizar_valor_carga(Decimal("350.50"), "USD")
        self.assertEqual(valor.usd, Decimal("350.50"))
        self.assertEqual(valor.ingresado, Decimal("350.50"))

    def test_clp_una_sola_division_redondeada_a_centavos(self):
        valor = normalizar_valor_carga(
            Decimal("300000"), "CLP", tipo_cambio=TC
        )
        # 300000 / 970.46 = 309.1317...
        self.assertEqual(valor.usd, Decimal("309.13"))
        self.assertEqual(valor.ingresado, Decimal("300000.00"))

    def test_clp_sin_tipo_cambio_lanza_error(self):
        with self.assertRaises(ConversionNoDisponible):
            normalizar_valor_carga(Decimal("1000"), "CLP")

    def test_clp_cero_sin_tipo_cambio_es_valido(self):
        valor = normalizar_valor_carga(Decimal("0"), "CLP")
        self.assertEqual(valor.usd, Decimal("0.00"))

    def test_moneda_invalida(self):
        with self.assertRaises(ValueError):
            normalizar_valor_carga(Decimal("1"), "EUR")

    def test_negativo_rechazado(self):
        with self.assertRaises(ValueError):
            normalizar_valor_carga(Decimal("-1"), "USD")

    def test_total_final_sin_valor_es_el_flete(self):
        totales = calcular_totales_finales(
            Decimal("3200.00"),
            Decimal("5600.00"),
            normalizar_valor_carga(None, "USD"),
            Decimal("3105472"),
            Decimal("5434576"),
            TC,
        )
        self.assertEqual(totales.total_final_min, Decimal("3200.00"))
        self.assertEqual(totales.total_final_max, Decimal("5600.00"))
        self.assertEqual(totales.total_final_min_clp, Decimal("3105472"))
        self.assertEqual(totales.total_final_max_clp, Decimal("5434576"))

    def test_total_final_usd_se_suma_una_vez(self):
        totales = calcular_totales_finales(
            Decimal("3200.00"),
            Decimal("5600.00"),
            normalizar_valor_carga(Decimal("1000"), "USD"),
        )
        self.assertEqual(totales.total_final_min, Decimal("4200.00"))
        self.assertEqual(totales.total_final_max, Decimal("6600.00"))
        self.assertIsNone(totales.total_final_min_clp)

    def test_clp_no_hay_doble_conversion(self):
        valor = normalizar_valor_carga(
            Decimal("300000"), "CLP", tipo_cambio=TC
        )
        totales = calcular_totales_finales(
            Decimal("3200.00"),
            Decimal("5600.00"),
            valor,
            Decimal("3105472"),
            Decimal("5434576"),
            TC,
        )
        # CLP final = flete CLP + monto CLP exacto (sin ida y vuelta).
        self.assertEqual(totales.total_final_min_clp, Decimal("3405472"))
        self.assertEqual(totales.total_final_max_clp, Decimal("5734576"))
        self.assertEqual(totales.total_final_min, Decimal("3509.13"))

    def test_clp_muy_pequeno_se_refleja_en_clp(self):
        # 1 CLP equivale a 0,00 USD redondeado; el total CLP igual
        # debe reflejar el peso ingresado (antes el historial lo omitía).
        valor = normalizar_valor_carga(Decimal("1"), "CLP", tipo_cambio=TC)
        self.assertEqual(valor.usd, Decimal("0.00"))
        self.assertTrue(valor.incluido)
        totales = calcular_totales_finales(
            Decimal("100"), Decimal("200"), valor,
            Decimal("97046"), Decimal("194092"), TC,
        )
        self.assertEqual(totales.total_final_min_clp, Decimal("97047"))


# ----------------------------------------------------------------------
# Endpoint de cotización
# ----------------------------------------------------------------------


@patch("cotizador.views.obtener_tipo_cambio")
class ControlExplicitoValorCargaTests(BaseCotizadorTestCase):

    def cotizar(self, **extra):
        datos = {
            "ruta_id": self.ruta.id,
            "peso_carga": 100,
            "unidad_peso": "tn",
            "tipo_contenedor": "20",
        }
        datos.update(extra)
        return self.client.post("/api/cotizar/", datos, format="json")

    def test_desactivado_ignora_monto_y_no_suma(self, mock_tc):
        mock_tc.return_value = _cambio()
        respuesta = self.cotizar(
            valor_carga="5000", incluir_valor_carga=False
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["incluyeValorCarga"])
        self.assertEqual(respuesta.data["valorCarga"], "0.00")
        self.assertEqual(
            respuesta.data["totalFinalMin"], respuesta.data["totalMin"]
        )
        self.assertEqual(
            respuesta.data["totalFinalMaxCLP"], respuesta.data["totalMaxCLP"]
        )
        cot = Cotizacion.objects.get(pk=respuesta.data["historialId"])
        self.assertEqual(cot.valor_carga_ingresado, Decimal("0.00"))

    def test_desactivado_en_clp_sin_dolar_no_falla(self, mock_tc):
        mock_tc.side_effect = TipoCambioNoDisponible("sin dólar")
        respuesta = self.cotizar(
            valor_carga="300000",
            moneda_valor_carga="CLP",
            incluir_valor_carga=False,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["valorCarga"], "0.00")

    def test_activado_suma_una_vez(self, mock_tc):
        mock_tc.return_value = _cambio()
        respuesta = self.cotizar(
            valor_carga="1000", incluir_valor_carga=True
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["incluyeValorCarga"])
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMin"]),
            Decimal(respuesta.data["totalMin"]) + Decimal("1000"),
        )

    def test_activado_sin_monto_es_cero(self, mock_tc):
        mock_tc.return_value = _cambio()
        respuesta = self.cotizar(incluir_valor_carga=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["incluyeValorCarga"])
        self.assertEqual(
            respuesta.data["totalFinalMax"], respuesta.data["totalMax"]
        )

    def test_bandera_invalida_rechazada(self, mock_tc):
        mock_tc.return_value = _cambio()
        respuesta = self.cotizar(incluir_valor_carga="quizas")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("incluir_valor_carga", respuesta.data)

    def test_instantanea_total_final_persistida(self, mock_tc):
        mock_tc.return_value = _cambio()
        respuesta = self.cotizar(
            valor_carga="300000", moneda_valor_carga="CLP"
        )
        cot = Cotizacion.objects.get(pk=respuesta.data["historialId"])
        self.assertEqual(
            str(cot.total_final_min), respuesta.data["totalFinalMin"]
        )
        self.assertEqual(
            str(int(cot.total_final_max_clp)),
            respuesta.data["totalFinalMaxCLP"],
        )

    def test_historial_no_se_recalcula_con_dolar_actual(self, mock_tc):
        mock_tc.return_value = _cambio()
        respuesta = self.cotizar(valor_carga="1000")
        original = respuesta.data

        # Cambia el dólar "actual": el historial debe conservar el
        # resultado informado al momento de cotizar.
        mock_tc.return_value = _cambio(valor=Decimal("1200.00"))
        TipoCambio.objects.create(
            moneda_origen="USD",
            moneda_destino="CLP",
            valor=Decimal("1200.00"),
            fecha_referencia=timezone.localdate() + timedelta(days=1),
            fuente="Dólar posterior",
        )

        detalle = self.client.get(
            f"/api/historial/{original['historialId']}/"
        ).data["cotizacion"]

        self.assertEqual(
            Decimal(detalle["tipoCambio"]), Decimal(original["tipoCambio"])
        )

        for campo in (
            "totalMinCLP",
            "totalFinalMin",
            "totalFinalMax",
            "totalFinalMinCLP",
            "totalFinalMaxCLP",
        ):
            with self.subTest(campo=campo):
                self.assertEqual(detalle[campo], original[campo])

    def test_respuesta_informa_antiguedad_del_dolar(self, mock_tc):
        cambio = _cambio(modo="respaldo")
        cambio["antiguedadDias"] = 9
        cambio["desactualizado"] = True
        mock_tc.return_value = cambio
        respuesta = self.cotizar()
        self.assertEqual(respuesta.data["antiguedadTipoCambioDias"], 9)
        self.assertTrue(respuesta.data["tipoCambioDesactualizado"])


class RestriccionesValorCargaTests(BaseCotizadorTestCase):
    """Constraints de PostgreSQL agregadas en la migración 0012."""

    def _base(self, **extra):
        datos = dict(
            usuario=self.usuario,
            origen="A",
            pais_origen="X",
            destino="B",
            tipo_ruta="Directo",
            peso_kg=Decimal("1000"),
            peso_tn=Decimal("1"),
            tipo_contenedor="20",
            nombre_contenedor="20",
            capacidad_tn=Decimal("23"),
            cantidad=1,
            tarifa_min=Decimal("100"),
            tarifa_max=Decimal("200"),
            total_min=Decimal("100"),
            total_max=Decimal("200"),
        )
        datos.update(extra)
        return datos

    def test_total_final_no_puede_ser_menor_al_flete(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cotizacion.objects.create(
                **self._base(total_final_min=Decimal("50"))
            )

    def test_cargo_sin_monto_ingresado_rechazado(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cotizacion.objects.create(
                **self._base(
                    valor_carga=Decimal("10"),
                    valor_carga_ingresado=Decimal("0"),
                    valor_carga_moneda="CLP",
                )
            )

    def test_usd_incoherente_rechazado(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cotizacion.objects.create(
                **self._base(
                    valor_carga=Decimal("10"),
                    valor_carga_ingresado=Decimal("20"),
                    valor_carga_moneda="USD",
                )
            )


class MigracionTotalFinalTests(BaseCotizadorTestCase):
    """La migración completa registros previos con sus propios datos."""

    def test_backfill_usa_datos_del_mismo_registro(self):
        cot = Cotizacion.objects.create(
            usuario=self.usuario,
            origen="A",
            pais_origen="X",
            destino="B",
            tipo_ruta="Directo",
            peso_kg=Decimal("1000"),
            peso_tn=Decimal("1"),
            tipo_contenedor="20",
            nombre_contenedor="20",
            capacidad_tn=Decimal("23"),
            cantidad=1,
            tarifa_min=Decimal("100"),
            tarifa_max=Decimal("200"),
            total_min=Decimal("100"),
            total_max=Decimal("200"),
            valor_carga=Decimal("309.13"),
            valor_carga_ingresado=Decimal("300000"),
            valor_carga_moneda="CLP",
            tipo_cambio=TC,
            conversion_disponible=True,
            total_min_clp=Decimal("97046"),
            total_max_clp=Decimal("194092"),
        )

        migracion = import_module(
            "cotizador.migrations.0012_cotizacion_total_final_snapshot"
        )
        migracion.completar_totales_finales(django_apps, None)

        cot.refresh_from_db()
        self.assertEqual(cot.total_final_min, Decimal("409.13"))
        self.assertEqual(cot.total_final_max, Decimal("509.13"))
        self.assertEqual(cot.total_final_min_clp, Decimal("397046"))
        self.assertEqual(cot.total_final_max_clp, Decimal("494092"))


# ----------------------------------------------------------------------
# Tipo de cambio
# ----------------------------------------------------------------------


class TipoCambioEstadoTests(TestCase):

    def setUp(self):
        cache.clear()

    def _registro(self, dias_atras, horas_obtenido=0, valor="950.00"):
        registro = TipoCambio.objects.create(
            moneda_origen="USD",
            moneda_destino="CLP",
            valor=Decimal(valor),
            fecha_referencia=timezone.localdate() - timedelta(days=dias_atras),
            fuente="Respaldo",
        )
        if horas_obtenido:
            TipoCambio.objects.filter(pk=registro.pk).update(
                obtenido_en=timezone.now() - timedelta(hours=horas_obtenido)
            )
        return registro

    @patch("cotizador.services.tipo_cambio._obtener_desde_internet")
    def test_respaldo_antiguo_recien_creado_no_es_cache(self, mock_net):
        # Simula el respaldo cargado en el despliegue: obtenido ahora,
        # pero con fecha de referencia antigua.
        self._registro(dias_atras=20)
        mock_net.side_effect = TipoCambioNoDisponible("caída")

        resultado = obtener_tipo_cambio()

        mock_net.assert_called_once()
        self.assertEqual(resultado["modo"], "respaldo")
        self.assertEqual(resultado["antiguedadDias"], 20)
        self.assertTrue(resultado["desactualizado"])

    @override_settings(TIPO_CAMBIO_REINTENTO_SEGUNDOS=300)
    @patch("cotizador.services.tipo_cambio._obtener_desde_internet")
    def test_tras_falla_no_reintenta_en_cada_cotizacion(self, mock_net):
        self._registro(dias_atras=1, horas_obtenido=3)
        mock_net.side_effect = TipoCambioNoDisponible("caída")

        primero = obtener_tipo_cambio()
        segundo = obtener_tipo_cambio()

        self.assertEqual(mock_net.call_count, 1)
        self.assertEqual(primero["modo"], "respaldo")
        self.assertEqual(segundo["modo"], "respaldo")

    @patch("cotizador.services.tipo_cambio._obtener_desde_internet")
    def test_sin_respaldo_error_controlado(self, mock_net):
        mock_net.side_effect = TipoCambioNoDisponible("caída")
        with self.assertRaises(TipoCambioNoDisponible):
            obtener_tipo_cambio()

    def test_cache_vigente_informa_antiguedad(self):
        self._registro(dias_atras=2)
        resultado = obtener_tipo_cambio()
        self.assertEqual(resultado["modo"], "cache")
        self.assertEqual(resultado["antiguedadDias"], 2)
        self.assertFalse(resultado["desactualizado"])
