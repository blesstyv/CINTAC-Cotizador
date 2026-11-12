"""
Pruebas EVA3 de seguridad, permisos por rol, exportación CSV,
paginación, vista previa del Excel, bitácora y recuperación de datos.
"""

import csv
import io
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .historial_views import celda_csv_segura
from .models import (
    Cotizacion,
    OperacionDatosMaestros,
    PerfilUsuario,
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)
from .services.datos_maestros import (
    InstantaneaInvalida,
    capturar_estado,
    restaurar_estado,
)
from .services.importador_datos import COLUMNAS_ESPERADAS


def _crear_usuario(username, rol, autorizado=True, **extra):
    usuario = User.objects.create_user(
        username=username,
        password="ClaveSegura123!",
        **extra,
    )
    perfil = usuario.perfil_cintac
    perfil.rol = rol
    perfil.autorizado = autorizado
    perfil.puede_gestionar_datos = rol in {
        PerfilUsuario.Rol.ENCARGADO,
        PerfilUsuario.Rol.ADMINISTRADOR,
    }
    perfil.save()
    return usuario


def _cliente(usuario):
    cliente = APIClient()
    token, _ = Token.objects.get_or_create(user=usuario)
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return cliente


class BaseEva3(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = _crear_usuario("usuario_eva3", PerfilUsuario.Rol.USUARIO)
        cls.otro = _crear_usuario("otro_eva3", PerfilUsuario.Rol.USUARIO)
        cls.encargado = _crear_usuario(
            "encargado_eva3", PerfilUsuario.Rol.ENCARGADO
        )
        cls.administrador = _crear_usuario(
            "administrador_eva3", PerfilUsuario.Rol.ADMINISTRADOR
        )

        cls.origen = Puerto.objects.create(nombre="Shanghai", pais="China")
        cls.destino = Puerto.objects.create(nombre="Valparaiso", pais="Chile")
        cls.ruta = Ruta.objects.create(
            puerto_origen=cls.origen,
            puerto_destino=cls.destino,
            tipo_ruta="Directo / Transbordo",
        )
        TipoContenedor.objects.create(
            codigo="20", nombre="Contenedor 20'", capacidad_tn=Decimal("23")
        )
        TipoContenedor.objects.create(
            codigo="40", nombre="Contenedor 40'", capacidad_tn=Decimal("25")
        )
        Tarifa.objects.create(
            ruta=cls.ruta,
            tipo_contenedor="20",
            valor_minimo=Decimal("1650"),
            valor_maximo=Decimal("2850"),
            fuente="Fuente",
        )
        Tarifa.objects.create(
            ruta=cls.ruta,
            tipo_contenedor="40",
            valor_minimo=Decimal("2350"),
            valor_maximo=Decimal("3850"),
            fuente="Fuente",
        )
        TiempoTransito.objects.create(
            ruta=cls.ruta, dias_minimos=26, dias_maximos=34
        )

    def setUp(self):
        cache.clear()

    def crear_cotizacion(self, usuario, origen="Shanghai", **extra):
        datos = dict(
            usuario=usuario,
            origen=origen,
            pais_origen="China",
            destino="Valparaiso",
            tipo_ruta="Directo",
            peso_kg=Decimal("1000"),
            peso_tn=Decimal("1"),
            tipo_contenedor="20",
            nombre_contenedor="Contenedor 20'",
            capacidad_tn=Decimal("23"),
            cantidad=1,
            tarifa_min=Decimal("1650"),
            tarifa_max=Decimal("2850"),
            total_min=Decimal("1650"),
            total_max=Decimal("2850"),
            total_final_min=Decimal("1650"),
            total_final_max=Decimal("2850"),
        )
        datos.update(extra)
        return Cotizacion.objects.create(**datos)


# ----------------------------------------------------------------------
# Autenticación
# ----------------------------------------------------------------------


@override_settings(LOGIN_MAX_FALLOS=3, LOGIN_BLOQUEO_SEGUNDOS=600)
class BloqueoPorCuentaTests(BaseEva3):

    def _login(self, password, ip):
        return APIClient().post(
            "/api/login/",
            {"username": "usuario_eva3", "password": password},
            format="json",
            REMOTE_ADDR=ip,
        )

    def test_bloquea_cuenta_aunque_cambie_la_ip(self):
        for indice in range(3):
            respuesta = self._login("incorrecta", f"10.0.0.{indice}")
            self.assertEqual(respuesta.status_code, 400)

        # Incluso con la contraseña correcta y otra IP, sigue bloqueada.
        respuesta = self._login("ClaveSegura123!", "10.0.0.99")
        self.assertEqual(respuesta.status_code, 429)

    def test_login_exitoso_reinicia_contador(self):
        self._login("incorrecta", "10.0.1.1")
        self._login("incorrecta", "10.0.1.2")
        self.assertEqual(
            self._login("ClaveSegura123!", "10.0.1.3").status_code, 200
        )
        self._login("incorrecta", "10.0.1.4")
        self.assertEqual(
            self._login("ClaveSegura123!", "10.0.1.5").status_code, 200
        )

    def test_mensaje_no_revela_si_usuario_existe(self):
        respuesta = APIClient().post(
            "/api/login/",
            {"username": "no_existe", "password": "x"},
            format="json",
            REMOTE_ADDR="10.0.2.1",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["detail"], "Usuario o contraseña incorrectos."
        )


class RevocacionTokensTests(BaseEva3):

    def test_cambio_de_password_revoca_sesiones(self):
        cliente_usuario = _cliente(self.otro)
        self.assertEqual(cliente_usuario.get("/api/sesion/").status_code, 200)

        respuesta = _cliente(self.administrador).patch(
            f"/api/administracion/usuarios/{self.otro.id}/",
            {
                "password": "NuevaClaveSegura456!",
                "password_confirm": "NuevaClaveSegura456!",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(cliente_usuario.get("/api/sesion/").status_code, 401)

    def test_cambio_de_rol_revoca_sesiones(self):
        cliente_encargado = _cliente(self.encargado)
        respuesta = _cliente(self.administrador).patch(
            f"/api/administracion/usuarios/{self.encargado.id}/",
            {"rol": PerfilUsuario.Rol.USUARIO},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            cliente_encargado.get("/api/administracion/resumen/").status_code,
            401,
        )

    def test_usuario_desactivado_no_accede(self):
        cliente = _cliente(self.otro)
        self.otro.is_active = False
        self.otro.save(update_fields=["is_active"])
        self.assertEqual(cliente.get("/api/sesion/").status_code, 401)
        self.otro.is_active = True
        self.otro.save(update_fields=["is_active"])


class EscaladaPrivilegiosTests(BaseEva3):

    def test_usuario_no_puede_modificarse_a_si_mismo(self):
        respuesta = _cliente(self.usuario).patch(
            f"/api/administracion/usuarios/{self.usuario.id}/",
            {"rol": PerfilUsuario.Rol.ADMINISTRADOR},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 403)
        self.usuario.perfil_cintac.refresh_from_db()
        self.assertEqual(
            self.usuario.perfil_cintac.rol, PerfilUsuario.Rol.USUARIO
        )

    def test_encargado_no_gestiona_usuarios(self):
        respuesta = _cliente(self.encargado).patch(
            f"/api/administracion/usuarios/{self.encargado.id}/",
            {"rol": PerfilUsuario.Rol.ADMINISTRADOR},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_campos_no_permitidos_rechazados(self):
        respuesta = _cliente(self.administrador).patch(
            f"/api/administracion/usuarios/{self.otro.id}/",
            {"is_superuser": True, "is_staff": True},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.otro.refresh_from_db()
        self.assertFalse(self.otro.is_superuser)
        self.assertFalse(self.otro.is_staff)


class MatrizPermisosTests(BaseEva3):
    """Cada rol accede solo a lo que le corresponde (respuesta HTTP)."""

    ESPERADO = {
        # endpoint: (USUARIO, ENCARGADO, ADMINISTRADOR, anónimo)
        ("get", "/api/rutas/"): (200, 200, 200, 401),
        ("get", "/api/historial/"): (200, 200, 200, 401),
        ("get", "/api/historial/exportar/"): (200, 200, 200, 401),
        ("get", "/api/administracion/resumen/"): (403, 200, 200, 401),
        ("get", "/api/administracion/operaciones/"): (403, 200, 200, 401),
        ("get", "/api/administracion/usuarios/"): (403, 403, 200, 401),
        ("post", "/api/administracion/operaciones/999/restaurar/"): (
            403, 403, 404, 401
        ),
    }

    def test_matriz(self):
        clientes = (
            _cliente(self.usuario),
            _cliente(self.encargado),
            _cliente(self.administrador),
            APIClient(),
        )

        for (metodo, url), esperados in self.ESPERADO.items():
            for cliente, esperado in zip(clientes, esperados):
                with self.subTest(url=url, esperado=esperado):
                    datos = {"confirmar": True} if metodo == "post" else None
                    respuesta = getattr(cliente, metodo)(
                        url, datos, format="json"
                    )
                    self.assertEqual(respuesta.status_code, esperado)


class CabecerasSeguridadTests(BaseEva3):

    def test_cabeceras_en_api(self):
        respuesta = _cliente(self.usuario).get("/api/rutas/")
        self.assertIn("Content-Security-Policy", respuesta.headers)
        self.assertIn(
            "frame-ancestors 'none'",
            respuesta.headers["Content-Security-Policy"],
        )
        self.assertEqual(respuesta.headers["X-Frame-Options"], "DENY")
        self.assertEqual(
            respuesta.headers["X-Content-Type-Options"], "nosniff"
        )
        self.assertEqual(
            respuesta.headers["Referrer-Policy"],
            "strict-origin-when-cross-origin",
        )

    def test_cors_no_autoriza_origen_desconocido(self):
        respuesta = APIClient().options(
            "/api/login/",
            HTTP_ORIGIN="https://sitio-malicioso.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", respuesta.headers)


class ErroresControladosTests(BaseEva3):

    @patch("cotizador.views.obtener_opciones")
    def test_error_inesperado_responde_json_generico(self, mock_opciones):
        mock_opciones.side_effect = RuntimeError("detalle interno secreto")
        cliente = _cliente(self.usuario)
        cliente.raise_request_exception = False

        with self.assertLogs("cotizador.api", level="ERROR"):
            respuesta = cliente.post(
                "/api/opciones-contenedores/",
                {"ruta_id": self.ruta.id, "peso_carga": 10, "unidad_peso": "tn"},
                format="json",
            )

        self.assertEqual(respuesta.status_code, 500)
        self.assertNotIn("secreto", respuesta.content.decode())
        self.assertIn("detail", respuesta.json())


# ----------------------------------------------------------------------
# Historial: paginación y exportación CSV
# ----------------------------------------------------------------------


class HistorialPaginacionTests(BaseEva3):

    def test_paginacion_opcional(self):
        for indice in range(5):
            self.crear_cotizacion(self.usuario, origen=f"P{indice}")

        cliente = _cliente(self.usuario)
        pagina1 = cliente.get("/api/historial/?por_pagina=2&pagina=1").data
        pagina3 = cliente.get("/api/historial/?por_pagina=2&pagina=3").data

        self.assertEqual(pagina1["total"], 5)
        self.assertEqual(pagina1["totalPaginas"], 3)
        self.assertEqual(len(pagina1["cotizaciones"]), 2)
        self.assertEqual(len(pagina3["cotizaciones"]), 1)

    def test_sin_parametros_mantiene_limite_500(self):
        respuesta = _cliente(self.usuario).get("/api/historial/")
        self.assertEqual(respuesta.data["limite"], 500)
        self.assertEqual(respuesta.data["pagina"], 1)

    def test_paginacion_invalida(self):
        respuesta = _cliente(self.usuario).get("/api/historial/?pagina=abc")
        self.assertEqual(respuesta.status_code, 400)


class ExportacionCsvTests(BaseEva3):

    def _leer(self, respuesta):
        texto = respuesta.content.decode("utf-8")
        self.assertTrue(texto.startswith("﻿"))
        return list(csv.reader(io.StringIO(texto[1:]), delimiter=";"))

    def test_usuario_exporta_solo_lo_propio(self):
        self.crear_cotizacion(self.usuario, origen="Propio")
        self.crear_cotizacion(self.otro, origen="Ajeno")

        respuesta = _cliente(self.usuario).get("/api/historial/exportar/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("attachment;", respuesta["Content-Disposition"])
        filas = self._leer(respuesta)

        self.assertEqual(len(filas), 2)
        self.assertIn("Propio", filas[1])
        self.assertNotIn("Ajeno", "".join(sum(filas, [])))

    def test_usuario_no_puede_filtrar_por_otro(self):
        respuesta = _cliente(self.usuario).get(
            f"/api/historial/exportar/?usuario_id={self.otro.id}"
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_encargado_exporta_todo_y_respeta_filtros(self):
        self.crear_cotizacion(self.usuario, origen="Ningbo")
        self.crear_cotizacion(self.otro, origen="Qingdao")
        cliente = _cliente(self.encargado)

        todas = self._leer(cliente.get("/api/historial/exportar/"))
        filtradas = self._leer(
            cliente.get("/api/historial/exportar/?origen=ning")
        )

        self.assertEqual(len(todas), 3)
        self.assertEqual(len(filtradas), 2)
        self.assertIn("Ningbo", filtradas[1])

    def test_no_exporta_datos_sensibles(self):
        self.usuario.email = "privado@cintac.cl"
        self.usuario.save(update_fields=["email"])
        self.crear_cotizacion(self.usuario)
        contenido = _cliente(self.usuario).get(
            "/api/historial/exportar/"
        ).content.decode()
        self.assertNotIn("privado@cintac.cl", contenido)
        self.assertNotIn("Token", contenido)

    def test_neutraliza_formulas(self):
        self.crear_cotizacion(self.usuario, origen="=HYPERLINK(\"x\")")
        filas = self._leer(
            _cliente(self.usuario).get("/api/historial/exportar/")
        )
        self.assertEqual(filas[1][3], "'=HYPERLINK(\"x\")")

    def test_celda_segura(self):
        self.assertEqual(celda_csv_segura("=1+1"), "'=1+1")
        self.assertEqual(celda_csv_segura("+56"), "'+56")
        self.assertEqual(celda_csv_segura("-2"), "'-2")
        self.assertEqual(celda_csv_segura("@SUM"), "'@SUM")
        self.assertEqual(celda_csv_segura("\tx"), "'\tx")
        self.assertEqual(celda_csv_segura("Shanghai"), "Shanghai")
        self.assertEqual(celda_csv_segura(Decimal("10.50")), "10.50")
        self.assertEqual(celda_csv_segura(None), "")

    def test_filtro_invalido(self):
        respuesta = _cliente(self.usuario).get(
            "/api/historial/exportar/?contenedor=99"
        )
        self.assertEqual(respuesta.status_code, 400)


# ----------------------------------------------------------------------
# Excel: vista previa, bitácora y restauración
# ----------------------------------------------------------------------


class ExcelMixin:

    def setUp(self):
        super().setUp()
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

    def crear_excel(self, filas):
        ruta = Path(self.temporal.name) / "tarifas.xlsx"
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Tarifas Referencia"
        hoja.append(COLUMNAS_ESPERADAS)
        for fila in filas:
            hoja.append(fila)
        libro.save(ruta)
        return ruta

    def fila(self, origen="Shanghai", destino="Valparaiso", t20=1650):
        return [
            f"{origen}|{destino}",
            origen,
            "China",
            destino,
            "Directo / Transbordo",
            t20,
            2850,
            2350,
            3850,
            26,
            34,
            "Fuente",
        ]

    def subir(self, cliente, url, ruta, **extra):
        with open(ruta, "rb") as archivo:
            return cliente.post(
                url, {"archivo": archivo, **extra}, format="multipart"
            )


class ImportacionTrazableTests(ExcelMixin, BaseEva3):

    def test_vista_previa_compara_actual_y_propuesto(self):
        ruta = self.crear_excel(
            [self.fila(t20=1700), self.fila(destino="San Antonio")]
        )
        respuesta = self.subir(
            _cliente(self.encargado),
            "/api/administracion/validar-excel/",
            ruta,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["resumenCambios"],
            {"nuevas": 1, "modificadas": 1, "sinCambios": 0, "conservadas": 0},
        )
        modificada = next(
            item for item in respuesta.data["comparacion"]
            if item["estado"] == "modificada"
        )
        self.assertEqual(
            modificada["cambios"],
            [{"campo": "tarifa20Min", "actual": "1650.00", "propuesto": "1700.00"}],
        )
        self.assertEqual(len(respuesta.data["archivoSha256"]), 64)
        # La vista previa no modifica nada.
        self.assertEqual(Ruta.objects.count(), 1)

    def test_importacion_registra_operacion_con_respaldo(self):
        ruta = self.crear_excel([self.fila(t20=1700)])
        respuesta = self.subir(
            _cliente(self.encargado),
            "/api/administracion/importar-excel/",
            ruta,
        )
        self.assertEqual(respuesta.status_code, 200)

        operacion = OperacionDatosMaestros.objects.get(
            pk=respuesta.data["operacionId"]
        )
        self.assertEqual(operacion.usuario, self.encargado)
        self.assertEqual(operacion.archivo_nombre, "tarifas.xlsx")
        self.assertEqual(len(operacion.archivo_sha256), 64)
        previa = operacion.estado_previo["rutas"][0]["tarifas"][0]
        self.assertEqual(previa["valor_minimo"], "1650.00")

    def test_hash_distinto_al_validado_se_rechaza(self):
        ruta = self.crear_excel([self.fila(t20=1700)])
        respuesta = self.subir(
            _cliente(self.encargado),
            "/api/administracion/importar-excel/",
            ruta,
            archivo_sha256="0" * 64,
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(
            Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="20").valor_minimo,
            Decimal("1650.00"),
        )
        self.assertFalse(OperacionDatosMaestros.objects.exists())

    @patch("cotizador.gestion_views.aplicar_importacion")
    def test_falla_interna_revierte_y_queda_registrada(self, mock_aplicar):
        def _falla(filas):
            Tarifa.objects.filter(ruta=self.ruta).update(
                valor_minimo=Decimal("1.00")
            )
            raise RuntimeError("falla simulada")

        mock_aplicar.side_effect = _falla
        ruta = self.crear_excel([self.fila(t20=1700)])

        respuesta = self.subir(
            _cliente(self.encargado),
            "/api/administracion/importar-excel/",
            ruta,
        )

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(
            Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="20").valor_minimo,
            Decimal("1650.00"),
        )
        fallida = OperacionDatosMaestros.objects.get()
        self.assertEqual(fallida.estado, "FALLIDA")
        self.assertIsNone(fallida.estado_previo)

    def test_restauracion_completa_y_reversible(self):
        historica = self.crear_cotizacion(self.usuario)

        ruta = self.crear_excel(
            [self.fila(t20=1999), self.fila(destino="San Antonio")]
        )
        importacion = self.subir(
            _cliente(self.encargado),
            "/api/administracion/importar-excel/",
            ruta,
        ).data
        self.assertEqual(Ruta.objects.count(), 2)

        admin = _cliente(self.administrador)

        sin_confirmar = admin.post(
            f"/api/administracion/operaciones/{importacion['operacionId']}/restaurar/",
            {},
            format="json",
        )
        self.assertEqual(sin_confirmar.status_code, 400)

        restaurada = admin.post(
            f"/api/administracion/operaciones/{importacion['operacionId']}/restaurar/",
            {"confirmar": True},
            format="json",
        )
        self.assertEqual(restaurada.status_code, 200)
        self.assertEqual(Ruta.objects.count(), 1)
        self.assertEqual(
            Tarifa.objects.get(ruta__puerto_destino__nombre="Valparaiso",
                               tipo_contenedor="20").valor_minimo,
            Decimal("1650.00"),
        )
        self.assertTrue(Cotizacion.objects.filter(pk=historica.pk).exists())

        # La restauración también es reversible.
        deshacer = admin.post(
            f"/api/administracion/operaciones/{restaurada.data['operacionId']}/restaurar/",
            {"confirmar": True},
            format="json",
        )
        self.assertEqual(deshacer.status_code, 200)
        self.assertEqual(Ruta.objects.count(), 2)

        listado = _cliente(self.encargado).get(
            "/api/administracion/operaciones/"
        ).data
        self.assertEqual(len(listado["operaciones"]), 3)
        self.assertFalse(listado["puedeRestaurar"])
        self.assertNotIn("estado_previo", listado["operaciones"][0])

    def test_encargado_no_puede_restaurar(self):
        ruta = self.crear_excel([self.fila(t20=1700)])
        operacion = self.subir(
            _cliente(self.encargado),
            "/api/administracion/importar-excel/",
            ruta,
        ).data["operacionId"]
        respuesta = _cliente(self.encargado).post(
            f"/api/administracion/operaciones/{operacion}/restaurar/",
            {"confirmar": True},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 403)


class InstantaneaServicioTests(BaseEva3):

    def test_instantanea_ida_y_vuelta(self):
        estado = capturar_estado()
        Tarifa.objects.update(valor_minimo=Decimal("1.00"))
        TipoContenedor.objects.filter(codigo="20").update(
            capacidad_tn=Decimal("10")
        )
        restaurar_estado(estado)
        self.assertEqual(capturar_estado(), estado)

    def test_instantanea_invalida_no_modifica(self):
        for invalida in (None, {}, {"version": 99}, {
            "version": 1, "rutas": [], "puertos": [], "tiposContenedor": []
        }):
            with self.subTest(invalida=invalida):
                with self.assertRaises(InstantaneaInvalida):
                    restaurar_estado(invalida)
        self.assertEqual(Ruta.objects.count(), 1)

    def test_contenedor_ausente_se_desactiva_no_se_borra(self):
        estado = capturar_estado()
        TipoContenedor.objects.create(
            codigo="45", nombre="HC", capacidad_tn=Decimal("26")
        )
        restaurar_estado(estado)
        self.assertFalse(TipoContenedor.objects.get(codigo="45").activo)


class FechaHistorialTests(BaseEva3):

    def test_exportacion_usa_hora_local(self):
        self.crear_cotizacion(self.usuario)
        texto = _cliente(self.usuario).get(
            "/api/historial/exportar/"
        ).content.decode()
        self.assertIn(timezone.localdate().isoformat(), texto)


class ComandoImportarExcelTests(ExcelMixin, BaseEva3):

    def test_sin_aplicar_solo_valida(self):
        ruta = self.crear_excel([self.fila(t20=1777)])
        salida = io.StringIO()
        call_command("importar_excel", str(ruta), stdout=salida)
        self.assertEqual(
            Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="20").valor_minimo,
            Decimal("1650.00"),
        )
        self.assertFalse(OperacionDatosMaestros.objects.exists())

    def test_aplicar_registra_bitacora(self):
        ruta = self.crear_excel([self.fila(t20=1777)])
        call_command(
            "importar_excel", str(ruta), "--aplicar", stdout=io.StringIO()
        )
        self.assertEqual(
            Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="20").valor_minimo,
            Decimal("1777.00"),
        )
        operacion = OperacionDatosMaestros.objects.get()
        self.assertEqual(operacion.usuario_username, "consola")
        self.assertIsNotNone(operacion.estado_previo)

    def test_archivo_invalido_falla_controlado(self):
        with self.assertRaises(CommandError):
            call_command(
                "importar_excel",
                str(Path(self.temporal.name) / "no_existe.xlsx"),
                stdout=io.StringIO(),
            )

