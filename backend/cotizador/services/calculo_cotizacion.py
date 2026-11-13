"""
Reglas financieras centralizadas del cotizador CINTAC.

El backend es la autoridad del resultado definitivo. Este módulo
concentra, en funciones puras y sin acceso HTTP, las reglas que antes
estaban repetidas entre la vista de cotización y el historial:

* El valor monetario de la carga se suma UNA sola vez al flete total,
  nunca por contenedor, y no modifica tarifas, cantidad ni tránsito.
* Si el valor no está activo, no existe o es 0, se considera 0 y el
  total final es exactamente el flete total.
* Un monto en CLP se convierte a USD con el mismo dólar de la
  cotización (una sola división, redondeo a centavos).
* El equivalente CLP del total final usa el monto CLP exacto ingresado
  para evitar una doble conversión CLP→USD→CLP.

Los montos USD se redondean a 2 decimales y los CLP a pesos enteros,
siempre con ROUND_HALF_UP.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


CENTAVOS = Decimal("0.01")
PESOS = Decimal("1")
CERO = Decimal("0.00")

MONEDAS_VALOR_CARGA = ("USD", "CLP")


class ConversionNoDisponible(Exception):
    """El valor de carga está en CLP y no hay tipo de cambio."""


def redondear_usd(valor) -> Decimal:
    return Decimal(valor).quantize(
        CENTAVOS,
        rounding=ROUND_HALF_UP,
    )


def redondear_clp(valor) -> Decimal:
    return Decimal(valor).quantize(
        PESOS,
        rounding=ROUND_HALF_UP,
    )


@dataclass(frozen=True)
class ValorCarga:
    """Valor monetario de la carga ya normalizado."""

    ingresado: Decimal
    moneda: str
    usd: Decimal

    @property
    def incluido(self) -> bool:
        return self.ingresado > 0


@dataclass(frozen=True)
class TotalesFinales:
    total_final_min: Decimal
    total_final_max: Decimal
    total_final_min_clp: Optional[Decimal]
    total_final_max_clp: Optional[Decimal]


def normalizar_valor_carga(
    monto,
    moneda="USD",
    incluir=True,
    tipo_cambio=None,
) -> ValorCarga:
    """
    Devuelve el valor de carga en su moneda original y en USD.

    ``incluir=False`` o un monto vacío/0 producen un valor 0 que no
    altera el total. Para CLP con monto > 0 se exige tipo de cambio.
    """
    if moneda not in MONEDAS_VALOR_CARGA:
        raise ValueError("Moneda de valor de carga no soportada.")

    if not incluir or monto in (None, ""):
        return ValorCarga(CERO, moneda, CERO)

    ingresado = redondear_usd(monto)

    if ingresado < 0:
        raise ValueError("El valor de carga no puede ser negativo.")

    if ingresado == 0:
        return ValorCarga(CERO, moneda, CERO)

    if moneda == "USD":
        return ValorCarga(ingresado, moneda, ingresado)

    if tipo_cambio is None:
        raise ConversionNoDisponible(
            "No es posible convertir el valor de carga en CLP "
            "porque no hay un tipo de cambio disponible."
        )

    tasa = Decimal(str(tipo_cambio))

    if tasa <= 0:
        raise ConversionNoDisponible(
            "El tipo de cambio disponible no es válido."
        )

    return ValorCarga(
        ingresado,
        moneda,
        redondear_usd(ingresado / tasa),
    )


def calcular_totales_finales(
    flete_min,
    flete_max,
    valor_carga: ValorCarga,
    flete_min_clp=None,
    flete_max_clp=None,
    tipo_cambio=None,
) -> TotalesFinales:
    """
    Total final = flete total + valor de carga (una sola vez).

    Los equivalentes CLP solo se calculan cuando existe el flete en
    CLP (es decir, hubo tipo de cambio al cotizar).
    """
    flete_min = Decimal(flete_min)
    flete_max = Decimal(flete_max)

    total_min = redondear_usd(flete_min + valor_carga.usd)
    total_max = redondear_usd(flete_max + valor_carga.usd)

    total_min_clp = None
    total_max_clp = None

    if flete_min_clp is not None and flete_max_clp is not None:
        if not valor_carga.incluido:
            total_min_clp = redondear_clp(flete_min_clp)
            total_max_clp = redondear_clp(flete_max_clp)

        elif valor_carga.moneda == "CLP":
            total_min_clp = redondear_clp(
                Decimal(flete_min_clp) + valor_carga.ingresado
            )
            total_max_clp = redondear_clp(
                Decimal(flete_max_clp) + valor_carga.ingresado
            )

        elif tipo_cambio is not None:
            tasa = Decimal(str(tipo_cambio))
            total_min_clp = redondear_clp(total_min * tasa)
            total_max_clp = redondear_clp(total_max * tasa)

    return TotalesFinales(
        total_min,
        total_max,
        total_min_clp,
        total_max_clp,
    )


def totales_finales_de_cotizacion(cotizacion) -> TotalesFinales:
    """
    Totales finales de una cotización guardada.

    Usa la instantánea persistida; solo si el registro es anterior a
    esa columna los reconstruye con los valores guardados en el mismo
    registro (nunca con tarifas ni tipos de cambio actuales).
    """
    if (
        cotizacion.total_final_min is not None
        and cotizacion.total_final_max is not None
    ):
        def _clp_o_nulo(valor):
            return (
                redondear_clp(valor)
                if valor is not None
                else None
            )

        return TotalesFinales(
            redondear_usd(cotizacion.total_final_min),
            redondear_usd(cotizacion.total_final_max),
            _clp_o_nulo(cotizacion.total_final_min_clp),
            _clp_o_nulo(cotizacion.total_final_max_clp),
        )

    valor = ValorCarga(
        cotizacion.valor_carga_ingresado,
        cotizacion.valor_carga_moneda,
        cotizacion.valor_carga,
    )

    return calcular_totales_finales(
        cotizacion.total_min,
        cotizacion.total_max,
        valor,
        cotizacion.total_min_clp,
        cotizacion.total_max_clp,
        cotizacion.tipo_cambio,
    )
