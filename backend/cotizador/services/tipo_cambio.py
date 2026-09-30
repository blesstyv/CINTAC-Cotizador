import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from cotizador.models import TipoCambio


URL_DOLAR = "https://mindicador.cl/api/dolar"

FUENTE_DOLAR = (
    "Mindicador - Dólar Observado"
)

TIMEOUT_SEGUNDOS = 5

CACHE_MINUTOS = 60


class TipoCambioNoDisponible(Exception):
    pass


def _guardar_tipo_cambio(
    valor,
    fecha_referencia,
):
    registro, creado = (
        TipoCambio.objects.update_or_create(
            moneda_origen="USD",
            moneda_destino="CLP",
            fecha_referencia=
                fecha_referencia,
            defaults={
                "valor":
                    valor,

                "fuente":
                    FUENTE_DOLAR,
            },
        )
    )

    if not creado:
        TipoCambio.objects.filter(
            pk=registro.pk
        ).update(
            obtenido_en=
                timezone.now()
        )

        registro.refresh_from_db()

    return registro


def _obtener_cache_reciente():
    limite = (
        timezone.now()
        - timedelta(
            minutes=CACHE_MINUTOS
        )
    )

    return (
        TipoCambio.objects
        .filter(
            moneda_origen="USD",
            moneda_destino="CLP",
            obtenido_en__gte=limite,
        )
        .order_by(
            "-fecha_referencia",
            "-obtenido_en",
        )
        .first()
    )


def _obtener_ultimo_respaldo():
    return (
        TipoCambio.objects
        .filter(
            moneda_origen="USD",
            moneda_destino="CLP",
        )
        .order_by(
            "-fecha_referencia",
            "-obtenido_en",
        )
        .first()
    )


def _obtener_desde_internet():
    solicitud = Request(
        URL_DOLAR,
        headers={
            "User-Agent":
                "CINTAC-Cotizador/1.0",

            "Accept":
                "application/json",
        },
    )

    try:
        with urlopen(
            solicitud,
            timeout=TIMEOUT_SEGUNDOS,
        ) as respuesta:
            contenido = (
                respuesta
                .read()
                .decode("utf-8")
            )

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
    ) as error:
        raise TipoCambioNoDisponible(
            (
                "No fue posible consultar "
                "el tipo de cambio en línea."
            )
        ) from error

    try:
        datos = json.loads(
            contenido
        )

    except json.JSONDecodeError as error:
        raise TipoCambioNoDisponible(
            (
                "La fuente del tipo de cambio "
                "entregó una respuesta inválida."
            )
        ) from error

    serie = datos.get(
        "serie"
    )

    if (
        not isinstance(
            serie,
            list,
        )
        or not serie
    ):
        raise TipoCambioNoDisponible(
            (
                "La fuente no entregó "
                "información del dólar."
            )
        )

    ultimo_registro = (
        serie[0]
    )

    try:
        valor = Decimal(
            str(
                ultimo_registro[
                    "valor"
                ]
            )
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        InvalidOperation,
    ) as error:
        raise TipoCambioNoDisponible(
            (
                "El valor recibido para "
                "el dólar no es válido."
            )
        ) from error

    if valor <= 0:
        raise TipoCambioNoDisponible(
            (
                "El tipo de cambio recibido "
                "debe ser mayor que cero."
            )
        )

    fecha_texto = (
        ultimo_registro.get(
            "fecha"
        )
    )

    if not fecha_texto:
        raise TipoCambioNoDisponible(
            (
                "La fuente no entregó "
                "una fecha válida."
            )
        )

    fecha_datetime = (
        parse_datetime(
            fecha_texto
        )
    )

    if fecha_datetime is None:
        raise TipoCambioNoDisponible(
            (
                "La fecha recibida para "
                "el tipo de cambio no "
                "tiene un formato válido."
            )
        )

    return _guardar_tipo_cambio(
        valor=valor,
        fecha_referencia=
            fecha_datetime.date(),
    )


def obtener_tipo_cambio():
    cache = (
        _obtener_cache_reciente()
    )

    if cache is not None:
        return {
            "valor":
                cache.valor,

            "fecha":
                cache.fecha_referencia,

            "fuente":
                cache.fuente,

            "modo":
                "cache",
        }

    try:
        registro = (
            _obtener_desde_internet()
        )

        return {
            "valor":
                registro.valor,

            "fecha":
                registro.fecha_referencia,

            "fuente":
                registro.fuente,

            "modo":
                "en_linea",
        }

    except TipoCambioNoDisponible:
        respaldo = (
            _obtener_ultimo_respaldo()
        )

        if respaldo is None:
            raise TipoCambioNoDisponible(
                (
                    "No fue posible obtener "
                    "el tipo de cambio y no "
                    "existe un valor de "
                    "respaldo almacenado."
                )
            )

        return {
            "valor":
                respaldo.valor,

            "fecha":
                respaldo.fecha_referencia,

            "fuente":
                respaldo.fuente,

            "modo":
                "respaldo",
        }


def convertir_usd_a_clp(
    monto_usd,
    tipo_cambio,
):
    monto = Decimal(
        str(monto_usd)
    )

    tasa = Decimal(
        str(tipo_cambio)
    )

    if monto < 0:
        raise ValueError(
            "El monto no puede ser negativo."
        )

    if tasa <= 0:
        raise ValueError(
            (
                "El tipo de cambio debe "
                "ser mayor que cero."
            )
        )

    return monto * tasa


def convertir_clp_a_usd(
    monto_clp,
    tipo_cambio,
):
    monto = Decimal(
        str(monto_clp)
    )

    tasa = Decimal(
        str(tipo_cambio)
    )

    if monto < 0:
        raise ValueError(
            "El monto no puede ser negativo."
        )

    if tasa <= 0:
        raise ValueError(
            (
                "El tipo de cambio debe "
                "ser mayor que cero."
            )
        )

    return monto / tasa