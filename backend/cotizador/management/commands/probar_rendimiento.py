import json
import math
import statistics
import time

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from getpass import getpass

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.request import (
    Request,
    urlopen,
)

from django.core.management.base import (
    BaseCommand,
    CommandError,
)


class Command(BaseCommand):
    help = (
        "Ejecuta pruebas de rendimiento "
        "y concurrencia contra la API "
        "del cotizador CINTAC."
    )


    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--base-url",
            default=
                "http://127.0.0.1:8000",

            help=(
                "URL base del backend. "
                "Por defecto: "
                "http://127.0.0.1:8000"
            ),
        )

        parser.add_argument(
            "--usuario",
            required=True,

            help=(
                "Usuario autorizado para "
                "ejecutar las pruebas."
            ),
        )

        parser.add_argument(
            "--niveles",
            nargs="+",
            type=int,
            default=[
                10,
                25,
                50,
            ],

            help=(
                "Niveles de concurrencia. "
                "Por defecto: 10 25 50"
            ),
        )

        parser.add_argument(
            "--factor",
            type=int,
            default=2,

            help=(
                "Cantidad de solicitudes por "
                "nivel = concurrencia x factor. "
                "Por defecto: 2"
            ),
        )

        parser.add_argument(
            "--timeout",
            type=float,
            default=10,

            help=(
                "Timeout por solicitud "
                "en segundos. "
                "Por defecto: 10"
            ),
        )


    def _solicitud(
        self,
        url,
        token=None,
        metodo="GET",
        datos=None,
        timeout=10,
    ):
        headers = {
            "Accept":
                "application/json",
        }

        if token:
            headers[
                "Authorization"
            ] = (
                f"Token {token}"
            )

        contenido = None

        if datos is not None:
            contenido = json.dumps(
                datos
            ).encode(
                "utf-8"
            )

            headers[
                "Content-Type"
            ] = (
                "application/json"
            )

        solicitud = Request(
            url=url,
            data=contenido,
            headers=headers,
            method=metodo,
        )

        inicio = (
            time.perf_counter()
        )

        try:
            with urlopen(
                solicitud,
                timeout=timeout,
            ) as respuesta:
                cuerpo = (
                    respuesta
                    .read()
                    .decode(
                        "utf-8"
                    )
                )

                codigo = (
                    respuesta.status
                )

                datos_respuesta = (
                    json.loads(
                        cuerpo
                    )
                    if cuerpo
                    else None
                )

                error = None

        except HTTPError as exc:
            codigo = exc.code

            try:
                cuerpo = (
                    exc.read()
                    .decode(
                        "utf-8"
                    )
                )

            except Exception:
                cuerpo = ""

            datos_respuesta = None

            error = (
                cuerpo
                or str(exc)
            )

        except (
            URLError,
            TimeoutError,
            OSError,
        ) as exc:
            codigo = None

            datos_respuesta = None

            error = str(
                exc
            )

        except Exception as exc:
            codigo = None

            datos_respuesta = None

            error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

        fin = (
            time.perf_counter()
        )

        duracion = (
            fin - inicio
        )

        return {
            "codigo":
                codigo,

            "duracion":
                duracion,

            "ok":
                (
                    codigo
                    is not None
                    and
                    200
                    <= codigo
                    < 300
                ),

            "datos":
                datos_respuesta,

            "error":
                error,
        }


    def _percentil(
        self,
        valores,
        porcentaje,
    ):
        if not valores:
            return 0

        ordenados = sorted(
            valores
        )

        indice = math.ceil(
            (
                porcentaje
                / 100
            )
            * len(
                ordenados
            )
        ) - 1

        indice = max(
            0,
            min(
                indice,
                len(
                    ordenados
                ) - 1,
            ),
        )

        return ordenados[
            indice
        ]


    def _ejecutar_lote(
        self,
        nombre,
        url,
        token,
        concurrencia,
        total,
        metodo="GET",
        datos=None,
        timeout=10,
    ):
        inicio_lote = (
            time.perf_counter()
        )

        resultados = []

        with ThreadPoolExecutor(
            max_workers=
                concurrencia
        ) as ejecutor:
            trabajos = [
                ejecutor.submit(
                    self._solicitud,
                    url,
                    token,
                    metodo,
                    datos,
                    timeout,
                )

                for _
                in range(
                    total
                )
            ]

            for trabajo in as_completed(
                trabajos
            ):
                resultados.append(
                    trabajo.result()
                )

        duracion_lote = (
            time.perf_counter()
            - inicio_lote
        )

        exitosos = [
            resultado
            for resultado
            in resultados
            if resultado[
                "ok"
            ]
        ]

        fallidos = [
            resultado
            for resultado
            in resultados
            if not resultado[
                "ok"
            ]
        ]

        tiempos_ms = [
            resultado[
                "duracion"
            ] * 1000

            for resultado
            in resultados
        ]

        promedio = (
            statistics.mean(
                tiempos_ms
            )
            if tiempos_ms
            else 0
        )

        mediana = (
            statistics.median(
                tiempos_ms
            )
            if tiempos_ms
            else 0
        )

        p95 = self._percentil(
            tiempos_ms,
            95,
        )

        maximo = (
            max(
                tiempos_ms
            )
            if tiempos_ms
            else 0
        )

        solicitudes_segundo = (
            total
            / duracion_lote
            if duracion_lote > 0
            else 0
        )

        codigos = {}

        for resultado in resultados:
            codigo = (
                resultado[
                    "codigo"
                ]
            )

            clave = (
                str(
                    codigo
                )
                if codigo
                is not None
                else "CONEXION"
            )

            codigos[
                clave
            ] = (
                codigos.get(
                    clave,
                    0,
                )
                + 1
            )


        self.stdout.write("")
        self.stdout.write(
            self.style.HTTP_INFO(
                (
                    f"{nombre} | "
                    f"concurrencia: "
                    f"{concurrencia}"
                )
            )
        )

        self.stdout.write(
            (
                f"  Solicitudes:       "
                f"{total}"
            )
        )

        self.stdout.write(
            (
                f"  Exitosas:          "
                f"{len(exitosos)}"
            )
        )

        self.stdout.write(
            (
                f"  Fallidas:          "
                f"{len(fallidos)}"
            )
        )

        self.stdout.write(
            (
                f"  Promedio:          "
                f"{promedio:.2f} ms"
            )
        )

        self.stdout.write(
            (
                f"  Mediana:           "
                f"{mediana:.2f} ms"
            )
        )

        self.stdout.write(
            (
                f"  P95:               "
                f"{p95:.2f} ms"
            )
        )

        self.stdout.write(
            (
                f"  Máximo:            "
                f"{maximo:.2f} ms"
            )
        )

        self.stdout.write(
            (
                f"  Rendimiento:       "
                f"{solicitudes_segundo:.2f} "
                "solicitudes/s"
            )
        )

        self.stdout.write(
            (
                "  Códigos HTTP:      "
                f"{codigos}"
            )
        )

        if fallidos:
            primer_error = (
                fallidos[0]
            )

            self.stdout.write(
                self.style.ERROR(
                    (
                        "  Primer error:      "
                        f"{primer_error['error']}"
                    )
                )
            )

        return {
            "nombre":
                nombre,

            "concurrencia":
                concurrencia,

            "total":
                total,

            "exitosos":
                len(
                    exitosos
                ),

            "fallidos":
                len(
                    fallidos
                ),

            "promedio_ms":
                promedio,

            "p95_ms":
                p95,

            "maximo_ms":
                maximo,

            "solicitudes_segundo":
                solicitudes_segundo,

            "codigos":
                codigos,
        }


    def handle(
        self,
        *args,
        **options,
    ):
        base_url = (
            options[
                "base_url"
            ].rstrip(
                "/"
            )
        )

        usuario = (
            options[
                "usuario"
            ]
        )

        niveles = (
            options[
                "niveles"
            ]
        )

        factor = (
            options[
                "factor"
            ]
        )

        timeout = (
            options[
                "timeout"
            ]
        )


        if not niveles:
            raise CommandError(
                (
                    "Debe indicar al menos "
                    "un nivel de concurrencia."
                )
            )

        if any(
            nivel <= 0
            for nivel
            in niveles
        ):
            raise CommandError(
                (
                    "Todos los niveles de "
                    "concurrencia deben ser "
                    "mayores que cero."
                )
            )

        if factor <= 0:
            raise CommandError(
                (
                    "El factor debe ser "
                    "mayor que cero."
                )
            )


        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                (
                    "PRUEBA DE RENDIMIENTO "
                    "CINTAC"
                )
            )
        )

        self.stdout.write(
            (
                "Servidor: "
                f"{base_url}"
            )
        )

        self.stdout.write(
            (
                "Usuario: "
                f"{usuario}"
            )
        )

        self.stdout.write(
            (
                "Concurrencias: "
                + ", ".join(
                    str(
                        nivel
                    )
                    for nivel
                    in niveles
                )
            )
        )

        self.stdout.write("")

        password = getpass(
            (
                f"Contraseña de "
                f"{usuario}: "
            )
        )


        respuesta_login = (
            self._solicitud(
                (
                    f"{base_url}"
                    "/api/login/"
                ),
                metodo="POST",
                datos={
                    "username":
                        usuario,

                    "password":
                        password,
                },
                timeout=timeout,
            )
        )

        if (
            not respuesta_login[
                "ok"
            ]
        ):
            raise CommandError(
                (
                    "No fue posible iniciar "
                    "sesión para ejecutar "
                    "las pruebas. "
                    f"HTTP: "
                    f"{respuesta_login['codigo']} "
                    f"{respuesta_login['error']}"
                )
            )

        datos_login = (
            respuesta_login[
                "datos"
            ]
        )

        token = (
            datos_login[
                "token"
            ]
        )


        self.stdout.write(
            self.style.SUCCESS(
                "Autenticación correcta."
            )
        )


        respuesta_rutas = (
            self._solicitud(
                (
                    f"{base_url}"
                    "/api/rutas/"
                ),
                token=token,
                timeout=timeout,
            )
        )

        if (
            not respuesta_rutas[
                "ok"
            ]
        ):
            raise CommandError(
                (
                    "No fue posible cargar "
                    "las rutas para preparar "
                    "las pruebas."
                )
            )

        rutas = (
            respuesta_rutas[
                "datos"
            ]
        )

        ruta = next(
            (
                item
                for item
                in rutas
                if item.get(
                    "tarifas"
                )
            ),
            None,
        )

        if ruta is None:
            raise CommandError(
                (
                    "No existe una ruta "
                    "con tarifas disponibles."
                )
            )

        tarifa = (
            ruta[
                "tarifas"
            ][0]
        )

        ruta_id = (
            ruta[
                "id"
            ]
        )

        tipo_contenedor = (
            tarifa[
                "tipoContenedor"
            ]
        )


        payload_opciones = {
            "ruta_id":
                ruta_id,

            "peso_carga":
                25,

            "unidad_peso":
                "tn",
        }

        payload_cotizar = {
            "ruta_id":
                ruta_id,

            "peso_carga":
                25,

            "unidad_peso":
                "tn",

            "tipo_contenedor":
                tipo_contenedor,

            "contingencia":
                0,
        }


        self.stdout.write("")
        self.stdout.write(
            (
                "Ruta de prueba: "
                f"{ruta['origen']} "
                "→ "
                f"{ruta['destino']}"
            )
        )

        self.stdout.write(
            (
                "Contenedor: "
                f"{tipo_contenedor}'"
            )
        )


        self.stdout.write("")
        self.stdout.write(
            "Ejecutando calentamiento..."
        )


        calentamientos = [
            self._solicitud(
                (
                    f"{base_url}"
                    "/api/sesion/"
                ),
                token=token,
                timeout=timeout,
            ),

            self._solicitud(
                (
                    f"{base_url}"
                    "/api/rutas/"
                ),
                token=token,
                timeout=timeout,
            ),

            self._solicitud(
                (
                    f"{base_url}"
                    "/api/opciones-contenedores/"
                ),
                token=token,
                metodo="POST",
                datos=
                    payload_opciones,
                timeout=timeout,
            ),

            self._solicitud(
                (
                    f"{base_url}"
                    "/api/cotizar/"
                ),
                token=token,
                metodo="POST",
                datos=
                    payload_cotizar,
                timeout=timeout,
            ),
        ]


        if any(
            not resultado[
                "ok"
            ]
            for resultado
            in calentamientos
        ):
            raise CommandError(
                (
                    "Falló el calentamiento "
                    "de uno o más endpoints. "
                    "Revise el servidor antes "
                    "de medir rendimiento."
                )
            )


        self.stdout.write(
            self.style.SUCCESS(
                "Calentamiento correcto."
            )
        )


        endpoints = [
            {
                "nombre":
                    "GET sesión",

                "url":
                    (
                        f"{base_url}"
                        "/api/sesion/"
                    ),

                "metodo":
                    "GET",

                "datos":
                    None,
            },

            {
                "nombre":
                    "GET rutas",

                "url":
                    (
                        f"{base_url}"
                        "/api/rutas/"
                    ),

                "metodo":
                    "GET",

                "datos":
                    None,
            },

            {
                "nombre":
                    "POST opciones",

                "url":
                    (
                        f"{base_url}"
                        "/api/opciones-contenedores/"
                    ),

                "metodo":
                    "POST",

                "datos":
                    payload_opciones,
            },

            {
                "nombre":
                    "POST cotizar",

                "url":
                    (
                        f"{base_url}"
                        "/api/cotizar/"
                    ),

                "metodo":
                    "POST",

                "datos":
                    payload_cotizar,
            },
        ]


        resultados_globales = []

        for nivel in niveles:
            total = (
                nivel
                * factor
            )

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    (
                        "==================== "
                        f"{nivel} CONCURRENTES "
                        "===================="
                    )
                )
            )

            for endpoint in endpoints:
                resultado = (
                    self._ejecutar_lote(
                        nombre=
                            endpoint[
                                "nombre"
                            ],

                        url=
                            endpoint[
                                "url"
                            ],

                        token=
                            token,

                        concurrencia=
                            nivel,

                        total=
                            total,

                        metodo=
                            endpoint[
                                "metodo"
                            ],

                        datos=
                            endpoint[
                                "datos"
                            ],

                        timeout=
                            timeout,
                    )
                )

                resultados_globales.append(
                    resultado
                )


        errores_totales = sum(
            resultado[
                "fallidos"
            ]

            for resultado
            in resultados_globales
        )


        self.stdout.write("")
        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            self.style.SUCCESS(
                "RESUMEN FINAL"
            )
        )

        self.stdout.write(
            "=" * 60
        )


        for resultado in (
            resultados_globales
        ):
            estado = (
                "OK"
                if resultado[
                    "fallidos"
                ] == 0
                else "ERROR"
            )

            self.stdout.write(
                (
                    f"{resultado['nombre']:<15} "
                    f"| C={resultado['concurrencia']:<3} "
                    f"| "
                    f"P95={resultado['p95_ms']:.2f} ms "
                    f"| "
                    f"{resultado['solicitudes_segundo']:.2f} req/s "
                    f"| {estado}"
                )
            )


        if errores_totales > 0:
            raise CommandError(
                (
                    "La prueba terminó con "
                    f"{errores_totales} "
                    "solicitud(es) fallida(s)."
                )
            )


        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Todas las solicitudes "
                    "terminaron correctamente."
                )
            )
        )