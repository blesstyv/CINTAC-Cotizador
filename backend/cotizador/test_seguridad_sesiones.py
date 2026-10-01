from django.core.cache import cache

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .tests import BaseCotizadorTestCase


class SeguridadSesionesTests(
    BaseCotizadorTestCase
):
    def test_sesion_sin_token_es_rechazada(
        self,
    ):
        cliente = APIClient()

        respuesta = cliente.get(
            "/api/sesion/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_token_inexistente_es_rechazado(
        self,
    ):
        cliente = APIClient()

        cliente.credentials(
            HTTP_AUTHORIZATION=(
                "Token "
                "000000000000000000000000"
                "0000000000000000"
            )
        )

        respuesta = cliente.get(
            "/api/rutas/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_token_malformado_es_rechazado(
        self,
    ):
        cliente = APIClient()

        cliente.credentials(
            HTTP_AUTHORIZATION=
                "Token"
        )

        respuesta = cliente.get(
            "/api/rutas/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_esquema_bearer_no_es_aceptado(
        self,
    ):
        cliente = APIClient()

        cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {self.token.key}"
            )
        )

        respuesta = cliente.get(
            "/api/rutas/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_token_no_funciona_despues_logout(
        self,
    ):
        token_anterior = (
            self.token.key
        )

        respuesta_logout = (
            self.client.post(
                "/api/logout/",
                {},
                format="json",
            )
        )

        self.assertEqual(
            respuesta_logout.status_code,
            200,
        )

        cliente = APIClient()

        cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token_anterior}"
            )
        )

        respuesta = cliente.get(
            "/api/rutas/"
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_logout_sin_token_es_rechazado(
        self,
    ):
        cliente = APIClient()

        respuesta = cliente.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


    def test_segundo_login_invalida_token_anterior(
        self,
    ):
        token_anterior = (
            self.token.key
        )

        cliente_login = (
            APIClient()
        )

        respuesta_login = (
            cliente_login.post(
                "/api/login/",
                {
                    "username":
                        "usuario_test",

                    "password":
                        "ClaveSegura123!",
                },
                format="json",
            )
        )

        self.assertEqual(
            respuesta_login.status_code,
            200,
        )

        token_nuevo = (
            respuesta_login.data[
                "token"
            ]
        )

        self.assertNotEqual(
            token_anterior,
            token_nuevo,
        )

        self.assertFalse(
            Token.objects.filter(
                key=token_anterior
            ).exists()
        )

        cliente_anterior = (
            APIClient()
        )

        cliente_anterior.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token_anterior}"
            )
        )

        respuesta_anterior = (
            cliente_anterior.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_anterior.status_code,
            401,
        )

        cliente_nuevo = APIClient()

        cliente_nuevo.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token_nuevo}"
            )
        )

        respuesta_nueva = (
            cliente_nuevo.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_nueva.status_code,
            200,
        )


    def test_revocar_autorizacion_bloquea_token_activo(
        self,
    ):
        respuesta_inicial = (
            self.client.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_inicial.status_code,
            200,
        )

        perfil = (
            self.usuario
            .perfil_cintac
        )

        perfil.autorizado = False

        perfil.save(
            update_fields=[
                "autorizado",
            ]
        )

        respuesta_posterior = (
            self.client.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_posterior.status_code,
            403,
        )


    def test_revocar_autorizacion_bloquea_sesion_actual(
        self,
    ):
        perfil = (
            self.usuario
            .perfil_cintac
        )

        perfil.autorizado = False

        perfil.save(
            update_fields=[
                "autorizado",
            ]
        )

        respuesta = self.client.get(
            "/api/sesion/"
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_reautorizar_usuario_rehabilita_mismo_token(
        self,
    ):
        perfil = (
            self.usuario
            .perfil_cintac
        )

        perfil.autorizado = False

        perfil.save(
            update_fields=[
                "autorizado",
            ]
        )

        respuesta_bloqueada = (
            self.client.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_bloqueada.status_code,
            403,
        )

        perfil.autorizado = True

        perfil.save(
            update_fields=[
                "autorizado",
            ]
        )

        respuesta_restaurada = (
            self.client.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_restaurada.status_code,
            200,
        )


    def test_usuario_desactivado_pierde_sesion_activa(
        self,
    ):
        respuesta_inicial = (
            self.client.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_inicial.status_code,
            200,
        )

        self.usuario.is_active = False

        self.usuario.save(
            update_fields=[
                "is_active",
            ]
        )

        respuesta_posterior = (
            self.client.get(
                "/api/rutas/"
            )
        )

        self.assertEqual(
            respuesta_posterior.status_code,
            401,
        )


    def test_usuario_inactivo_no_puede_iniciar_sesion(
        self,
    ):
        self.usuario.is_active = False

        self.usuario.save(
            update_fields=[
                "is_active",
            ]
        )

        cliente = APIClient()

        respuesta = cliente.post(
            "/api/login/",
            {
                "username":
                    "usuario_test",

                "password":
                    "ClaveSegura123!",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertNotIn(
            "token",
            respuesta.data,
        )


    def test_sesion_devuelve_permisos_vigentes(
        self,
    ):
        perfil = (
            self.usuario
            .perfil_cintac
        )

        perfil.autorizado = True
        perfil.puede_gestionar_datos = False

        perfil.save(
            update_fields=[
                "autorizado",
                "puede_gestionar_datos",
            ]
        )

        respuesta = self.client.get(
            "/api/sesion/"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertTrue(
            respuesta.data[
                "autorizado"
            ]
        )

        self.assertFalse(
            respuesta.data[
                "puedeGestionarDatos"
            ]
        )


    def test_login_aplica_limite_de_intentos(
        self,
    ):
        cache.clear()

        cliente = APIClient()

        for _ in range(5):
            respuesta = cliente.post(
                "/api/login/",
                {
                    "username":
                        "usuario_test",

                    "password":
                        "incorrecta",
                },
                format="json",

                REMOTE_ADDR=
                    "10.100.100.100",
            )

            self.assertEqual(
                respuesta.status_code,
                400,
            )

        respuesta_bloqueada = (
            cliente.post(
                "/api/login/",
                {
                    "username":
                        "usuario_test",

                    "password":
                        "incorrecta",
                },
                format="json",

                REMOTE_ADDR=
                    "10.100.100.100",
            )
        )

        self.assertEqual(
            respuesta_bloqueada.status_code,
            429,
        )

        cache.clear()