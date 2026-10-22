# Generated manually for PostgreSQL numeric compatibility.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cotizador", "0008_cotizacion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cotizacion",
            name="peso_kg",
            field=models.DecimalField(
                decimal_places=3,
                max_digits=21,
            ),
        ),
        migrations.AlterField(
            model_name="cotizacion",
            name="cantidad",
            field=models.PositiveBigIntegerField(),
        ),
        migrations.AlterField(
            model_name="cotizacion",
            name="total_min",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=20,
            ),
        ),
        migrations.AlterField(
            model_name="cotizacion",
            name="total_max",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=20,
            ),
        ),
        migrations.AlterField(
            model_name="cotizacion",
            name="total_min_clp",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=24,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="cotizacion",
            name="total_max_clp",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=24,
                null=True,
            ),
        ),
    ]
