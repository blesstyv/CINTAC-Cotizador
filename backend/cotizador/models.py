from django.db import models


class Puerto(models.Model):
    nombre = models.CharField(max_length=100)
    pais = models.CharField(max_length=100)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre", "pais"],
                name="puerto_nombre_pais_unico",
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.pais}"


class Ruta(models.Model):
    TIPO_RUTA_CHOICES = [
        ("Directo", "Directo"),
        ("Transbordo", "Transbordo"),
        ("Directo / Transbordo", "Directo / Transbordo"),
    ]

    puerto_origen = models.ForeignKey(
        Puerto,
        on_delete=models.PROTECT,
        related_name="rutas_origen",
    )

    puerto_destino = models.ForeignKey(
        Puerto,
        on_delete=models.PROTECT,
        related_name="rutas_destino",
    )

    tipo_ruta = models.CharField(
        max_length=30,
        choices=TIPO_RUTA_CHOICES,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["puerto_origen", "puerto_destino"],
                name="ruta_origen_destino_unica",
            )
        ]

    def __str__(self):
        return f"{self.puerto_origen.nombre} → {self.puerto_destino.nombre}"


class Tarifa(models.Model):
    TIPO_CONTENEDOR_CHOICES = [
        ("20", "20 pies"),
        ("40", "40 pies"),
    ]

    ruta = models.ForeignKey(
        Ruta,
        on_delete=models.CASCADE,
        related_name="tarifas",
    )

    tipo_contenedor = models.CharField(
        max_length=2,
        choices=TIPO_CONTENEDOR_CHOICES,
    )

    valor_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    valor_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    fuente = models.CharField(
        max_length=200,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ruta", "tipo_contenedor"],
                name="tarifa_ruta_contenedor_unica",
            )
        ]

    def __str__(self):
        return f"{self.ruta} - {self.tipo_contenedor} pies"


class TiempoTransito(models.Model):
    ruta = models.OneToOneField(
        Ruta,
        on_delete=models.CASCADE,
        related_name="tiempo_transito",
    )

    dias_minimos = models.PositiveIntegerField()
    dias_maximos = models.PositiveIntegerField()

    def __str__(self):
        return (
            f"{self.ruta} - "
            f"{self.dias_minimos} a {self.dias_maximos} días"
        )