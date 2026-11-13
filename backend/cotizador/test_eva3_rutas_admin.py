"""
Pruebas de la gestión manual de rutas, puertos y tarifas
(requerimiento: agregar puertos del cliente y actualización manual
de tarifas por el administrador).
"""

from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from .models import (
    Cotizacion,
    OperacionDatosMaestros,
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
)
from .test_eva3_seguridad_datos import BaseEva3, _cliente


URL = "/api/administracion/rutas/"


def _nueva(**extra):
    datos = {
        "origen": "Singapur",
        "pais_origen": "Singapur",
        "destino": "San Antonio",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": "1800",
        "tarifa20_max": "3000.50",
        "tarifa40_min": "2500",
        "tarifa40_max": "4000",
        "transito_min": 30,
        "transito_max": 40,
    }
    datos.update(extra)
    return datos


class RutasAdminPermisosTests(BaseEva3):

    def test_matriz_de_permisos(self):
        casos = (
            (_cliente(self.usuario), 403),
            (_cliente(self.encargado), 200),
            (_cliente(self.administrador), 200),
        )
        for cliente, esperado in casos:
            with self.subTest(esperado=esperado):
                self.assertEqual(cliente.get(URL).status_code, esperado)

    def test_usuario_no_puede_crear_ni_editar(self):
        cliente = _cliente(self.usuario)
        self.assertEqual(
            cliente.post(URL, _nueva(), format="json").status_code, 403
        )
        self.assertEqual(
            cliente.patch(
                f"{URL}{self.ruta.id}/",
                {"tarifa20_min": "1"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(Ruta.objects.count(), 1)

    def test_anonimo_rechazado(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get(URL).status_code, 401)


class CrearRutaTests(BaseEva3):

    def test_listado_incluye_tarifas_y_transito(self):
        datos = _cliente(self.encargado).get(URL).data
        self.assertEqual(len(datos["rutas"]), 1)
        ruta = datos["rutas"][0]
        self.assertEqual(ruta["tarifa20Min"], "1650.00")
        self.assertEqual(ruta["tarifa40Max"], "3850.00")
        self.assertEqual(ruta["transitoMin"], 26)
        self.assertNotIn("fuente", ruta)
        self.assertIn("Transbordo", datos["tiposRuta"])

    def test_crea_ruta_con_puerto_nuevo_y_reutiliza_destino(self):
        Puerto.objects.create(nombre="San Antonio", pais="Chile")
        respuesta = _cliente(self.encargado).post(
            URL, _nueva(destino="san antonio"), format="json"
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(
            Puerto.objects.filter(nombre__iexact="San Antonio").count(), 1
        )
        ruta = Ruta.objects.get(puerto_origen__nombre="Singapur")
        self.assertEqual(ruta.puerto_destino.pais, "Chile")
        self.assertEqual(ruta.tarifas.count(), 2)
        self.assertEqual(
            ruta.tarifas.get(tipo_contenedor="20").valor_maximo,
            Decimal("3000.50"),
        )
        self.assertEqual(ruta.tiempo_transito.dias_maximos, 40)

        operacion = OperacionDatosMaestros.objects.get(
            pk=respuesta.data["operacionId"]
        )
        self.assertEqual(operacion.tipo, "EDICION_MANUAL")
        self.assertEqual(operacion.usuario, self.encargado)
        self.assertEqual(len(operacion.estado_previo["rutas"]), 1)

    @patch("cotizador.views.obtener_tipo_cambio")
    def test_ruta_nueva_se_puede_cotizar(self, mock_tc):
        mock_tc.return_value = {
            "valor": Decimal("950.00"),
            "fecha": timezone.localdate(),
            "fuente": "Prueba",
            "modo": "en_linea",
        }
        creada = _cliente(self.administrador).post(
            URL, _nueva(), format="json"
        ).data["ruta"]

        cliente = _cliente(self.usuario)
        rutas = cliente.get("/api/rutas/").data
        self.assertIn("Singapur", [r["origen"] for r in rutas])

        cotizacion = cliente.post(
            "/api/cotizar/",
            {
                "ruta_id": creada["id"],
                "peso_carga": 46,
                "unidad_peso": "tn",
                "tipo_contenedor": "20",
            },
            format="json",
        )
        self.assertEqual(cotizacion.status_code, 200)
        self.assertEqual(cotizacion.data["cantidad"], 2)
        self.assertEqual(cotizacion.data["totalMin"], "3600.00")
        self.assertEqual(cotizacion.data["transitoMax"], 40)

    def test_ruta_duplicada_no_crea_nada(self):
        respuesta = _cliente(self.encargado).post(
            URL,
            _nueva(origen="shanghai", pais_origen="china",
                   destino="Valparaiso"),
            format="json",
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(Ruta.objects.count(), 1)
        self.assertEqual(Puerto.objects.count(), 2)
        self.assertFalse(OperacionDatosMaestros.objects.exists())

    @patch("cotizador.rutas_admin_views.Ruta.objects.create")
    def test_creacion_simultanea_responde_conflicto(self, mock_create):
        from django.db import IntegrityError
        mock_create.side_effect = IntegrityError("duplicada")
        respuesta = _cliente(self.encargado).post(
            URL, _nueva(), format="json"
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertFalse(Puerto.objects.filter(nombre="Singapur").exists())
        self.assertFalse(OperacionDatosMaestros.objects.exists())

    def test_validaciones(self):
        invalidos = {
            "tarifa negativa": {"tarifa20_min": "-5"},
            "tarifa cero": {"tarifa40_min": "0"},
            "tarifa texto": {"tarifa20_max": "abc"},
            "tres decimales": {"tarifa20_min": "10.123"},
            "max menor que min": {"tarifa20_min": "3001", "tarifa20_max": "3000"},
            "transito invertido": {"transito_min": 50, "transito_max": 40},
            "transito cero": {"transito_min": 0},
            "transito decimal": {"transito_min": "3.5"},
            "tipo invalido": {"tipo_ruta": "Aéreo"},
            "origen vacio": {"origen": "   "},
            "formula": {"origen": "=CMD()"},
            "mismo puerto": {"origen": "San Antonio", "pais_origen": "Chile"},
            "campo extra": {"is_superuser": True},
            "nombre largo": {"origen": "x" * 101},
        }
        cliente = _cliente(self.encargado)
        for nombre, cambio in invalidos.items():
            with self.subTest(caso=nombre):
                respuesta = cliente.post(URL, _nueva(**cambio), format="json")
                self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Ruta.objects.count(), 1)
        self.assertEqual(Puerto.objects.count(), 2)

    def test_campos_obligatorios(self):
        respuesta = _cliente(self.encargado).post(URL, {}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        for campo in ("origen", "pais_origen", "destino", "tipo_ruta",
                      "tarifa20_min", "tarifa40_max", "transito_min"):
            self.assertIn(campo, respuesta.data)


class ActualizarRutaTests(BaseEva3):

    def url(self):
        return f"{URL}{self.ruta.id}/"

    def test_actualiza_tarifa_y_registra_cambio(self):
        respuesta = _cliente(self.encargado).patch(
            self.url(),
            {"tarifa20_min": "1700", "transito_max": 36},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        tarifa = Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="20")
        self.assertEqual(tarifa.valor_minimo, Decimal("1700.00"))
        self.assertEqual(tarifa.valor_maximo, Decimal("2850.00"))
        self.assertEqual(
            TiempoTransito.objects.get(ruta=self.ruta).dias_maximos, 36
        )
        # La tarifa de 40' no se tocó.
        self.assertEqual(
            Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="40").fuente,
            "Fuente",
        )
        operacion = OperacionDatosMaestros.objects.get()
        self.assertEqual(
            operacion.resumen["cambios"]["tarifa20Min"],
            {"antes": "1650.00", "despues": "1700.00"},
        )

    def test_minimo_sobre_maximo_actual_rechazado(self):
        respuesta = _cliente(self.encargado).patch(
            self.url(), {"tarifa20_min": "9999"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="20").valor_minimo,
            Decimal("1650.00"),
        )

    def test_sin_cambios_no_registra_operacion(self):
        respuesta = _cliente(self.encargado).patch(
            self.url(), {"tarifa20_min": "1650.00"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(OperacionDatosMaestros.objects.exists())

    def test_cuerpo_vacio_y_ruta_inexistente(self):
        cliente = _cliente(self.encargado)
        self.assertEqual(
            cliente.patch(self.url(), {}, format="json").status_code, 400
        )
        self.assertEqual(
            cliente.patch(
                f"{URL}999999/", {"tarifa20_min": "1"}, format="json"
            ).status_code,
            404,
        )

    def test_no_permite_cambiar_puertos(self):
        respuesta = _cliente(self.encargado).patch(
            self.url(), {"origen": "Otro"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_historial_no_cambia_y_admin_puede_restaurar(self):
        historica = self.crear_cotizacion(self.usuario)
        operacion = _cliente(self.encargado).patch(
            self.url(), {"tarifa20_min": "1000"}, format="json"
        ).data["operacionId"]

        historica.refresh_from_db()
        self.assertEqual(historica.tarifa_min, Decimal("1650.00"))

        restaurar = _cliente(self.administrador).post(
            f"/api/administracion/operaciones/{operacion}/restaurar/",
            {"confirmar": True},
            format="json",
        )
        self.assertEqual(restaurar.status_code, 200)
        self.assertEqual(
            Tarifa.objects.get(ruta=self.ruta, tipo_contenedor="20").valor_minimo,
            Decimal("1650.00"),
        )
        self.assertTrue(Cotizacion.objects.filter(pk=historica.pk).exists())

    def test_restaurar_creacion_elimina_ruta_y_puerto_nuevos(self):
        operacion = _cliente(self.encargado).post(
            URL, _nueva(), format="json"
        ).data["operacionId"]
        self.assertEqual(Ruta.objects.count(), 2)

        _cliente(self.administrador).post(
            f"/api/administracion/operaciones/{operacion}/restaurar/",
            {"confirmar": True},
            format="json",
        )
        self.assertEqual(Ruta.objects.count(), 1)
        self.assertFalse(Puerto.objects.filter(nombre="Singapur").exists())
