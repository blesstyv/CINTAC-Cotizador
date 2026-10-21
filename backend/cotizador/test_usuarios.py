from django.contrib.auth.models import User
from django.test import TestCase

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import PerfilUsuario


class GestionUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_normal = (
            User.objects.create_user(
                username="usuario_normal",
                first_name="Usuario",
                last_name="Normal",
                email="usuario@cintac.cl",
                password="ClaveSegura123!",
            )
        )

        perfil_usuario = (
            cls.usuario_normal
            .perfil_cintac
        )

        perfil_usuario.rol = (
            PerfilUsuario.Rol.USUARIO
        )

        perfil_usuario.autorizado = True

        perfil_usuario.puede_gestionar_datos = False

        perfil_usuario.save()


        cls.encargado = (
            User.objects.create_user(
                username="encargado",
                first_name="Usuario",
                last_name="Encargado",
                email="encargado@cintac.cl",
                password="ClaveSegura123!",
            )
        )

        perfil_encargado = (
            cls.encargado
            .perfil_cintac
        )

        perfil_encargado.rol = (
            PerfilUsuario.Rol.ENCARGADO
        )

        perfil_encargado.autorizado = True

        perfil_encargado.puede_gestionar_datos = True

        perfil_encargado.save()


        cls.admin = (
            User.objects.create_user(
                username="administrador",
                first_name="Admin",
                last_name="Cintac",
                email="admin@cintac.cl",
                password="ClaveSegura123!",
            )
        )

        perfil_admin = (
            cls.admin
            .perfil_cintac
        )

        perfil_admin.rol = (
            PerfilUsuario.Rol.ADMINISTRADOR
        )

        perfil_admin.autorizado = True

        perfil_admin.puede_gestionar_datos = True

        perfil_admin.save()


        cls.superusuario = (
            User.objects.create_superuser(
                username="superadmin",
                email="superadmin@cintac.cl",
                password="ClaveSuper123!",
            )
        )


    def setUp(self):
        self.client = APIClient()


    def autenticar(
        self,
        usuario,
    ):
        token, _ = (
            Token.objects.get_or_create(
                user=usuario
            )
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token.key}"
            )
        )

        return token


    def datos_usuario_valido(
        self,
        **cambios,
    ):
        datos = {
            "username":
                "nuevo_usuario",

            "first_name":
                "Nuevo",

            "last_name":
                "Usuario",

            "email":
                "nuevo.usuario@cintac.cl",

            "password":
                "ClaveNueva123!",

            "password_confirm":
                "ClaveNueva123!",

            "rol":
                PerfilUsuario
                .Rol
                .USUARIO,

            "activo":
                True,
        }

        datos.update(
            cambios
        )

        return datos


    def test_usuario_normal_no_puede_listar_usuarios(
        self,
    ):
        self.autenticar(
            self.usuario_normal
        )

        respuesta = self.client.get(
            "/api/administracion/usuarios/"
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_encargado_no_puede_listar_usuarios(
        self,
    ):
        self.autenticar(
            self.encargado
        )

        respuesta = self.client.get(
            "/api/administracion/usuarios/"
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_administrador_puede_listar_usuarios(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.get(
            "/api/administracion/usuarios/"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertIn(
            "usuarios",
            respuesta.data,
        )

        self.assertGreaterEqual(
            respuesta.data[
                "cantidad"
            ],
            4,
        )


    def test_superusuario_puede_listar_usuarios(
        self,
    ):
        self.autenticar(
            self.superusuario
        )

        respuesta = self.client.get(
            "/api/administracion/usuarios/"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )


    def test_administrador_puede_crear_usuario(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            201,
        )

        creado = User.objects.get(
            username="nuevo_usuario"
        )

        self.assertTrue(
            creado.check_password(
                "ClaveNueva123!"
            )
        )

        self.assertEqual(
            creado.email,
            "nuevo.usuario@cintac.cl",
        )

        self.assertEqual(
            creado
            .perfil_cintac
            .rol,
            PerfilUsuario.Rol.USUARIO,
        )

        self.assertTrue(
            creado
            .perfil_cintac
            .autorizado
        )

        self.assertFalse(
            creado
            .perfil_cintac
            .puede_gestionar_datos
        )


    def test_crear_encargado_asigna_permisos_correctos(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                username="nuevo_encargado",
                email="nuevo.encargado@cintac.cl",
                rol=
                    PerfilUsuario
                    .Rol
                    .ENCARGADO,
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            201,
        )

        creado = User.objects.get(
            username="nuevo_encargado"
        )

        self.assertEqual(
            creado
            .perfil_cintac
            .rol,
            PerfilUsuario.Rol.ENCARGADO,
        )

        self.assertTrue(
            creado
            .perfil_cintac
            .puede_gestionar_datos
        )


    def test_crear_administrador_asigna_permisos_correctos(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                username="nuevo_admin",
                email="nuevo.admin@cintac.cl",
                rol=
                    PerfilUsuario
                    .Rol
                    .ADMINISTRADOR,
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            201,
        )

        creado = User.objects.get(
            username="nuevo_admin"
        )

        self.assertEqual(
            creado
            .perfil_cintac
            .rol,
            PerfilUsuario
            .Rol
            .ADMINISTRADOR,
        )

        self.assertTrue(
            creado
            .perfil_cintac
            .puede_gestionar_datos
        )


    def test_usuario_normal_no_puede_crear_usuario(
        self,
    ):
        self.autenticar(
            self.usuario_normal
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_encargado_no_puede_crear_usuario(
        self,
    ):
        self.autenticar(
            self.encargado
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            403,
        )


    def test_username_duplicado_es_rechazado(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                username="USUARIO_NORMAL",
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertIn(
            "username",
            respuesta.data,
        )


    def test_email_duplicado_es_rechazado(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                email="USUARIO@CINTAC.CL",
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertIn(
            "email",
            respuesta.data,
        )


    def test_email_invalido_es_rechazado(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                email="correo-invalido",
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertIn(
            "email",
            respuesta.data,
        )


    def test_passwords_distintos_son_rechazados(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                password_confirm=
                    "OtraClave123!",
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertIn(
            "password_confirm",
            respuesta.data,
        )


    def test_password_debil_es_rechazado(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                password="12345678",
                password_confirm="12345678",
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_rol_invalido_es_rechazado(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            self.datos_usuario_valido(
                rol="SUPERGERENTE",
            ),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.assertIn(
            "rol",
            respuesta.data,
        )


    def test_campo_extra_es_rechazado(
        self,
    ):
        self.autenticar(
            self.admin
        )

        datos = (
            self.datos_usuario_valido()
        )

        datos[
            "es_superusuario"
        ] = True

        respuesta = self.client.post(
            "/api/administracion/usuarios/",
            datos,
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


    def test_administrador_puede_editar_usuario(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.usuario_normal.id}/"
            ),
            {
                "first_name":
                    "Javier",

                "last_name":
                    "Actualizado",

                "email":
                    "javier.actualizado@cintac.cl",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.usuario_normal.refresh_from_db()

        self.assertEqual(
            self.usuario_normal.first_name,
            "Javier",
        )

        self.assertEqual(
            self.usuario_normal.last_name,
            "Actualizado",
        )

        self.assertEqual(
            self.usuario_normal.email,
            "javier.actualizado@cintac.cl",
        )


    def test_administrador_puede_cambiar_rol(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.usuario_normal.id}/"
            ),
            {
                "rol":
                    PerfilUsuario
                    .Rol
                    .ENCARGADO,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.usuario_normal.refresh_from_db()

        perfil = (
            self.usuario_normal
            .perfil_cintac
        )

        perfil.refresh_from_db()

        self.assertEqual(
            perfil.rol,
            PerfilUsuario.Rol.ENCARGADO,
        )

        self.assertTrue(
            perfil.puede_gestionar_datos
        )


    def test_administrador_puede_desactivar_usuario(
        self,
    ):
        token_usuario = (
            Token.objects.create(
                user=self.usuario_normal
            )
        )

        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.usuario_normal.id}/"
            ),
            {
                "activo":
                    False,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.usuario_normal.refresh_from_db()

        self.assertFalse(
            self.usuario_normal.is_active
        )

        self.assertFalse(
            Token.objects.filter(
                key=token_usuario.key
            ).exists()
        )


    def test_administrador_no_puede_desactivarse_a_si_mismo(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.admin.id}/"
            ),
            {
                "activo":
                    False,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )

        self.admin.refresh_from_db()

        self.assertTrue(
            self.admin.is_active
        )


    def test_administrador_no_puede_quitarse_su_rol(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.admin.id}/"
            ),
            {
                "rol":
                    PerfilUsuario
                    .Rol
                    .USUARIO,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_ultimo_administrador_no_puede_perder_rol(
        self,
    ):
        otro_cliente = APIClient()

        token, _ = (
            Token.objects.get_or_create(
                user=self.superusuario
            )
        )

        otro_cliente.credentials(
            HTTP_AUTHORIZATION=(
                f"Token {token.key}"
            )
        )

        respuesta = otro_cliente.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.admin.id}/"
            ),
            {
                "rol":
                    PerfilUsuario
                    .Rol
                    .USUARIO,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_superusuario_no_puede_modificarse_desde_api(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.superusuario.id}/"
            ),
            {
                "activo":
                    False,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_administrador_puede_cambiar_password_de_usuario(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.usuario_normal.id}/"
            ),
            {
                "password":
                    "NuevaClave456!",

                "password_confirm":
                    "NuevaClave456!",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.usuario_normal.refresh_from_db()

        self.assertTrue(
            self.usuario_normal
            .check_password(
                "NuevaClave456!"
            )
        )


    def test_password_nueva_sin_confirmacion_es_rechazada(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.patch(
            (
                "/api/administracion/"
                f"usuarios/{self.usuario_normal.id}/"
            ),
            {
                "password":
                    "NuevaClave456!",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_usuario_inexistente_retorna_404(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.get(
            "/api/administracion/usuarios/999999/"
        )

        self.assertEqual(
            respuesta.status_code,
            404,
        )


    def test_filtro_por_rol_funciona(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.get(
            (
                "/api/administracion/usuarios/"
                "?rol=ENCARGADO"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        for usuario in (
            respuesta.data[
                "usuarios"
            ]
        ):
            self.assertEqual(
                usuario["rol"],
                PerfilUsuario
                .Rol
                .ENCARGADO,
            )


    def test_filtro_rol_invalido_es_rechazado(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.get(
            (
                "/api/administracion/usuarios/"
                "?rol=NO_EXISTE"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            400,
        )


    def test_busqueda_usuario_funciona(
        self,
    ):
        self.autenticar(
            self.admin
        )

        respuesta = self.client.get(
            (
                "/api/administracion/usuarios/"
                "?q=encargado"
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        usernames = [
            usuario["username"]
            for usuario
            in respuesta.data[
                "usuarios"
            ]
        ]

        self.assertIn(
            "encargado",
            usernames,
        )