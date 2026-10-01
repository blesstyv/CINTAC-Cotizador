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


class RobustezImportadorTests(
    TestCase
):
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
    ):
        ruta = (
            self.carpeta
            / f"{uuid4().hex}.xlsx"
        )

        libro = Workbook()

        hoja = libro.active

        hoja.title = (
            "Tarifas Referencia"
        )

        hoja.append(
            encabezados
            if encabezados is not None
            else COLUMNAS_ESPERADAS
        )

        if filas:
            for fila in filas:
                hoja.append(
                    fila
                )

        libro.save(
            ruta
        )

        libro.close()

        return ruta


    def test_excel_sin_filas_es_rechazado(
        self,
    ):
        archivo = self.crear_excel(
            filas=[]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_columna_adicional_es_rechazada(
        self,
    ):
        encabezados = (
            COLUMNAS_ESPERADAS
            + ["Columna extra"]
        )

        archivo = self.crear_excel(
            filas=[
                self.fila_valida
                + ["dato"]
            ],
            encabezados=
                encabezados,
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_tipo_ruta_invalido_es_rechazado(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[4] = (
            "Ruta inventada"
        )

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_booleano_en_tarifa_es_rechazado(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = True

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_numero_ambiguo_es_rechazado(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = "1,650.00"

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_formula_en_campo_texto_es_rechazada(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[11] = (
            "=HYPERLINK("
            "\"http://ejemplo.cl\","
            "\"Fuente\")"
        )

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_nan_en_tarifa_es_rechazado(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = "NaN"

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_infinito_en_tarifa_es_rechazado(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = "Infinity"

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_tarifa_con_mas_de_dos_decimales_es_rechazada(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = "1650.123"

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_tarifa_supera_maximo_de_digitos_es_rechazada(
        self,
    ):
        fila = deepcopy(
            self.fila_valida
        )

        fila[5] = (
            "12345678901.00"
        )

        fila[6] = (
            "12345678902.00"
        )

        archivo = self.crear_excel(
            [fila]
        )

        with self.assertRaises(
            ErrorImportacionExcel
        ):
            validar_archivo_excel(
                archivo
            )


    def test_rollback_si_falla_al_final_de_importacion(
        self,
    ):
        archivo = self.crear_excel(
            [self.fila_valida]
        )

        filas = validar_archivo_excel(
            archivo
        )

        with patch(
            (
                "cotizador.services."
                "importador_datos."
                "TiempoTransito.objects."
                "update_or_create"
            ),
            side_effect=RuntimeError(
                "Error simulado tardío"
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


    def test_rollback_conserva_valores_anteriores(
        self,
    ):
        archivo_inicial = (
            self.crear_excel(
                [self.fila_valida]
            )
        )

        filas_iniciales = (
            validar_archivo_excel(
                archivo_inicial
            )
        )

        aplicar_importacion(
            filas_iniciales
        )

        tarifa_original = (
            Tarifa.objects.get(
                tipo_contenedor="20"
            )
        )

        valor_original = (
            tarifa_original
            .valor_minimo
        )

        fila_actualizada = deepcopy(
            self.fila_valida
        )

        fila_actualizada[5] = 1800
        fila_actualizada[6] = 3000

        archivo_actualizado = (
            self.crear_excel(
                [fila_actualizada]
            )
        )

        filas_actualizadas = (
            validar_archivo_excel(
                archivo_actualizado
            )
        )

        with patch(
            (
                "cotizador.services."
                "importador_datos."
                "TiempoTransito.objects."
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
                    filas_actualizadas
                )

        tarifa_original.refresh_from_db()

        self.assertEqual(
            tarifa_original.valor_minimo,
            valor_original,
        )

        self.assertEqual(
            tarifa_original.valor_minimo,
            1650,
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