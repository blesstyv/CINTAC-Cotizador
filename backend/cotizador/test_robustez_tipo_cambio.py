import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from cotizador.models import TipoCambio

from cotizador.services.tipo_cambio import (
    TipoCambioNoDisponible,
    _obtener_desde_internet,
    obtener_tipo_cambio,
)


class RespuestaHTTPFalsa:
    def __init__(
        self,
        contenido,
    ):
        self.contenido = contenido

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False

    def read(
        self,
    ):
        return self.contenido


class RobustezTipoCambioTests(
    TestCase
):
    def crear_respaldo(
        self,
        valor=Decimal("950.00"),
    ):
        registro = (
            TipoCambio.objects.create(
                moneda_origen="USD",
                moneda_destino="CLP",
                valor=valor,
                fecha_referencia=(
                    timezone.localdate()
                    - timedelta(days=1)
                ),
                fuente="Fuente respaldo",
            )
        )

        TipoCambio.objects.filter(
            pk=registro.pk
        ).update(
            obtenido_en=(
                timezone.now()
                - timedelta(hours=2)
            )
        )

        registro.refresh_from_db()

        return registro


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_respuesta_valida_se_guarda_correctamente(
        self,
        mock_urlopen,
    ):
        datos = {
            "serie": [
                {
                    "valor": 970.46,
                    "fecha":
                        "2026-09-30T03:00:00.000Z",
                }
            ]
        }

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    datos
                ).encode("utf-8")
            )
        )

        registro = (
            _obtener_desde_internet()
        )

        self.assertEqual(
            registro.valor,
            Decimal("970.46"),
        )

        self.assertEqual(
            registro.fecha_referencia.isoformat(),
            "2026-09-30",
        )

        self.assertEqual(
            TipoCambio.objects.count(),
            1,
        )


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_json_invalido_es_rechazado(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                b"{json-invalido"
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_respuesta_sin_serie_es_rechazada(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    {}
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_serie_vacia_es_rechazada(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    {
                        "serie": [],
                    }
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_valor_faltante_es_rechazado(
        self,
        mock_urlopen,
    ):
        datos = {
            "serie": [
                {
                    "fecha":
                        "2026-09-30T03:00:00.000Z",
                }
            ]
        }

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    datos
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_valor_cero_es_rechazado(
        self,
        mock_urlopen,
    ):
        datos = {
            "serie": [
                {
                    "valor": 0,
                    "fecha":
                        "2026-09-30T03:00:00.000Z",
                }
            ]
        }

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    datos
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_valor_negativo_es_rechazado(
        self,
        mock_urlopen,
    ):
        datos = {
            "serie": [
                {
                    "valor": -970.46,
                    "fecha":
                        "2026-09-30T03:00:00.000Z",
                }
            ]
        }

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    datos
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_fecha_faltante_es_rechazada(
        self,
        mock_urlopen,
    ):
        datos = {
            "serie": [
                {
                    "valor": 970.46,
                }
            ]
        }

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    datos
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_fecha_invalida_es_rechazada(
        self,
        mock_urlopen,
    ):
        datos = {
            "serie": [
                {
                    "valor": 970.46,
                    "fecha":
                        "fecha-invalida",
                }
            ]
        }

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    datos
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_tipo_json_incorrecto_es_rechazado(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    []
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_utf8_invalido_es_controlado(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                b"\xff\xfe\xfd"
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_valor_nan_es_rechazado(
        self,
        mock_urlopen,
    ):
        datos = {
            "serie": [
                {
                    "valor": "NaN",
                    "fecha":
                        "2026-09-30T03:00:00.000Z",
                }
            ]
        }

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                json.dumps(
                    datos
                ).encode("utf-8")
            )
        )

        with self.assertRaises(
            TipoCambioNoDisponible
        ):
            _obtener_desde_internet()


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_respuesta_invalida_utiliza_respaldo(
        self,
        mock_urlopen,
    ):
        self.crear_respaldo(
            Decimal("950.00")
        )

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                b"{respuesta-invalida"
            )
        )

        resultado = (
            obtener_tipo_cambio()
        )

        self.assertEqual(
            resultado["modo"],
            "respaldo",
        )

        self.assertEqual(
            resultado["valor"],
            Decimal("950.00"),
        )


    @patch(
        "cotizador.services.tipo_cambio.urlopen"
    )
    def test_error_externo_no_elimina_respaldo(
        self,
        mock_urlopen,
    ):
        respaldo = (
            self.crear_respaldo(
                Decimal("960.00")
            )
        )

        mock_urlopen.return_value = (
            RespuestaHTTPFalsa(
                b"{json-invalido"
            )
        )

        resultado = (
            obtener_tipo_cambio()
        )

        respaldo.refresh_from_db()

        self.assertEqual(
            resultado["valor"],
            Decimal("960.00"),
        )

        self.assertEqual(
            respaldo.valor,
            Decimal("960.00"),
        )

        self.assertEqual(
            TipoCambio.objects.count(),
            1,
        )