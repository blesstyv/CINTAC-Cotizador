import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from openpyxl import Workbook

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from cotizador.models import (
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
)

from cotizador.services.importador_datos import (
    COLUMNAS_ESPERADAS,
)


class GestionDatosAPITests(TestCase):
    def setUp(self):
        self.temporal = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temporal.cleanup
        )

        self.usuario_gestor = (
            User.objects.create_user(
                username="gestor",
                password="ClaveSegura123!",
            )
        )

        perfil_gestor = (
            self.usuario_gestor
            .perfil_cintac
        )

        perfil_gestor.autorizado = True
        perfil_gestor.puede_gestionar_datos = True

        perfil_gestor.save()

        self.usuario_normal = (
            User.objects.create_user(
                username="normal",
                password="ClaveSegura123!",
            )
        )

        perfil_normal = (
            self.usuario_normal
            .perfil_cintac
        )

        perfil_normal.autorizado = True
        perfil_normal.puede_gestionar_datos = False

        perfil_normal.save()

        self.cliente_gestor = APIClient()

        token_gestor = (
            Token.objects.create(
                user=self.usuario_gestor
            )
        )

        self.cliente_gestor.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token_gestor.key}"
            )
        )

        self.cliente_normal = APIClient()

        token_normal = (
            Token.objects.create(
                user=self.usuario_normal
            )
        )

        self.cliente_normal.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token_normal.key}"
            )
        )


    def crear_excel(
        self,
        tarifa_minima=1650,
    ):
        ruta = (
            Path(
                self.temporal.name
            )
            / "tarifas.xlsx"
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
                tarifa_minima,
                2850,
                2350,
                3850,
                26,
                34,
                (
                    "Segucargo / "
                    "Delpa Group 2026"
                ),
            ]
        )

        libro.save(
            ruta
        )

        libro.close()

        return ruta


    def subir_archivo(
        self,
        cliente,
        url,
        ruta,
    ):
        with open(
            ruta,
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


    def test_sin_token_no_accede_resumen(
        self,
    ):
        cliente = APIClient()

        respuesta = cliente.get(
            "/api/administracion/resumen/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_usuario_normal_no_accede_resumen(
        self,
    ):
        respuesta = (
            self.cliente_normal.get(
                "/api/administracion/resumen/"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_gestor_accede_resumen(
        self,
    ):
        respuesta = (
            self.cliente_gestor.get(
                "/api/administracion/resumen/"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertIn(
            "rutas",
            respuesta.data,
        )

        self.assertIn(
            "tarifas",
            respuesta.data,
        )


    def test_gestor_valida_excel_correcto(
        self,
    ):
        ruta = self.crear_excel()

        respuesta = self.subir_archivo(
            self.cliente_gestor,
            (
                "/api/administracion/"
                "validar-excel/"
            ),
            ruta,
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertTrue(
            respuesta.data[
                "valido"
            ]
        )

        self.assertEqual(
            respuesta.data[
                "filasValidas"
            ],
            1,
        )


    def test_usuario_normal_no_puede_validar(
        self,
    ):
        ruta = self.crear_excel()

        respuesta = self.subir_archivo(
            self.cliente_normal,
            (
                "/api/administracion/"
                "validar-excel/"
            ),
            ruta,
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_excel_invalido_es_rechazado(
        self,
    ):
        ruta = self.crear_excel(
            tarifa_minima=-100
        )

        respuesta = self.subir_archivo(
            self.cliente_gestor,
            (
                "/api/administracion/"
                "validar-excel/"
            ),
            ruta,
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertFalse(
            respuesta.data[
                "valido"
            ]
        )

        self.assertGreater(
            len(
                respuesta.data[
                    "errores"
                ]
            ),
            0,
        )


    @patch(
        (
            "cotizador.gestion_views."
            "crear_respaldo_sqlite"
        )
    )
    def test_gestor_importa_excel_valido(
        self,
        mock_respaldo,
    ):
        mock_respaldo.return_value = (
            Path(
                "respaldo.sqlite3"
            )
        )

        ruta = self.crear_excel()

        respuesta = self.subir_archivo(
            self.cliente_gestor,
            (
                "/api/administracion/"
                "importar-excel/"
            ),
            ruta,
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertTrue(
            respuesta.data[
                "importado"
            ]
        )

        self.assertEqual(
            Puerto.objects.count(),
            2,
        )

        self.assertEqual(
            Ruta.objects.count(),
            1,
        )

        self.assertEqual(
            Tarifa.objects.count(),
            2,
        )

        self.assertEqual(
            TiempoTransito.objects.count(),
            1,
        )

        mock_respaldo.assert_called_once()


    def test_usuario_normal_no_puede_importar(
        self,
    ):
        ruta = self.crear_excel()

        respuesta = self.subir_archivo(
            self.cliente_normal,
            (
                "/api/administracion/"
                "importar-excel/"
            ),
            ruta,
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_importacion_sin_archivo_es_rechazada(
        self,
    ):
        respuesta = (
            self.cliente_gestor.post(
                (
                    "/api/administracion/"
                    "importar-excel/"
                ),
                {},
                format="multipart",
            )
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_archivo_no_excel_es_rechazado(
        self,
    ):
        ruta = (
            Path(
                self.temporal.name
            )
            / "archivo.txt"
        )

        ruta.write_text(
            "contenido",
            encoding="utf-8",
        )

        respuesta = self.subir_archivo(
            self.cliente_gestor,
            (
                "/api/administracion/"
                "validar-excel/"
            ),
            ruta,
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_permiso_revocado_bloquea_token_existente(
        self,
    ):
        respuesta_inicial = (
            self.cliente_gestor.get(
                "/api/administracion/resumen/"
            )
        )

        self.assertEqual(
            respuesta_inicial.status_code,
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

        respuesta_posterior = (
            self.cliente_gestor.get(
                "/api/administracion/resumen/"
            )
        )

        self.assertEqual(
            respuesta_posterior.status_code,
            403,
        )