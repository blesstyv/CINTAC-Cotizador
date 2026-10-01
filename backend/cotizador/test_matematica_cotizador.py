from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from .tests import BaseCotizadorTestCase


class MatematicaOpcionesTests(
    BaseCotizadorTestCase
):
    def test_un_kg_requiere_un_contenedor(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    1,

                "unidad_peso":
                    "kg",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "pesoTN"
                ]
            ),
            Decimal("0.001"),
        )

        for opcion in respuesta.data[
            "opciones"
        ]:
            self.assertEqual(
                opcion["cantidad"],
                1,
            )


    def test_24999_kg_requiere_un_contenedor(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    24999,

                "unidad_peso":
                    "kg",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "pesoTN"
                ]
            ),
            Decimal("24.999"),
        )

        for opcion in respuesta.data[
            "opciones"
        ]:
            self.assertEqual(
                opcion["cantidad"],
                1,
            )


    def test_25001_kg_requiere_dos_contenedores(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    25001,

                "unidad_peso":
                    "kg",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "pesoTN"
                ]
            ),
            Decimal("25.001"),
        )

        for opcion in respuesta.data[
            "opciones"
        ]:
            self.assertEqual(
                opcion["cantidad"],
                2,
            )


    def test_kg_y_tn_generan_misma_cantidad(
        self,
    ):
        respuesta_kg = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    50000,

                "unidad_peso":
                    "kg",
            },
            format="json",
        )

        respuesta_tn = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    50,

                "unidad_peso":
                    "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta_kg.status_code,
            200,
        )

        self.assertEqual(
            respuesta_tn.status_code,
            200,
        )

        self.assertEqual(
            Decimal(
                respuesta_kg.data[
                    "pesoTN"
                ]
            ),
            Decimal("50"),
        )

        self.assertEqual(
            Decimal(
                respuesta_tn.data[
                    "pesoTN"
                ]
            ),
            Decimal("50"),
        )

        opciones_kg = {
            opcion["codigo"]:
                opcion["cantidad"]

            for opcion
            in respuesta_kg.data[
                "opciones"
            ]
        }

        opciones_tn = {
            opcion["codigo"]:
                opcion["cantidad"]

            for opcion
            in respuesta_tn.data[
                "opciones"
            ]
        }

        self.assertEqual(
            opciones_kg,
            opciones_tn,
        )


    def test_totales_opciones_corresponden_a_tarifa_por_cantidad(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    100,

                "unidad_peso":
                    "tn",
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
            cantidad = Decimal(
                opcion["cantidad"]
            )

            tarifa_min = Decimal(
                opcion["tarifaMin"]
            )

            tarifa_max = Decimal(
                opcion["tarifaMax"]
            )

            total_min = Decimal(
                opcion["totalMin"]
            )

            total_max = Decimal(
                opcion["totalMax"]
            )

            self.assertEqual(
                total_min,
                tarifa_min
                * cantidad,
            )

            self.assertEqual(
                total_max,
                tarifa_max
                * cantidad,
            )


    def test_sugerencia_corresponde_a_menor_costo(
        self,
    ):
        respuesta = self.client.post(
            "/api/opciones-contenedores/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    50,

                "unidad_peso":
                    "tn",
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        opciones = (
            respuesta.data[
                "opciones"
            ]
        )

        opcion_menor_costo = min(
            opciones,
            key=lambda opcion: (
                (
                    Decimal(
                        opcion[
                            "totalMin"
                        ]
                    )
                    +
                    Decimal(
                        opcion[
                            "totalMax"
                        ]
                    )
                )
                / Decimal("2")
            ),
        )

        self.assertEqual(
            respuesta.data[
                "sugerida"
            ],
            opcion_menor_costo[
                "codigo"
            ],
        )


class MatematicaCotizacionTests(
    BaseCotizadorTestCase
):
    def configurar_tipo_cambio(
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


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_100_tn_contenedor_20_calcula_totales_correctos(
        self,
        mock_tipo_cambio,
    ):
        self.configurar_tipo_cambio(
            mock_tipo_cambio
        )

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    100,

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
            respuesta.data[
                "cantidad"
            ],
            4,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMin"
                ]
            ),
            Decimal("6600"),
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMax"
                ]
            ),
            Decimal("11400"),
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_100_tn_contenedor_40_calcula_totales_correctos(
        self,
        mock_tipo_cambio,
    ):
        self.configurar_tipo_cambio(
            mock_tipo_cambio
        )

        respuesta = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    100,

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
            respuesta.data[
                "cantidad"
            ],
            4,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMin"
                ]
            ),
            Decimal("9400"),
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMax"
                ]
            ),
            Decimal("15400"),
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_kg_y_tn_generan_misma_cotizacion(
        self,
        mock_tipo_cambio,
    ):
        self.configurar_tipo_cambio(
            mock_tipo_cambio
        )

        respuesta_kg = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    50000,

                "unidad_peso":
                    "kg",

                "tipo_contenedor":
                    "20",

                "contingencia":
                    0,
            },
            format="json",
        )

        respuesta_tn = self.client.post(
            "/api/cotizar/",
            {
                "ruta_id":
                    self.ruta.id,

                "peso_carga":
                    50,

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
            respuesta_kg.status_code,
            200,
        )

        self.assertEqual(
            respuesta_tn.status_code,
            200,
        )

        self.assertEqual(
            respuesta_kg.data[
                "cantidad"
            ],
            respuesta_tn.data[
                "cantidad"
            ],
        )

        self.assertEqual(
            Decimal(
                respuesta_kg.data[
                    "totalMin"
                ]
            ),
            Decimal(
                respuesta_tn.data[
                    "totalMin"
                ]
            ),
        )

        self.assertEqual(
            Decimal(
                respuesta_kg.data[
                    "totalMax"
                ]
            ),
            Decimal(
                respuesta_tn.data[
                    "totalMax"
                ]
            ),
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_contingencia_alta_no_modifica_precio(
        self,
        mock_tipo_cambio,
    ):
        self.configurar_tipo_cambio(
            mock_tipo_cambio
        )

        sin_contingencia = (
            self.client.post(
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
        )

        con_contingencia = (
            self.client.post(
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
                        30,
                },
                format="json",
            )
        )

        self.assertEqual(
            sin_contingencia.status_code,
            200,
        )

        self.assertEqual(
            con_contingencia.status_code,
            200,
        )

        self.assertEqual(
            sin_contingencia.data[
                "totalMin"
            ],
            con_contingencia.data[
                "totalMin"
            ],
        )

        self.assertEqual(
            sin_contingencia.data[
                "totalMax"
            ],
            con_contingencia.data[
                "totalMax"
            ],
        )

        self.assertEqual(
            con_contingencia.data[
                "transitoMin"
            ],
            56,
        )

        self.assertEqual(
            con_contingencia.data[
                "transitoMax"
            ],
            64,
        )


    @patch(
        "cotizador.views.obtener_tipo_cambio"
    )
    def test_conversion_clp_para_dos_contenedores_es_correcta(
        self,
        mock_tipo_cambio,
    ):
        self.configurar_tipo_cambio(
            mock_tipo_cambio
        )

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
            respuesta.data[
                "cantidad"
            ],
            2,
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMin"
                ]
            ),
            Decimal("3300"),
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMax"
                ]
            ),
            Decimal("5700"),
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMinCLP"
                ]
            ),
            Decimal("3202518"),
        )

        self.assertEqual(
            Decimal(
                respuesta.data[
                    "totalMaxCLP"
                ]
            ),
            Decimal("5531622"),
        )