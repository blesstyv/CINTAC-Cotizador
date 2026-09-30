import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase

from openpyxl import Workbook

from cotizador.models import (
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)

from cotizador.services.importador_datos import (
    COLUMNAS_ESPERADAS,
    ErrorImportacionExcel,
    aplicar_importacion,
    validar_archivo_excel,
)


class ImportadorExcelTests(TestCase):
    def setUp(self):
        self.temporal = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temporal.cleanup
        )

        self.carpeta = Path(
            self.temporal.name
        )

        self.fila_valida = [
            "Shanghai|Valparaiso",
            "Shanghai",
            "China",
            "Valparaiso",
            "Directo / Transbordo",
            1650,
            2850,
            2350,
            3850,
            26,
            34,
            "Segucargo / Delpa Group 2026",
        ]

    def crear_excel(
        self,
        filas=None,
        encabezados=None,
        nombre_hoja="Tarifas Referencia",
    ):
        archivo = (
            self.carpeta
            / f"{uuid4().hex}.xlsx"
        )

        libro = Workbook()

        hoja = libro.active
        hoja.title = nombre_hoja

        hoja.append(
            encabezados
            if encabezados is not None
            else COLUMNAS_ESPERADAS
        )

        for fila in (
            filas
            if filas is not None
            else [self.fila_valida]
        ):
            hoja.append(fila)

        libro.save(archivo)
        libro.close()

        return archivo

    def test_archivo_valido_supera_validacion(
        self
    ):
        archivo = self.crear_excel()

        filas = validar_archivo_excel(
            archivo
        )

        self.assertEqual(
            len(filas),
            1,
        )

        self.assertEqual(
            filas[0].origen,
            "Shanghai",
        )

        self.assertEqual(
            filas[0].destino,
            "Valparaiso",
        )

    def test_rechaza_hoja_incorrecta(
        self
    ):
        archivo = self.crear_excel(
            nombre_hoja="Otra Hoja"
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )

    def test_rechaza_columna_faltante(
        self
    ):
        encabezados = (
            COLUMNAS_ESPERADAS[:-1]
        )

        archivo = self.crear_excel(
            encabezados=encabezados
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )

    def test_rechaza_tarifa_cero(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = 0

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                "mayor que cero"
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_rechaza_tarifa_negativa(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = -100

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )

    def test_rechaza_tarifa_maxima_menor(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = 3000
        fila[6] = 2000

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                (
                    "tarifa máxima de "
                    "20'"
                )
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_rechaza_transito_decimal(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[9] = 26.5

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                "número entero"
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_rechaza_transito_maximo_menor(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[9] = 40
        fila[10] = 20

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                "tránsito máximo"
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_rechaza_clave_incorrecta(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[0] = (
            "Singapur|Valparaiso"
        )

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                "no coincide"
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_rechaza_ruta_duplicada(
        self
    ):
        fila_1 = deepcopy(
            self.fila_valida
        )

        fila_2 = deepcopy(
            self.fila_valida
        )

        archivo = self.crear_excel(
            [
                fila_1,
                fila_2,
            ]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                "duplicada"
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_rechaza_pais_inconsistente(
        self
    ):
        fila_1 = deepcopy(
            self.fila_valida
        )

        fila_2 = [
            "Shanghai|San Antonio",
            "Shanghai",
            "Singapur",
            "San Antonio",
            "Directo / Transbordo",
            1600,
            2800,
            2300,
            3800,
            25,
            32,
            "Fuente prueba",
        ]

        archivo = self.crear_excel(
            [
                fila_1,
                fila_2,
            ]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                "anteriormente fue asociado"
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_rechaza_formula_en_tarifa(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = "=1000+650"

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ) as contexto:
            validar_archivo_excel(
                archivo
            )

        self.assertTrue(
            any(
                "fórmula"
                in error
                for error
                in contexto.exception.errores
            )
        )

    def test_archivo_invalido_no_modifica_bd(
        self
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = -1

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )

        self.assertEqual(
            Puerto.objects.count(),
            0,
        )

        self.assertEqual(
            Ruta.objects.count(),
            0,
        )

        self.assertEqual(
            Tarifa.objects.count(),
            0,
        )

        self.assertEqual(
            TiempoTransito.objects.count(),
            0,
        )

    def test_importacion_valida_crea_registros(
        self
    ):
        archivo = self.crear_excel()

        filas = validar_archivo_excel(
            archivo
        )

        resumen = aplicar_importacion(
            filas
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

        self.assertEqual(
            TipoContenedor.objects.count(),
            2,
        )

        self.assertEqual(
            resumen[
                "puertos_creados"
            ],
            2,
        )

        self.assertEqual(
            resumen[
                "rutas_creadas"
            ],
            1,
        )

        self.assertEqual(
            resumen[
                "tarifas_creadas"
            ],
            2,
        )

    def test_segunda_importacion_actualiza_sin_duplicar(
        self
    ):
        archivo_1 = self.crear_excel()

        filas_1 = validar_archivo_excel(
            archivo_1
        )

        aplicar_importacion(
            filas_1
        )

        fila_actualizada = deepcopy(
            self.fila_valida
        )

        fila_actualizada[5] = 1700
        fila_actualizada[6] = 2900
        fila_actualizada[11] = (
            "Fuente actualizada"
        )

        archivo_2 = self.crear_excel(
            [fila_actualizada]
        )

        filas_2 = validar_archivo_excel(
            archivo_2
        )

        resumen = aplicar_importacion(
            filas_2
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

        tarifa_20 = (
            Tarifa.objects.get(
                tipo_contenedor="20"
            )
        )

        self.assertEqual(
            tarifa_20.valor_minimo,
            1700,
        )

        self.assertEqual(
            tarifa_20.valor_maximo,
            2900,
        )

        self.assertEqual(
            tarifa_20.fuente,
            "Fuente actualizada",
        )

        self.assertEqual(
            resumen[
                "rutas_actualizadas"
            ],
            1,
        )

        self.assertEqual(
            resumen[
                "tarifas_actualizadas"
            ],
            2,
        )

    def test_importacion_es_atomica(
        self
    ):
        archivo = self.crear_excel()

        filas = validar_archivo_excel(
            archivo
        )

        with patch(
            (
                "cotizador.services."
                "importador_datos."
                "Tarifa.objects."
                "update_or_create"
            ),
            side_effect=RuntimeError(
                "Error simulado"
            ),
        ):
            with self.assertRaises(
                RuntimeError
            ):
                aplicar_importacion(
                    filas
                )

        self.assertEqual(
            Puerto.objects.count(),
            0,
        )

        self.assertEqual(
            Ruta.objects.count(),
            0,
        )

        self.assertEqual(
            Tarifa.objects.count(),
            0,
        )

        self.assertEqual(
            TiempoTransito.objects.count(),
            0,
        )

        self.assertEqual(
            TipoContenedor.objects.count(),
            0,
        )