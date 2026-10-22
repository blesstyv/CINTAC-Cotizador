from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import (
    Cotizacion,
    PerfilUsuario,
)

from .tests import BaseCotizadorTestCase

from .services.tipo_cambio import (
    TipoCambioNoDisponible,
)


class HistorialCotizacionesTests(
    BaseCotizadorTestCase
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.otro_usuario = (
            User.objects.create_user(
                username="otro_usuario",
                password="ClaveSegura123!",
            )
        )

        perfil = (
            cls.otro_usuario
            .perfil_cintac
        )

        perfil.autorizado = True

        perfil.rol = (
            PerfilUsuario.Rol.USUARIO
        )

        perfil.save()


        cls.encargado = (
            User.objects.create_user(
                username="encargado_historial",
                password="ClaveSegura123!",
            )
        )

        perfil = (
            cls.encargado
            .perfil_cintac
        )

        perfil.autorizado = True

        perfil.rol = (
            PerfilUsuario.Rol.ENCARGADO
        )

        perfil.puede_gestionar_datos = True

        perfil.save()


        cls.administrador = (
            User.objects.create_user(
                username="admin_historial",
                password="ClaveSegura123!",
            )
        )

        perfil = (
            cls.administrador
            .perfil_cintac
        )

        perfil.autorizado = True

        perfil.rol = (
            PerfilUsuario
            .Rol
            .ADMINISTRADOR
        )

        perfil.puede_gestionar_datos = True

        perfil.save()


    def cliente_usuario(
        self,
        usuario,
    ):
        cliente = APIClient()

        token, _ = (
            Token.objects.get_or_create(
                user=usuario
            )
        )

        cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token.key}"
            )
        )

        return cliente


    def crear_cotizacion_directa(
        self,
        usuario,
        origen="Shanghai",
        destino="Valparaiso",
        contenedor="20",
    ):
        return (
            Cotizacion.objects.create(
                usuario=
                    usuario,

                origen=
                    origen,

                pais_origen=
                    "China",

                destino=
                    destino,

                tipo_ruta=
                    "Directo / Transbordo",

                peso_kg=
                    Decimal("23000"),

                peso_tn=
                    Decimal("23"),

                tipo_contenedor=
                    contenedor,

                nombre_contenedor=
                    (
                        "Contenedor 20'"
                        if contenedor
                        == "20"
                        else
                        "Contenedor 40'"
                    ),

                capacidad_tn=
                    (
                        Decimal("23")
                        if contenedor
                        == "20"
                        else
                        Decimal("25")
                    ),

                cantidad=
                    1,

                tarifa_min=
                    Decimal("1650"),

                tarifa_max=
                    Decimal("2850"),

                total_min=
                    Decimal("1650"),

                total_max=
                    Decimal("2850"),

                es_sugerida=
                    True,

                contingencia=
                    0,

                transito_original_min=
                    26,

                transito_original_max=
                    34,

                transito_min=
                    26,

                transito_max=
                    34,

                fuente_tarifa=
                    "Fuente prueba",

                conversion_disponible=
                    False,
            )
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_cotizacion_exitosa_se_guarda_en_historial(
        self,
        mock_tipo_cambio,
    ):
        mock_tipo_cambio.return_value = {
            "valor":
                Decimal("970.46"),

            "fecha":
                timezone.localdate(),

            "fuente":
                "Fuente prueba",

            "modo":
                "en_linea",
        }

        cantidad_antes = (
            Cotizacion.objects.count()
        )

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    23,

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
            Cotizacion.objects.count(),
            cantidad_antes + 1,
        )

        self.assertIn(
            "historialId",
            respuesta.data,
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_historial_guarda_snapshot_correcto(
        self,
        mock_tipo_cambio,
    ):
        mock_tipo_cambio.return_value = {
            "valor":
                Decimal("970.46"),

            "fecha":
                timezone.localdate(),

            "fuente":
                "Banco Central",

            "modo":
                "en_linea",
        }

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
                    2,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        registro = (
            Cotizacion.objects.get(
                id=
                    respuesta.data[
                        "historialId"
                    ]
            )
        )

        self.assertEqual(
            registro.usuario,
            self.usuario,
        )

        self.assertEqual(
            registro.origen,
            "Shanghai",
        )

        self.assertEqual(
            registro.destino,
            "Valparaiso",
        )

        self.assertEqual(
            registro.tipo_contenedor,
            "20",
        )

        self.assertEqual(
            registro.cantidad,
            2,
        )

        self.assertEqual(
            registro.total_min,
            Decimal("3300"),
        )

        self.assertEqual(
            registro.total_max,
            Decimal("5700"),
        )

        self.assertEqual(
            registro.contingencia,
            2,
        )

        self.assertEqual(
            registro.transito_min,
            28,
        )

        self.assertEqual(
            registro.transito_max,
            36,
        )

        self.assertEqual(
            registro.tipo_cambio,
            Decimal("970.46"),
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_historial_se_guarda_aunque_conversion_no_este_disponible(
        self,
        mock_tipo_cambio,
    ):
        mock_tipo_cambio.side_effect = (
            TipoCambioNoDisponible(
                "Sin conexión"
            )
        )

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    23,

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

        registro = (
            Cotizacion.objects.get(
                id=
                    respuesta.data[
                        "historialId"
                    ]
            )
        )

        self.assertFalse(
            registro
            .conversion_disponible
        )

        self.assertIsNone(
            registro.tipo_cambio
        )

        self.assertIsNone(
            registro.total_min_clp
        )


    def test_usuario_solo_ve_sus_cotizaciones(
        self,
    ):
        propia = (
            self.crear_cotizacion_directa(
                self.usuario
            )
        )

        ajena = (
            self.crear_cotizacion_directa(
                self.otro_usuario
            )
        )

        respuesta = self.client.get(
            "/api/historial/"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        ids = {
            item["id"]
            for item
            in respuesta.data[
                "cotizaciones"
            ]
        }

        self.assertIn(
            propia.id,
            ids,
        )

        self.assertNotIn(
            ajena.id,
            ids,
        )

        self.assertFalse(
            respuesta.data[
                "puedeVerTodas"
            ]
        )


    def test_usuario_no_puede_filtrar_otro_usuario(
        self,
    ):
        respuesta = self.client.get(
            (
                "/api/historial/"
                f"?usuario_id={self.otro_usuario.id}"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_usuario_no_puede_ver_detalle_ajeno(
        self,
    ):
        ajena = (
            self.crear_cotizacion_directa(
                self.otro_usuario
            )
        )

        respuesta = self.client.get(
            (
                "/api/historial/"
                f"{ajena.id}/"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            404,
        )


    def test_encargado_puede_ver_historial_general(
        self,
    ):
        primera = (
            self.crear_cotizacion_directa(
                self.usuario
            )
        )

        segunda = (
            self.crear_cotizacion_directa(
                self.otro_usuario
            )
        )

        cliente = (
            self.cliente_usuario(
                self.encargado
            )
        )

        respuesta = cliente.get(
            "/api/historial/"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        ids = {
            item["id"]
            for item
            in respuesta.data[
                "cotizaciones"
            ]
        }

        self.assertIn(
            primera.id,
            ids,
        )

        self.assertIn(
            segunda.id,
            ids,
        )

        self.assertTrue(
            respuesta.data[
                "puedeVerTodas"
            ]
        )


    def test_administrador_puede_ver_historial_general(
        self,
    ):
        self.crear_cotizacion_directa(
            self.usuario
        )

        cliente = (
            self.cliente_usuario(
                self.administrador
            )
        )

        respuesta = cliente.get(
            "/api/historial/"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertTrue(
            respuesta.data[
                "puedeVerTodas"
            ]
        )


    def test_encargado_puede_filtrar_por_usuario(
        self,
    ):
        propia = (
            self.crear_cotizacion_directa(
                self.usuario
            )
        )

        self.crear_cotizacion_directa(
            self.otro_usuario
        )

        cliente = (
            self.cliente_usuario(
                self.encargado
            )
        )

        respuesta = cliente.get(
            (
                "/api/historial/"
                f"?usuario_id={self.usuario.id}"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        ids = [
            item["id"]
            for item
            in respuesta.data[
                "cotizaciones"
            ]
        ]

        self.assertEqual(
            ids,
            [propia.id],
        )


    def test_filtro_por_contenedor_funciona(
        self,
    ):
        veinte = (
            self.crear_cotizacion_directa(
                self.usuario,
                contenedor="20",
            )
        )

        self.crear_cotizacion_directa(
            self.usuario,
            contenedor="40",
        )

        respuesta = self.client.get(
            (
                "/api/historial/"
                "?contenedor=20"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        ids = [
            item["id"]
            for item
            in respuesta.data[
                "cotizaciones"
            ]
        ]

        self.assertEqual(
            ids,
            [veinte.id],
        )


    def test_filtro_contenedor_invalido_es_rechazado(
        self,
    ):
        respuesta = self.client.get(
            (
                "/api/historial/"
                "?contenedor=99"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_filtro_origen_funciona(
        self,
    ):
        shanghai = (
            self.crear_cotizacion_directa(
                self.usuario,
                origen="Shanghai",
            )
        )

        self.crear_cotizacion_directa(
            self.usuario,
            origen="Busan",
        )

        respuesta = self.client.get(
            (
                "/api/historial/"
                "?origen=Shanghai"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        ids = [
            item["id"]
            for item
            in respuesta.data[
                "cotizaciones"
            ]
        ]

        self.assertEqual(
            ids,
            [shanghai.id],
        )


    def test_fecha_invalida_es_rechazada(
        self,
    ):
        respuesta = self.client.get(
            (
                "/api/historial/"
                "?desde=20-10-2026"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_rango_fechas_invertido_es_rechazado(
        self,
    ):
        respuesta = self.client.get(
            (
                "/api/historial/"
                "?desde=2026-10-21"
                "&hasta=2026-10-20"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_detalle_propio_puede_consultarse(
        self,
    ):
        registro = (
            self.crear_cotizacion_directa(
                self.usuario
            )
        )

        respuesta = self.client.get(
            (
                "/api/historial/"
                f"{registro.id}/"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.data[
                "cotizacion"
            ][
                "id"
            ],
            registro.id,
        )