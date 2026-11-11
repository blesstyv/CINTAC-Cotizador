"""
Pruebas del campo opcional "Valor de carga".

Objetivos:
1. Verificar que el valor de carga se suma una sola vez
   al total estimado (mínimo y máximo, USD y CLP).
2. Verificar que es opcional: vacío, nulo u omitido = 0.
3. Rechazar valores inválidos (negativos, texto, exceso
   de decimales o de dígitos).
4. Regresión: demostrar que tarifas, cantidad de
   contenedores, recomendación, tránsito, contingencia,
   totales del flete y su conversión CLP quedan
   EXACTAMENTE iguales que antes de esta funcionalidad.
"""

from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Cotizacion
from .services.tipo_cambio import TipoCambioNoDisponible
from .tests import BaseCotizadorTestCase


TIPO_CAMBIO_PRUEBA = Decimal("970.46")

# Campos que existían antes de agregar el valor de carga.
# Ninguno de ellos debe cambiar al informar un valor de carga.
CAMPOS_EXISTENTES = [
    "rutaId",
    "origen",
    "destino",
    "pais",
    "tipoRuta",
    "pesoKg",
    "pesoTN",
    "tipoContenedor",
    "nombreContenedor",
    "capacidadTN",
    "cantidad",
    "tarifaMin",
    "tarifaMax",
    "totalMin",
    "totalMax",
    "esSugerida",
    "transitoOriginalMin",
    "transitoOriginalMax",
    "transitoMin",
    "transitoMax",
    "contingencia",
    "fuente",
    "conversionDisponible",
    "tipoCambio",
    "fechaTipoCambio",
    "fuenteTipoCambio",
    "modoTipoCambio",
    "totalMinCLP",
    "totalMaxCLP",
    "mensajeConversion",
]


def clp(valor_usd):
    return (
        Decimal(valor_usd) * TIPO_CAMBIO_PRUEBA
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )


@patch("cotizador.views.obtener_tipo_cambio")
class ValorCargaTests(BaseCotizadorTestCase):

    def configurar_tipo_cambio(self, mock_tipo_cambio):
        mock_tipo_cambio.return_value = {
            "valor": TIPO_CAMBIO_PRUEBA,
            "fecha": timezone.localdate(),
            "fuente": "Fuente prueba",
            "modo": "en_linea",
        }

    def cotizar(self, **extra):
        datos = {
            "ruta_id": self.ruta.id,
            "peso_carga": 100,
            "unidad_peso": "tn",
            "tipo_contenedor": "20",
            "contingencia": 3,
        }
        datos.update(extra)

        return self.client.post(
            "/api/cotizar/",
            datos,
            format="json",
        )

    # ------------------------------------------------------
    # Opcionalidad
    # ------------------------------------------------------

    def test_sin_valor_carga_se_considera_cero(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["valorCarga"], "0.00")
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMin"]),
            Decimal(respuesta.data["totalMin"]),
        )
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMax"]),
            Decimal(respuesta.data["totalMax"]),
        )
        self.assertEqual(
            respuesta.data["totalFinalMinCLP"],
            respuesta.data["totalMinCLP"],
        )
        self.assertEqual(
            respuesta.data["totalFinalMaxCLP"],
            respuesta.data["totalMaxCLP"],
        )

        cotizacion = Cotizacion.objects.get(
            id=respuesta.data["historialId"]
        )
        self.assertEqual(cotizacion.valor_carga, Decimal("0.00"))

    def test_valor_carga_nulo_se_considera_cero(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(valor_carga=None)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["valorCarga"], "0.00")

    def test_valor_carga_cero_explicito(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(valor_carga=0)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMin"]),
            Decimal(respuesta.data["totalMin"]),
        )

    # ------------------------------------------------------
    # Suma al total
    # ------------------------------------------------------

    def test_valor_carga_se_suma_al_total_min_y_max(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(valor_carga="350.50")

        self.assertEqual(respuesta.status_code, 200)

        total_min = Decimal(respuesta.data["totalMin"])
        total_max = Decimal(respuesta.data["totalMax"])

        # 100 TN / 23 TN = 5 contenedores de 20'
        # 1650 x 5 = 8250 ; 2850 x 5 = 14250
        self.assertEqual(total_min, Decimal("8250.00"))
        self.assertEqual(total_max, Decimal("14250.00"))

        self.assertEqual(respuesta.data["valorCarga"], "350.50")
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMin"]),
            Decimal("8600.50"),
        )
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMax"]),
            Decimal("14600.50"),
        )

    def test_valor_carga_se_suma_una_sola_vez_no_por_contenedor(
        self, mock_tc
    ):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(valor_carga=100)

        self.assertEqual(respuesta.data["cantidad"], 5)
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMin"])
            - Decimal(respuesta.data["totalMin"]),
            Decimal("100.00"),
        )

    def test_conversion_clp_del_total_final(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(valor_carga="350.50")

        self.assertEqual(
            Decimal(respuesta.data["totalFinalMinCLP"]),
            clp("8600.50"),
        )
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMaxCLP"]),
            clp("14600.50"),
        )

    def test_valor_carga_se_guarda_en_el_historial(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(valor_carga="1200.75")

        cotizacion = Cotizacion.objects.get(
            id=respuesta.data["historialId"]
        )
        self.assertEqual(cotizacion.valor_carga, Decimal("1200.75"))
        # Los totales del flete guardados no incluyen el valor de carga.
        self.assertEqual(cotizacion.total_min, Decimal("8250.00"))
        self.assertEqual(cotizacion.total_max, Decimal("14250.00"))

    def test_sin_tipo_cambio_total_final_usd_disponible(self, mock_tc):
        mock_tc.side_effect = TipoCambioNoDisponible("sin servicio")

        respuesta = self.cotizar(valor_carga=500)

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["conversionDisponible"])
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMin"]),
            Decimal("8750.00"),
        )
        self.assertIsNone(respuesta.data["totalFinalMinCLP"])
        self.assertIsNone(respuesta.data["totalFinalMaxCLP"])

    # ------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------

    def assert_rechazado(self, valor, mock_tc):
        self.configurar_tipo_cambio(mock_tc)
        cantidad_antes = Cotizacion.objects.count()

        respuesta = self.cotizar(valor_carga=valor)

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("valor_carga", respuesta.data)
        # Una solicitud inválida no debe guardar nada.
        self.assertEqual(Cotizacion.objects.count(), cantidad_antes)

    def test_rechaza_valor_carga_negativo(self, mock_tc):
        self.assert_rechazado(-1, mock_tc)

    def test_rechaza_valor_carga_texto(self, mock_tc):
        self.assert_rechazado("abc", mock_tc)

    def test_rechaza_valor_carga_con_tres_decimales(self, mock_tc):
        self.assert_rechazado("10.123", mock_tc)

    def test_rechaza_valor_carga_excesivo(self, mock_tc):
        self.assert_rechazado("12345678901.00", mock_tc)

    def test_restriccion_bd_impide_valor_carga_negativo(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)
        respuesta = self.cotizar()
        cotizacion_id = respuesta.data["historialId"]

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cotizacion.objects.filter(id=cotizacion_id).update(
                    valor_carga=Decimal("-0.01")
                )

    # ------------------------------------------------------
    # Regresión: nada de lo existente cambia
    # ------------------------------------------------------

    def test_regresion_campos_existentes_identicos(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        for contenedor in ("20", "40"):
            for peso, unidad in ((1, "kg"), (25001, "kg"), (100, "tn")):
                with self.subTest(
                    contenedor=contenedor, peso=peso, unidad=unidad
                ):
                    base = self.cotizar(
                        tipo_contenedor=contenedor,
                        peso_carga=peso,
                        unidad_peso=unidad,
                    )
                    con_valor = self.cotizar(
                        tipo_contenedor=contenedor,
                        peso_carga=peso,
                        unidad_peso=unidad,
                        valor_carga="999.99",
                    )

                    self.assertEqual(base.status_code, 200)
                    self.assertEqual(con_valor.status_code, 200)

                    for campo in CAMPOS_EXISTENTES:
                        self.assertEqual(
                            base.data[campo],
                            con_valor.data[campo],
                            f"El campo existente '{campo}' cambió",
                        )

    def test_regresion_opciones_contenedor_no_cambian(self, mock_tc):
        # El endpoint de opciones no recibe valor de carga y su
        # contrato estricto debe seguir rechazándolo.
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 100,
                "unidad_peso": "tn",
                "valor_carga": 100,
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)


# ----------------------------------------------------------
# Valor de carga ingresado en CLP
# ----------------------------------------------------------

def usd_desde_clp(valor_clp, tipo_cambio=TIPO_CAMBIO_PRUEBA):
    return (
        Decimal(valor_clp) / Decimal(tipo_cambio)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


@patch("cotizador.views.obtener_tipo_cambio")
class ValorCargaClpTests(BaseCotizadorTestCase):

    def configurar_tipo_cambio(self, mock_tipo_cambio, modo="en_linea"):
        mock_tipo_cambio.return_value = {
            "valor": TIPO_CAMBIO_PRUEBA,
            "fecha": timezone.localdate(),
            "fuente": "Fuente prueba",
            "modo": modo,
        }

    def cotizar(self, **extra):
        datos = {
            "ruta_id": self.ruta.id,
            "peso_carga": 100,
            "unidad_peso": "tn",
            "tipo_contenedor": "20",
            "contingencia": 0,
        }
        datos.update(extra)

        return self.client.post(
            "/api/cotizar/",
            datos,
            format="json",
        )

    def test_moneda_por_defecto_es_usd(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(valor_carga=100)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["monedaValorCarga"], "USD")
        self.assertEqual(respuesta.data["valorCargaIngresado"], "100.00")
        self.assertEqual(respuesta.data["valorCarga"], "100.00")

    def test_clp_se_convierte_a_usd_con_el_dolar_de_la_cotizacion(
        self, mock_tc
    ):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(
            valor_carga=300000,
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 200)

        equivalente = usd_desde_clp("300000")

        self.assertEqual(respuesta.data["monedaValorCarga"], "CLP")
        self.assertEqual(
            respuesta.data["valorCargaIngresado"], "300000.00"
        )
        self.assertEqual(
            Decimal(respuesta.data["valorCarga"]), equivalente
        )
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMin"]),
            Decimal("8250.00") + equivalente,
        )
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMax"]),
            Decimal("14250.00") + equivalente,
        )

    def test_clp_total_final_clp_suma_el_monto_exacto(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(
            valor_carga=300000,
            moneda_valor_carga="CLP",
        )

        self.assertEqual(
            Decimal(respuesta.data["totalFinalMinCLP"]),
            Decimal(respuesta.data["totalMinCLP"]) + 300000,
        )
        self.assertEqual(
            Decimal(respuesta.data["totalFinalMaxCLP"]),
            Decimal(respuesta.data["totalMaxCLP"]) + 300000,
        )

    def test_clp_acepta_decimales(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(
            valor_carga="1250000.50",
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["valorCargaIngresado"], "1250000.50"
        )

    def test_clp_acepta_maximo_permitido(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(
            valor_carga="999999999999.99",
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_clp_rechaza_sobre_el_maximo(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)
        cantidad_antes = Cotizacion.objects.count()

        respuesta = self.cotizar(
            valor_carga="1000000000000",
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("valor_carga", respuesta.data)
        self.assertEqual(Cotizacion.objects.count(), cantidad_antes)

    def test_clp_rechaza_negativo(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(
            valor_carga=-1,
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_rechaza_moneda_no_soportada(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(
            valor_carga=100,
            moneda_valor_carga="EUR",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("moneda_valor_carga", respuesta.data)

    def test_clp_se_guarda_con_moneda_y_monto_original(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc)

        respuesta = self.cotizar(
            valor_carga=300000,
            moneda_valor_carga="CLP",
        )

        cotizacion = Cotizacion.objects.get(
            id=respuesta.data["historialId"]
        )

        self.assertEqual(cotizacion.valor_carga_moneda, "CLP")
        self.assertEqual(
            cotizacion.valor_carga_ingresado, Decimal("300000.00")
        )
        self.assertEqual(
            cotizacion.valor_carga, usd_desde_clp("300000")
        )
        # El flete guardado no cambia.
        self.assertEqual(cotizacion.total_min, Decimal("8250.00"))
        self.assertEqual(cotizacion.total_max, Decimal("14250.00"))

    def test_clp_usa_ultimo_valor_respaldado(self, mock_tc):
        self.configurar_tipo_cambio(mock_tc, modo="respaldo")

        respuesta = self.cotizar(
            valor_carga=300000,
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["modoTipoCambio"], "respaldo")
        self.assertEqual(
            Decimal(respuesta.data["valorCarga"]),
            usd_desde_clp("300000"),
        )

    def test_clp_sin_ningun_tipo_de_cambio_se_rechaza(self, mock_tc):
        mock_tc.side_effect = TipoCambioNoDisponible("sin datos")
        cantidad_antes = Cotizacion.objects.count()

        respuesta = self.cotizar(
            valor_carga=300000,
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("valor_carga", respuesta.data)
        self.assertEqual(Cotizacion.objects.count(), cantidad_antes)

    def test_clp_cero_sin_tipo_de_cambio_se_permite(self, mock_tc):
        mock_tc.side_effect = TipoCambioNoDisponible("sin datos")

        respuesta = self.cotizar(
            valor_carga=0,
            moneda_valor_carga="CLP",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["valorCarga"], "0.00")

    def test_regresion_campos_existentes_identicos_con_clp(
        self, mock_tc
    ):
        self.configurar_tipo_cambio(mock_tc)

        base = self.cotizar()
        con_clp = self.cotizar(
            valor_carga=450000,
            moneda_valor_carga="CLP",
        )

        for campo in CAMPOS_EXISTENTES:
            self.assertEqual(
                base.data[campo],
                con_clp.data[campo],
                f"El campo existente '{campo}' cambió",
            )


class ValorCargaClpRespaldoRealTests(BaseCotizadorTestCase):
    """
    Sin simular obtener_tipo_cambio: si el servicio externo
    falla, se usa el último dólar observado almacenado.
    """

    @patch(
        "cotizador.services.tipo_cambio._obtener_desde_internet",
        side_effect=TipoCambioNoDisponible("servicio caído"),
    )
    def test_servicio_caido_usa_ultimo_valor_observado(self, _mock):
        from .models import TipoCambio

        TipoCambio.objects.create(
            moneda_origen="USD",
            moneda_destino="CLP",
            valor=Decimal("950.00"),
            fecha_referencia=timezone.localdate(),
            fuente="Respaldo de prueba",
        )

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 100,
                "unidad_peso": "tn",
                "tipo_contenedor": "20",
                "valor_carga": 95000,
                "moneda_valor_carga": "CLP",
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["conversionDisponible"])
        self.assertEqual(
            Decimal(respuesta.data["tipoCambio"]), Decimal("950.00")
        )
        # 95.000 CLP / 950 = 100,00 USD
        self.assertEqual(respuesta.data["valorCarga"], "100.00")
