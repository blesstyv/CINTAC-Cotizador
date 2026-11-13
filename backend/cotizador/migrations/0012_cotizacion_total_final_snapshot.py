"""
Persiste la instantánea del total final (flete + valor de carga).

Los registros existentes se completan con los valores guardados en el
MISMO registro (flete, valor de carga, moneda y dólar de la cotización),
aplicando la regla vigente al cotizar. No se consultan tarifas ni tipos
de cambio actuales y no se modifica ninguna columna existente.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


def _usd(valor):
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clp(valor):
    return Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def completar_totales_finales(apps, schema_editor):
    Cotizacion = apps.get_model("cotizador", "Cotizacion")

    pendientes = Cotizacion.objects.filter(total_final_min__isnull=True)

    for cot in pendientes.iterator(chunk_size=500):
        total_min = _usd(cot.total_min + cot.valor_carga)
        total_max = _usd(cot.total_max + cot.valor_carga)

        min_clp = None
        max_clp = None

        if cot.total_min_clp is not None and cot.total_max_clp is not None:
            if cot.valor_carga_ingresado <= 0:
                min_clp = _clp(cot.total_min_clp)
                max_clp = _clp(cot.total_max_clp)
            elif cot.valor_carga_moneda == "CLP":
                min_clp = _clp(cot.total_min_clp + cot.valor_carga_ingresado)
                max_clp = _clp(cot.total_max_clp + cot.valor_carga_ingresado)
            elif cot.tipo_cambio is not None:
                min_clp = _clp(total_min * cot.tipo_cambio)
                max_clp = _clp(total_max * cot.tipo_cambio)

        Cotizacion.objects.filter(pk=cot.pk).update(
            total_final_min=total_min,
            total_final_max=total_max,
            total_final_min_clp=min_clp,
            total_final_max_clp=max_clp,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("cotizador", "0011_cotizacion_valor_carga_moneda"),
    ]

    operations = [
        migrations.AddField(
            model_name="cotizacion",
            name="total_final_min",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=21, null=True),
        ),
        migrations.AddField(
            model_name="cotizacion",
            name="total_final_max",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=21, null=True),
        ),
        migrations.AddField(
            model_name="cotizacion",
            name="total_final_min_clp",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=25, null=True),
        ),
        migrations.AddField(
            model_name="cotizacion",
            name="total_final_max_clp",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=25, null=True),
        ),
        migrations.RunPython(
            completar_totales_finales,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="cotizacion",
            constraint=models.CheckConstraint(
                condition=models.Q(("total_final_min__isnull", True), ("total_final_min__gte", models.F("total_min")), _connector="OR"),
                name="cot_total_final_min_ge_flete",
            ),
        ),
        migrations.AddConstraint(
            model_name="cotizacion",
            constraint=models.CheckConstraint(
                condition=models.Q(("total_final_max__isnull", True), ("total_final_max__gte", models.F("total_max")), _connector="OR"),
                name="cot_total_final_max_ge_flete",
            ),
        ),
        migrations.AddConstraint(
            model_name="cotizacion",
            constraint=models.CheckConstraint(
                condition=models.Q(("valor_carga_ingresado__gt", 0), ("valor_carga", 0), _connector="OR"),
                name="cot_valor_carga_sin_monto_cero",
            ),
        ),
        migrations.AddConstraint(
            model_name="cotizacion",
            constraint=models.CheckConstraint(
                condition=models.Q(("valor_carga_moneda", "CLP"), ("valor_carga", models.F("valor_carga_ingresado")), _connector="OR"),
                name="cot_valor_carga_usd_coherente",
            ),
        ),
    ]
