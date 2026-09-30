from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import (
    PerfilUsuario,
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)


class BaseCotizadorTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(
            username="usuario_test",
            password="ClaveSegura123!",
        )

        cls.usuario.perfil_cintac.autorizado = True
        cls.usuario.perfil_cintac.save()

        cls.usuario_no_autorizado = (
            User.objects.create_user(
                username="usuario_bloqueado",
                password="ClaveSegura123!",
            )
        )

        cls.admin = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.cl",
            password="ClaveAdmin123!",
        )

        cls.origen = Puerto.objects.create(
            nombre="Shanghai",
            pais="China",
        )

        cls.destino = Puerto.objects.create(
            nombre="Valparaiso",
            pais="Chile",
        )

        cls.ruta = Ruta.objects.create(
            puerto_origen=cls.origen,
            puerto_destino=cls.destino,
            tipo_ruta="Directo / Transbordo",
        )

        cls.contenedor_20 = (
            TipoContenedor.objects.create(
                codigo="20",
                nombre="Contenedor 20'",
                capacidad_tn=Decimal("25.00"),
                activo=True,
            )
        )

        cls.contenedor_40 = (
            TipoContenedor.objects.create(
                codigo="40",
                nombre="Contenedor 40'",
                capacidad_tn=Decimal("25.00"),
                activo=True,
            )
        )

        cls.tarifa_20 = Tarifa.objects.create(
            ruta=cls.ruta,
            tipo_contenedor="20",
            valor_minimo=Decimal("1650.00"),
            valor_maximo=Decimal("2850.00"),
            fuente="Fuente de prueba",
        )

        cls.tarifa_40 = Tarifa.objects.create(
            ruta=cls.ruta,
            tipo_contenedor="40",
            valor_minimo=Decimal("2350.00"),
            valor_maximo=Decimal("3850.00"),
            fuente="Fuente de prueba",
        )

        cls.transito = TiempoTransito.objects.create(
            ruta=cls.ruta,
            dias_minimos=26,
            dias_maximos=34,
        )

    def setUp(self):
        self.client = APIClient()

        self.token = Token.objects.create(
            user=self.usuario
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {self.token.key}"
            )
        )


class AutenticacionTests(BaseCotizadorTestCase):
    def test_api_rechaza_usuario_sin_token(self):
        cliente = APIClient()

        respuesta = cliente.get(
            "/api/rutas/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )

    def test_usuario_autorizado_puede_acceder(self):
        respuesta = self.client.get(
            "/api/rutas/"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

    def test_usuario_no_autorizado_es_bloqueado(self):
        cliente = APIClient()

        token = Token.objects.create(
            user=self.usuario_no_autorizado
        )

        cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token.key}"
            )
        )

        respuesta = cliente.get(
            "/api/rutas/"
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )

    def test_login_con_credenciales_incorrectas(self):
        cliente = APIClient()

        respuesta = cliente.post(
            "/api/login/",
            {
                "username": "usuario_test",
                "password": "incorrecta",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_login_usuario_no_autorizado(self):
        cliente = APIClient()

        respuesta = cliente.post(
            "/api/login/",
            {
                "username":
                    "usuario_bloqueado",

                "password":
                    "ClaveSegura123!",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )

    def test_logout_elimina_token(self):
        respuesta = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        existe = Token.objects.filter(
            key=self.token.key
        ).exists()

        self.assertFalse(existe)

    def test_token_expirado_es_rechazado(self):
        Token.objects.filter(
            key=self.token.key
        ).update(
            created=(
                timezone.now()
                - timedelta(hours=9)
            )
        )

        respuesta = self.client.get(
            "/api/sesion/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


class ModeloTests(BaseCotizadorTestCase):
    def test_capacidad_cero_es_invalida(self):
        contenedor = TipoContenedor(
            codigo="XX",
            nombre="Prueba",
            capacidad_tn=Decimal("0"),
        )

        with self.assertRaises(
            ValidationError
        ):
            contenedor.full_clean()

    def test_tarifa_negativa_es_invalida(self):
        tarifa = Tarifa(
            ruta=self.ruta,
            tipo_contenedor="20",
            valor_minimo=Decimal("-1"),
            valor_maximo=Decimal("100"),
        )

        with self.assertRaises(
            ValidationError
        ):
            tarifa.full_clean()

    def test_tarifa_maxima_no_puede_ser_menor(self):
        tarifa = Tarifa(
            ruta=self.ruta,
            tipo_contenedor="20",
            valor_minimo=Decimal("5000"),
            valor_maximo=Decimal("1000"),
        )

        with self.assertRaises(
            ValidationError
        ):
            tarifa.full_clean()

    def test_transito_maximo_no_puede_ser_menor(self):
        otra_ruta = Ruta.objects.create(
            puerto_origen=self.origen,
            puerto_destino=Puerto.objects.create(
                nombre="San Antonio",
                pais="Chile",
            ),
            tipo_ruta="Directo",
        )

        transito = TiempoTransito(
            ruta=otra_ruta,
            dias_minimos=40,
            dias_maximos=20,
        )

        with self.assertRaises(
            ValidationError
        ):
            transito.full_clean()

    def test_origen_y_destino_no_pueden_ser_iguales(self):
        ruta = Ruta(
            puerto_origen=self.origen,
            puerto_destino=self.origen,
            tipo_ruta="Directo",
        )

        with self.assertRaises(
            ValidationError
        ):
            ruta.full_clean()


class OpcionesContenedorTests(
    BaseCotizadorTestCase
):
    def test_25_tn_requiere_un_contenedor(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 25,
                "unidad_peso": "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta.data["pesoTN"]
            ),
            Decimal("25"),
        )

        for opcion in respuesta.data[
            "opciones"
        ]:
            self.assertEqual(
                opcion["cantidad"],
                1,
            )

    def test_25000_kg_equivale_a_25_tn(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 25000,
                "unidad_peso": "kg",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta.data["pesoTN"]
            ),
            Decimal("25"),
        )

    def test_50_tn_requiere_dos_contenedores(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 50,
                "unidad_peso": "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        for opcion in respuesta.data[
            "opciones"
        ]:
            self.assertEqual(
                opcion["cantidad"],
                2,
            )

    def test_25_001_tn_requiere_dos_contenedores(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 25.001,
                "unidad_peso": "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        for opcion in respuesta.data[
            "opciones"
        ]:
            self.assertEqual(
                opcion["cantidad"],
                2,
            )

    def test_peso_cero_es_rechazado(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 0,
                "unidad_peso": "kg",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_peso_negativo_es_rechazado(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": -25,
                "unidad_peso": "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_peso_texto_es_rechazado(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": "hola",
                "unidad_peso": "kg",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_unidad_invalida_es_rechazada(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 25,
                "unidad_peso": "lb",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_ruta_inexistente_es_rechazada(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": 999999,
                "peso_carga": 25,
                "unidad_peso": "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_campo_no_permitido_es_rechazado(self):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": 25,
                "unidad_peso": "tn",
                "campo_inventado": "prueba",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


class CotizacionTests(BaseCotizadorTestCase):
    def test_cotizacion_20_pies_25_tn(self):
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
            200,
        )

        self.assertEqual(
            respuesta.data["cantidad"],
            1,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMin"
                ]
            ),
            Decimal("1650"),
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMax"
                ]
            ),
            Decimal("2850"),
        )

    def test_cotizacion_40_pies_50_tn(self):
        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    50,

                "unidad_peso":
                    "tn",

                "tipo_contenedor":
                    "40",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.data["cantidad"],
            2,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMin"
                ]
            ),
            Decimal("4700"),
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMax"
                ]
            ),
            Decimal("7700"),
        )

    def test_contingencia_modifica_solo_transito(self):
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

        self.assertEqual(
            respuesta.data[
                "transitoOriginalMin"
            ],
            26,
        )

        self.assertEqual(
            respuesta.data[
                "transitoOriginalMax"
            ],
            34,
        )

        self.assertEqual(
            respuesta.data[
                "transitoMin"
            ],
            29,
        )

        self.assertEqual(
            respuesta.data[
                "transitoMax"
            ],
            37,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMin"
                ]
            ),
            Decimal("1650"),
        )

    def test_contenedor_inexistente_es_rechazado(self):
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
                    "99",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_contingencia_negativa_es_rechazada(self):
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
                    -1,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_contingencia_decimal_es_rechazada(self):
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
                    2.5,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

    def test_contenedor_inactivo_no_se_puede_usar(self):
        self.contenedor_40.activo = False
        self.contenedor_40.save()

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
                    "40",

                "contingencia":
                    0,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


class SeedTests(BaseCotizadorTestCase):
    def test_cargar_datos_no_sobrescribe_tarifa_existente(
        self
    ):
        self.tarifa_20.valor_minimo = (
            Decimal("1666.00")
        )

        self.tarifa_20.save()

        call_command(
            "cargar_datos",
            verbosity=0,
        )

        self.tarifa_20.refresh_from_db()

        self.assertEqual(
            self.tarifa_20.valor_minimo,
            Decimal("1666.00"),
        )