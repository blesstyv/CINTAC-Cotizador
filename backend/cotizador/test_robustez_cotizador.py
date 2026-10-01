from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .tests import BaseCotizadorTestCase


class RobustezOpcionesContenedorTests(
    BaseCotizadorTestCase
):
    def test_sin_ruta_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "peso_carga": 25,
                "unidad_peso": "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_sin_peso_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "unidad_peso":
                    "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_sin_unidad_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_ruta_cero_es_rechazada(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": 0,
                "peso_carga": 25,
                "unidad_peso": "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_peso_con_mas_de_tres_decimales_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    "25.0001",

                "unidad_peso":
                    "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_peso_que_excede_formato_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    "1000000000000000",

                "unidad_peso":
                    "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_ruta_sin_tarifas_no_genera_opciones(
        self,
    ):
        self.tarifa_20.delete()
        self.tarifa_40.delete()

        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertIn(
            "detail",
            respuesta.data,
        )


    def test_sin_contenedores_activos_no_genera_opciones(
        self,
    ):
        self.contenedor_20.activo = False
        self.contenedor_20.save()

        self.contenedor_40.activo = False
        self.contenedor_40.save()

        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


class RobustezCotizacionTests(
    BaseCotizadorTestCase
):
    def test_body_vacio_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/cotizar/",
            {},
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_sin_tipo_contenedor_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_contingencia_texto_es_rechazada(
        self,
    ):
        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    "hola",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_campo_extra_en_cotizacion_es_rechazado(
        self,
    ):
        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    0,

                "precio_manual":
                    1,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertIn(
            "campos_no_permitidos",
            respuesta.data,
        )


    def test_contenedor_sin_tarifa_en_ruta_es_rechazado(
        self,
    ):
        self.tarifa_20.delete()

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_sin_tiempo_transito_cotizacion_sigue_funcionando(
        self,
        mock_tipo_cambio,
    ):
        mock_tipo_cambio.return_value = {
            "valor":
                Decimal("970.46"),

            "fecha":
                timezone.localdate(),

            "fuente":
                "Prueba",

            "modo":
                "en_linea",
        }

        self.transito.delete()

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    3,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertIsNone(
            respuesta.data[
                "transitoOriginalMin"
            ]
        )

        self.assertIsNone(
            respuesta.data[
                "transitoOriginalMax"
            ]
        )

        self.assertIsNone(
            respuesta.data[
                "transitoMin"
            ]
        )

        self.assertIsNone(
            respuesta.data[
                "transitoMax"
            ]
        )


    def test_json_malformado_es_rechazado(
        self,
    ):
        respuesta = self.client.generic(
            "POST",
            "/api/cotizar/",
            data=b'{"ruta_id":',
            content_type=
                "application/json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_cotizar_sin_token_es_rechazado(
        self,
    ):
        cliente = APIClient()

        respuesta = cliente.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_usuario_no_autorizado_no_puede_cotizar(
        self,
    ):
        cliente = APIClient()

        token = Token.objects.create(
            user=
                self.usuario_no_autorizado
        )

        cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token.key}"
            )
        )

        respuesta = cliente.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25,

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_peso_muy_alto_pero_valido_no_produce_error_500(
        self,
        mock_tipo_cambio,
    ):
        mock_tipo_cambio.return_value = {
            "valor":
                Decimal("970.46"),

            "fecha":
                timezone.localdate(),

            "fuente":
                "Prueba",

            "modo":
                "en_linea",
        }

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    "999999999999999.999",

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertGreater(
            respuesta.data[
                "cantidad"
            ],
            0,
        )