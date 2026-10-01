import tempfile

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

from openpyxl import Workbook

from rest_framework.test import APIClient

from .tests import BaseCotizadorTestCase

from .models import (
    Ruta,
    Tarifa,
)

from .services.importador_datos import (
    COLUMNAS_ESPERADAS,
)


class IntegracionFlujosTests(
    BaseCotizadorTestCase
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.usuario_gestor = (
            User.objects.create_user(
                username="gestor_integracion",
                password="ClaveGestor123!",
            )
        )

        perfil = (
            cls.usuario_gestor
            .perfil_cintac
        )

        perfil.autorizado = True

        perfil.puede_gestionar_datos = True

        perfil.save(
            update_fields=[
                "autorizado",
                "puede_gestionar_datos",
            ]
        )


    def setUp(self):
        super().setUp()

        cache.clear()

        self.temporal = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temporal.cleanup
        )


    def crear_excel(
        self,
        tarifa20_min=1800,
        tarifa20_max=3000,
        tarifa40_min=2500,
        tarifa40_max=4000,
        transito_min=28,
        transito_max=36,
    ):
        ruta_archivo = (
            Path(
                self.temporal.name
            )
            / "actualizacion_cintac.xlsx"
        )

        libro = Workbook()

        hoja = libro.active

        hoja.title = (
            "Tarifas Referencia"
        )

        hoja.append(
            COLUMNAS_ESPERADAS
        )

        hoja.append(
            [
                "Shanghai|Valparaiso",
                "Shanghai",
                "China",
                "Valparaiso",
                "Directo / Transbordo",
                tarifa20_min,
                tarifa20_max,
                tarifa40_min,
                tarifa40_max,
                transito_min,
                transito_max,
                "Fuente integración",
            ]
        )

        libro.save(
            ruta_archivo
        )

        libro.close()

        return ruta_archivo


    def subir_archivo(
        self,
        cliente,
        url,
        ruta_archivo,
    ):
        with open(
            ruta_archivo,
            "rb",
        ) as archivo:
            return cliente.post(
                url,
                {
                    "archivo":
                        archivo,
                },
                format="multipart",
            )


    def iniciar_sesion(
        self,
        username,
        password,
    ):
        cliente = APIClient()

        respuesta = cliente.post(
            "/api/login/",
            {
                "username":
                    username,

                "password":
                    password,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertIn(
            "token",
            respuesta.data,
        )

        token = (
            respuesta.data[
                "token"
            ]
        )

        cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token}"
            )
        )

        return (
            cliente,
            token,
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_flujo_completo_usuario_cotizador(
        self,
        mock_tipo_cambio,
    ):
        mock_tipo_cambio.return_value = {
            "valor":
                Decimal("970.46"),

            "fecha":
                timezone.localdate(),

            "fuente":
                "Fuente integración",

            "modo":
                "en_linea",
        }

        cliente, token = (
            self.iniciar_sesion(
                "usuario_test",
                "ClaveSegura123!",
            )
        )


        respuesta_sesion = (
            cliente.get(
                "/api/sesion/"
            )
        )

        self.assertEqual(
            respuesta_sesion.status_code,
            200,
        )

        self.assertTrue(
            respuesta_sesion.data[
                "autorizado"
            ]
        )

        self.assertFalse(
            respuesta_sesion.data[
                "puedeGestionarDatos"
            ]
        )


        respuesta_rutas = (
            cliente.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_rutas.status_code,
            200,
        )

        self.assertGreater(
            len(
                respuesta_rutas.data
            ),
            0,
        )

        ruta = next(
            item
            for item
            in respuesta_rutas.data
            if (
                item["origen"]
                == "Shanghai"
                and
                item["destino"]
                == "Valparaiso"
            )
        )


        respuesta_opciones = (
            cliente.post(
                "/api/opciones-contenedores/",
                {
                    "ruta_id":
                        ruta["id"],

                    "peso_carga":
                        25000,

                    "unidad_peso":
                        "kg",
                },
                format="json",
            )
        )

        self.assertEqual(
            respuesta_opciones.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta_opciones.data[
                    "pesoTN"
                ]
            ),
            Decimal("25"),
        )

        self.assertEqual(
            respuesta_opciones.data[
                "sugerida"
            ],
            "20",
        )


        respuesta_cotizacion = (
            cliente.post(
                "/api/cotizar/",
                {
                    "ruta_id":
                        ruta["id"],

                    "peso_carga":
                        25000,

                    "unidad_peso":
                        "kg",

                    "tipo_contenedor":
                        "20",

                    "contingencia":
                        3,
                },
                format="json",
            )
        )

        self.assertEqual(
            respuesta_cotizacion.status_code,
            200,
        )

        self.assertEqual(
            respuesta_cotizacion.data[
                "cantidad"
            ],
            1,
        )

        self.assertEqual(
            Decimal(
                respuesta_cotizacion.data[
                    "totalMin"
                ]
            ),
            Decimal("1650"),
        )

        self.assertEqual(
            Decimal(
                respuesta_cotizacion.data[
                    "totalMax"
                ]
            ),
            Decimal("2850"),
        )

        self.assertEqual(
            respuesta_cotizacion.data[
                "transitoMin"
            ],
            29,
        )

        self.assertEqual(
            respuesta_cotizacion.data[
                "transitoMax"
            ],
            37,
        )

        self.assertTrue(
            respuesta_cotizacion.data[
                "conversionDisponible"
            ]
        )

        self.assertEqual(
            Decimal(
                respuesta_cotizacion.data[
                    "totalMinCLP"
                ]
            ),
            Decimal("1601259"),
        )

        self.assertEqual(
            Decimal(
                respuesta_cotizacion.data[
                    "totalMaxCLP"
                ]
            ),
            Decimal("2765811"),
        )


        respuesta_logout = (
            cliente.post(
                "/api/logout/",
                {},
                format="json",
            )
        )

        self.assertEqual(
            respuesta_logout.status_code,
            200,
        )


        cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token}"
            )
        )

        respuesta_posterior = (
            cliente.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_posterior.status_code,
            401,
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    @patch(
        (
            "cotizador.gestion_views."
            "crear_respaldo_sqlite"
        )
    )
    def test_actualizacion_admin_se_refleja_en_cotizador(
        self,
        mock_respaldo,
        mock_tipo_cambio,
    ):
        mock_respaldo.return_value = (
            Path(
                "respaldo_integracion.sqlite3"
            )
        )

        mock_tipo_cambio.return_value = {
            "valor":
                Decimal("970.46"),

            "fecha":
                timezone.localdate(),

            "fuente":
                "Fuente integración",

            "modo":
                "en_linea",
        }


        cliente, _ = (
            self.iniciar_sesion(
                "gestor_integracion",
                "ClaveGestor123!",
            )
        )


        respuesta_sesion = (
            cliente.get(
                "/api/sesion/"
            )
        )

        self.assertEqual(
            respuesta_sesion.status_code,
            200,
        )

        self.assertTrue(
            respuesta_sesion.data[
                "puedeGestionarDatos"
            ]
        )


        tarifa_antes = (
            Tarifa.objects.get(
                ruta=self.ruta,
                tipo_contenedor="20",
            )
        )

        self.assertEqual(
            tarifa_antes.valor_minimo,
            Decimal("1650.00"),
        )


        archivo = self.crear_excel()


        respuesta_validacion = (
            self.subir_archivo(
                cliente,
                (
                    "/api/administracion/"
                    "validar-excel/"
                ),
                archivo,
            )
        )

        self.assertEqual(
            respuesta_validacion.status_code,
            200,
        )

        self.assertTrue(
            respuesta_validacion.data[
                "valido"
            ]
        )

        self.assertEqual(
            respuesta_validacion.data[
                "filasValidas"
            ],
            1,
        )


        respuesta_importacion = (
            self.subir_archivo(
                cliente,
                (
                    "/api/administracion/"
                    "importar-excel/"
                ),
                archivo,
            )
        )

        self.assertEqual(
            respuesta_importacion.status_code,
            200,
        )

        self.assertTrue(
            respuesta_importacion.data[
                "importado"
            ]
        )

        mock_respaldo.assert_called_once()


        tarifa_despues = (
            Tarifa.objects.get(
                ruta=self.ruta,
                tipo_contenedor="20",
            )
        )

        self.assertEqual(
            tarifa_despues.valor_minimo,
            Decimal("1800.00"),
        )

        self.assertEqual(
            tarifa_despues.valor_maximo,
            Decimal("3000.00"),
        )


        respuesta_rutas = (
            cliente.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_rutas.status_code,
            200,
        )

        ruta_actualizada = next(
            item
            for item
            in respuesta_rutas.data
            if (
                item["origen"]
                == "Shanghai"
                and
                item["destino"]
                == "Valparaiso"
            )
        )

        tarifa_20 = next(
            tarifa
            for tarifa
            in ruta_actualizada[
                "tarifas"
            ]
            if (
                tarifa[
                    "tipoContenedor"
                ]
                == "20"
            )
        )

        self.assertEqual(
            Decimal(
                tarifa_20[
                    "valorMinimo"
                ]
            ),
            Decimal("1800.00"),
        )

        self.assertEqual(
            Decimal(
                tarifa_20[
                    "valorMaximo"
                ]
            ),
            Decimal("3000.00"),
        )


        respuesta_cotizacion = (
            cliente.post(
                "/api/cotizar/",
                {
                    "ruta_id":
                        ruta_actualizada[
                            "id"
                        ],

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
        )

        self.assertEqual(
            respuesta_cotizacion.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta_cotizacion.data[
                    "totalMin"
                ]
            ),
            Decimal("1800"),
        )

        self.assertEqual(
            Decimal(
                respuesta_cotizacion.data[
                    "totalMax"
                ]
            ),
            Decimal("3000"),
        )

        self.assertEqual(
            respuesta_cotizacion.data[
                "transitoMin"
            ],
            28,
        )

        self.assertEqual(
            respuesta_cotizacion.data[
                "transitoMax"
            ],
            36,
        )

        self.assertEqual(
            respuesta_cotizacion.data[
                "fuente"
            ],
            "Fuente integración",
        )


    @patch(
        (
            "cotizador.gestion_views."
            "crear_respaldo_sqlite"
        )
    )
    def test_excel_invalido_no_modifica_cotizador(
        self,
        mock_respaldo,
    ):
        cliente, _ = (
            self.iniciar_sesion(
                "gestor_integracion",
                "ClaveGestor123!",
            )
        )


        ruta_antes = (
            Ruta.objects.get(
                id=self.ruta.id
            )
        )

        tarifa_antes = (
            Tarifa.objects.get(
                ruta=ruta_antes,
                tipo_contenedor="20",
            )
        )

        valor_minimo_antes = (
            tarifa_antes.valor_minimo
        )

        cantidad_rutas_antes = (
            Ruta.objects.count()
        )

        cantidad_tarifas_antes = (
            Tarifa.objects.count()
        )


        archivo = self.crear_excel(
            tarifa20_min=-100,
        )


        respuesta_validacion = (
            self.subir_archivo(
                cliente,
                (
                    "/api/administracion/"
                    "validar-excel/"
                ),
                archivo,
            )
        )

        self.assertEqual(
            respuesta_validacion.status_code,
            400,
        )

        self.assertFalse(
            respuesta_validacion.data[
                "valido"
            ]
        )


        respuesta_importacion = (
            self.subir_archivo(
                cliente,
                (
                    "/api/administracion/"
                    "importar-excel/"
                ),
                archivo,
            )
        )

        self.assertEqual(
            respuesta_importacion.status_code,
            400,
        )

        self.assertFalse(
            respuesta_importacion.data[
                "importado"
            ]
        )


        tarifa_antes.refresh_from_db()

        self.assertEqual(
            tarifa_antes.valor_minimo,
            valor_minimo_antes,
        )

        self.assertEqual(
            Ruta.objects.count(),
            cantidad_rutas_antes,
        )

        self.assertEqual(
            Tarifa.objects.count(),
            cantidad_tarifas_antes,
        )

        mock_respaldo.assert_not_called()


    def test_gestor_revocado_conserva_cotizador_pero_pierde_administracion(
        self,
    ):
        cliente, _ = (
            self.iniciar_sesion(
                "gestor_integracion",
                "ClaveGestor123!",
            )
        )


        respuesta_admin_inicial = (
            cliente.get(
                "/api/administracion/resumen/"
            )
        )

        self.assertEqual(
            respuesta_admin_inicial.status_code,
            200,
        )


        perfil = (
            self.usuario_gestor
            .perfil_cintac
        )

        perfil.puede_gestionar_datos = False

        perfil.save(
            update_fields=[
                "puede_gestionar_datos",
            ]
        )


        respuesta_admin_posterior = (
            cliente.get(
                "/api/administracion/resumen/"
            )
        )

        self.assertEqual(
            respuesta_admin_posterior.status_code,
            403,
        )


        respuesta_cotizador = (
            cliente.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_cotizador.status_code,
            200,
        )


        respuesta_sesion = (
            cliente.get(
                "/api/sesion/"
            )
        )

        self.assertEqual(
            respuesta_sesion.status_code,
            200,
        )

        self.assertTrue(
            respuesta_sesion.data[
                "autorizado"
            ]
        )

        self.assertFalse(
            respuesta_sesion.data[
                "puedeGestionarDatos"
            ]
        )