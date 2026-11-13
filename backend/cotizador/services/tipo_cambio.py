"""
Obtención del tipo de cambio USD/CLP con trazabilidad del origen.

Modos informados al usuario:

* ``en_linea``: consultado ahora en la fuente externa (mindicador.cl).
* ``cache``: valor consultado en línea hace menos de CACHE_MINUTOS y
  cuya fecha de referencia sigue vigente (no se vuelve a consultar).
* ``respaldo``: la fuente externa no respondió; se usa el último valor
  almacenado en PostgreSQL, informando su fecha y antigüedad.

Si la fuente falla, se evita reintentar en cada cotización durante
TIPO_CAMBIO_REINTENTO_SEGUNDOS para no bloquear al usuario con el
tiempo de espera de la red.
"""

import json
import logging

from datetime import timedelta

from decimal import (
    Decimal,
    InvalidOperation,
)

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.request import (
    Request,
    urlopen,
)

from django.conf import settings
from django.core.cache import cache as cache_django
from django.utils import timezone

from django.utils.dateparse import (
    parse_datetime,
)

from cotizador.models import (
    TipoCambio,
)


URL_DOLAR = (
    "https://mindicador.cl/api/dolar"
)

FUENTE_DOLAR = (
    "Mindicador - Dólar Observado"
)

TIMEOUT_SEGUNDOS = 5

CACHE_MINUTOS = 60

# Un valor con fecha de referencia más antigua que esto se informa
# como desactualizado (cubre fines de semana largos y feriados).
DIAS_VIGENCIA = 5

CLAVE_FALLO_RECIENTE = "cintac:tipo_cambio:fallo_reciente"

logger = logging.getLogger(__name__)


class TipoCambioNoDisponible(
    Exception
):
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

    # Un registro recién creado con una fecha de referencia antigua
    # (por ejemplo, el respaldo cargado en el despliegue) no es una
    # consulta reciente: no debe ocultar el intento en línea.
    fecha_minima = (
        timezone.localdate()
        - timedelta(days=DIAS_VIGENCIA)
    )

    return (
        TipoCambio.objects
        .filter(
            moneda_origen="USD",
            moneda_destino="CLP",
            obtenido_en__gte=limite,
            fecha_referencia__gte=fecha_minima,
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
            contenido_bytes = (
                respuesta.read()
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
        contenido = (
            contenido_bytes
            .decode("utf-8")
        )

    except UnicodeDecodeError as error:
        raise TipoCambioNoDisponible(
            (
                "La fuente del tipo de cambio "
                "entregó contenido con una "
                "codificación inválida."
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


    if not isinstance(
        datos,
        dict,
    ):
        raise TipoCambioNoDisponible(
            (
                "La fuente del tipo de cambio "
                "entregó una estructura inválida."
            )
        )


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

    if not isinstance(
        ultimo_registro,
        dict,
    ):
        raise TipoCambioNoDisponible(
            (
                "La información recibida "
                "para el dólar no tiene "
                "una estructura válida."
            )
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


    if not valor.is_finite():
        raise TipoCambioNoDisponible(
            (
                "El valor recibido para "
                "el dólar no es válido."
            )
        )


    try:
        valor_invalido = (
            valor <= 0
        )

    except InvalidOperation as error:
        raise TipoCambioNoDisponible(
            (
                "El valor recibido para "
                "el dólar no es válido."
            )
        ) from error


    if valor_invalido:
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

    if (
        not fecha_texto
        or not isinstance(
            fecha_texto,
            str,
        )
    ):
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


def antiguedad_dias(fecha_referencia):
    """Días transcurridos desde la fecha de referencia del dólar."""
    if fecha_referencia is None:
        return None

    return max(
        (timezone.localdate() - fecha_referencia).days,
        0,
    )


def _resultado(registro, modo):
    antiguedad = antiguedad_dias(
        registro.fecha_referencia
    )

    return {
        "valor":
            registro.valor,

        "fecha":
            registro.fecha_referencia,

        "fuente":
            registro.fuente,

        "modo":
            modo,

        "obtenidoEn":
            registro.obtenido_en,

        "antiguedadDias":
            antiguedad,

        "desactualizado":
            (
                antiguedad is not None
                and antiguedad > DIAS_VIGENCIA
            ),
    }


def _reintento_suspendido():
    espera = getattr(
        settings,
        "TIPO_CAMBIO_REINTENTO_SEGUNDOS",
        0,
    )

    return (
        espera > 0
        and bool(cache_django.get(CLAVE_FALLO_RECIENTE))
    )


def _registrar_fallo():
    espera = getattr(
        settings,
        "TIPO_CAMBIO_REINTENTO_SEGUNDOS",
        0,
    )

    if espera > 0:
        cache_django.set(
            CLAVE_FALLO_RECIENTE,
            True,
            espera,
        )


def obtener_tipo_cambio():
    cache = (
        _obtener_cache_reciente()
    )

    if cache is not None:
        return _resultado(
            cache,
            "cache",
        )

    if not _reintento_suspendido():
        try:
            registro = (
                _obtener_desde_internet()
            )

            return _resultado(
                registro,
                "en_linea",
            )

        except TipoCambioNoDisponible as error:
            logger.warning(
                "Tipo de cambio en línea no disponible: %s",
                error,
            )
            _registrar_fallo()

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

    return _resultado(
        respaldo,
        "respaldo",
    )


def convertir_usd_a_clp(
    monto_usd,
    tipo_cambio,
):
    try:
        monto = Decimal(
            str(monto_usd)
        )

        tasa = Decimal(
            str(tipo_cambio)
        )

    except (
        TypeError,
        ValueError,
        InvalidOperation,
    ) as error:
        raise ValueError(
            "El monto o tipo de cambio no es válido."
        ) from error


    if (
        not monto.is_finite()
        or not tasa.is_finite()
    ):
        raise ValueError(
            "El monto o tipo de cambio no es válido."
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


    return (
        monto * tasa
    )


def convertir_clp_a_usd(
    monto_clp,
    tipo_cambio,
):
    try:
        monto = Decimal(
            str(monto_clp)
        )

        tasa = Decimal(
            str(tipo_cambio)
        )

    except (
        TypeError,
        ValueError,
        InvalidOperation,
    ) as error:
        raise ValueError(
            "El monto o tipo de cambio no es válido."
        ) from error


    if (
        not monto.is_finite()
        or not tasa.is_finite()
    ):
        raise ValueError(
            "El monto o tipo de cambio no es válido."
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


    return (
        monto / tasa
    )