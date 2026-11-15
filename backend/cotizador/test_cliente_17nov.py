"""
Aceptación de requisitos del cliente para la exposición del 17-11-2026.

Verifica límites exactos 20'=23 TN y 40'=25 TN, cálculo automático
de cantidad y equivalencia entre kg y TN sin usar servicios externos.
"""
from decimal import Decimal

from .test_eva3_seguridad_datos import BaseEva3, _cliente


class CapacidadesCliente17NovTests(BaseEva3):
    def test_contenedores_calculados_según_peso_y_limites(self):
        casos = (
            ("23", {"20": 1, "40": 1}),
            ("23.001", {"20": 2, "40": 1}),
            ("24", {"20": 2, "40": 1}),
            ("25", {"20": 2, "40": 1}),
            ("26", {"20": 2, "40": 2}),
            ("46", {"20": 2, "40": 2}),
            ("50", {"20": 3, "40": 2}),
        )
        cliente = _cliente(self.usuario)

        for peso, cantidades in casos:
            with self.subTest(peso_tn=peso):
                respuesta = cliente.post(
                    "/api/opciones-contenedores/",
                    {
                        "ruta_id": self.ruta.id,
                        "peso_carga": peso,
                        "unidad_peso": "tn",
                    },
                    format="json",
                )
                self.assertEqual(respuesta.status_code, 200)
                opciones = {
                    opcion["codigo"]: opcion["cantidad"]
                    for opcion in respuesta.data["opciones"]
                }
                self.assertEqual(opciones, cantidades)

    def test_23001_kg_equivale_a_23_001_tn(self):
        respuesta = _cliente(self.usuario).post(
            "/api/opciones-contenedores/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": "23001",
                "unidad_peso": "kg",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Decimal(respuesta.data["pesoTN"]), Decimal("23.001"))
        opciones = {
            opcion["codigo"]: opcion["cantidad"]
            for opcion in respuesta.data["opciones"]
        }
        self.assertEqual(opciones, {"20": 2, "40": 1})

    def test_no_permite_forzar_cantidad_desde_el_cliente(self):
        respuesta = _cliente(self.usuario).post(
            "/api/cotizar/",
            {
                "ruta_id": self.ruta.id,
                "peso_carga": "50",
                "unidad_peso": "tn",
                "tipo_contenedor": "20",
                "cantidad": 1,
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("campos_no_permitidos", respuesta.data)
