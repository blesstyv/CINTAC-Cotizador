from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from cotizador.services.importador_datos import (
    ErrorImportacionExcel,
    aplicar_importacion,
    crear_respaldo_sqlite,
    validar_archivo_excel,
)


class Command(BaseCommand):
    help = (
        "Valida e importa la hoja "
        "'Tarifas Referencia' del "
        "archivo Excel de CINTAC."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "archivo",
            type=str,
            help=(
                "Ruta del archivo .xlsx "
                "que se desea validar."
            ),
        )

        parser.add_argument(
            "--aplicar",
            action="store_true",
            help=(
                "Aplica los datos a SQLite "
                "después de superar todas "
                "las validaciones."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        ruta_archivo = Path(
            options["archivo"]
        ).expanduser()

        self.stdout.write("")
        self.stdout.write(
            "Validando archivo:"
        )

        self.stdout.write(
            f"  {ruta_archivo}"
        )

        self.stdout.write("")

        try:
            filas = validar_archivo_excel(
                ruta_archivo
            )

        except ErrorImportacionExcel as error:
            self.stdout.write(
                self.style.ERROR(
                    "VALIDACIÓN RECHAZADA"
                )
            )

            self.stdout.write("")

            self.stdout.write(
                (
                    "No se realizó ninguna "
                    "modificación en la "
                    "base de datos."
                )
            )

            self.stdout.write("")

            self.stdout.write(
                (
                    f"Se encontraron "
                    f"{len(error.errores)} "
                    "problema(s):"
                )
            )

            self.stdout.write("")

            for problema in error.errores:
                self.stdout.write(
                    self.style.ERROR(
                        f"  - {problema}"
                    )
                )

            raise CommandError(
                (
                    "El archivo debe ser "
                    "corregido antes de "
                    "importarlo."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "VALIDACIÓN CORRECTA"
            )
        )

        self.stdout.write("")

        self.stdout.write(
            (
                f"Filas válidas: "
                f"{len(filas)}"
            )
        )

        if not options[
            "aplicar"
        ]:
            self.stdout.write("")

            self.stdout.write(
                self.style.WARNING(
                    (
                        "Modo de validación: "
                        "la base de datos NO "
                        "fue modificada."
                    )
                )
            )

            self.stdout.write("")

            self.stdout.write(
                (
                    "Para aplicar el archivo, "
                    "ejecute nuevamente el "
                    "comando agregando "
                    "--aplicar."
                )
            )

            return

        self.stdout.write("")
        self.stdout.write(
            "Creando respaldo de SQLite..."
        )

        respaldo = (
            crear_respaldo_sqlite()
        )

        if respaldo:
            self.stdout.write(
                self.style.SUCCESS(
                    (
                        "Respaldo creado en: "
                        f"{respaldo}"
                    )
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    (
                        "La base de datos aún "
                        "no existía; no fue "
                        "necesario crear "
                        "respaldo."
                    )
                )
            )

        self.stdout.write("")
        self.stdout.write(
            "Aplicando datos..."
        )

        resumen = aplicar_importacion(
            filas
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IMPORTACIÓN FINALIZADA"
            )
        )

        self.stdout.write("")

        self.stdout.write(
            (
                "Puertos creados: "
                f"{resumen['puertos_creados']}"
            )
        )

        self.stdout.write(
            (
                "Rutas creadas: "
                f"{resumen['rutas_creadas']}"
            )
        )

        self.stdout.write(
            (
                "Rutas actualizadas: "
                f"{resumen['rutas_actualizadas']}"
            )
        )

        self.stdout.write(
            (
                "Tarifas creadas: "
                f"{resumen['tarifas_creadas']}"
            )
        )

        self.stdout.write(
            (
                "Tarifas actualizadas: "
                f"{resumen['tarifas_actualizadas']}"
            )
        )

        self.stdout.write(
            (
                "Tránsitos creados: "
                f"{resumen['transitos_creados']}"
            )
        )

        self.stdout.write(
            (
                "Tránsitos actualizados: "
                f"{resumen['transitos_actualizados']}"
            )
        )