from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_cintac",
    )

    autorizado = models.BooleanField(
        default=False,
    )

    def __str__(self):
        estado = (
            "Autorizado"
            if self.autorizado
            else "No autorizado"
        )

        return (
            f"{self.usuario.username} - {estado}"
        )


class Puerto(models.Model):
    nombre = models.CharField(
        max_length=100,
    )

    pais = models.CharField(
        max_length=100,
    )

    class Meta:
        ordering = ["nombre"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "nombre",
                    "pais",
                ],
                name="puerto_nombre_pais_unico",
            )
        ]

    def __str__(self):
        return (
            f"{self.nombre} - "
            f"{self.pais}"
        )


class TipoContenedor(models.Model):
    codigo = models.CharField(
        max_length=2,
        unique=True,
    )

    nombre = models.CharField(
        max_length=50,
    )

    capacidad_tn = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("25.00"),
        validators=[
            MinValueValidator(
                Decimal("0.01")
            )
        ],
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["codigo"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    capacidad_tn__gt=0
                ),
                name=(
                    "tipo_contenedor_"
                    "capacidad_positiva"
                ),
            )
        ]

    def clean(self):
        super().clean()

        if (
            self.capacidad_tn is not None
            and self.capacidad_tn <= 0
        ):
            raise ValidationError(
                {
                    "capacidad_tn":
                        (
                            "La capacidad debe "
                            "ser mayor que cero."
                        )
                }
            )

    def __str__(self):
        return (
            f"{self.nombre} - "
            f"{self.capacidad_tn} TN"
        )


class Ruta(models.Model):
    TIPO_RUTA_CHOICES = [
        (
            "Directo",
            "Directo",
        ),
        (
            "Transbordo",
            "Transbordo",
        ),
        (
            "Directo / Transbordo",
            "Directo / Transbordo",
        ),
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
                fields=[
                    "puerto_origen",
                    "puerto_destino",
                ],
                name=(
                    "ruta_origen_"
                    "destino_unica"
                ),
            ),

            models.CheckConstraint(
                condition=~models.Q(
                    puerto_origen=models.F(
                        "puerto_destino"
                    )
                ),
                name=(
                    "ruta_origen_"
                    "destino_distintos"
                ),
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.puerto_origen_id is not None
            and self.puerto_destino_id is not None
            and self.puerto_origen_id
            == self.puerto_destino_id
        ):
            raise ValidationError(
                {
                    "puerto_destino":
                        (
                            "El puerto de destino "
                            "debe ser distinto al "
                            "puerto de origen."
                        )
                }
            )

    def __str__(self):
        return (
            f"{self.puerto_origen.nombre} "
            f"→ "
            f"{self.puerto_destino.nombre}"
        )


class Tarifa(models.Model):
    TIPO_CONTENEDOR_CHOICES = [
        (
            "20",
            "20 pies",
        ),
        (
            "40",
            "40 pies",
        ),
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
        validators=[
            MinValueValidator(
                Decimal("0.01")
            )
        ],
    )

    valor_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01")
            )
        ],
    )

    fuente = models.CharField(
        max_length=200,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "ruta",
                    "tipo_contenedor",
                ],
                name=(
                    "tarifa_ruta_"
                    "contenedor_unica"
                ),
            ),

            models.CheckConstraint(
                condition=models.Q(
                    valor_minimo__gt=0
                ),
                name=(
                    "tarifa_minima_"
                    "positiva"
                ),
            ),

            models.CheckConstraint(
                condition=models.Q(
                    valor_maximo__gt=0
                ),
                name=(
                    "tarifa_maxima_"
                    "positiva"
                ),
            ),

            models.CheckConstraint(
                condition=models.Q(
                    valor_maximo__gte=models.F(
                        "valor_minimo"
                    )
                ),
                name=(
                    "tarifa_maxima_"
                    "mayor_igual_minima"
                ),
            ),
        ]

    def clean(self):
        super().clean()

        errores = {}

        if (
            self.valor_minimo is not None
            and self.valor_minimo <= 0
        ):
            errores["valor_minimo"] = (
                "La tarifa mínima debe "
                "ser mayor que cero."
            )

        if (
            self.valor_maximo is not None
            and self.valor_maximo <= 0
        ):
            errores["valor_maximo"] = (
                "La tarifa máxima debe "
                "ser mayor que cero."
            )

        if (
            self.valor_minimo is not None
            and self.valor_maximo is not None
            and self.valor_maximo
            < self.valor_minimo
        ):
            errores["valor_maximo"] = (
                "La tarifa máxima no "
                "puede ser menor que "
                "la tarifa mínima."
            )

        if errores:
            raise ValidationError(
                errores
            )

    def __str__(self):
        return (
            f"{self.ruta} - "
            f"{self.tipo_contenedor} pies"
        )


class TiempoTransito(models.Model):
    ruta = models.OneToOneField(
        Ruta,
        on_delete=models.CASCADE,
        related_name="tiempo_transito",
    )

    dias_minimos = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1)
        ],
    )

    dias_maximos = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1)
        ],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    dias_minimos__gte=1
                ),
                name=(
                    "transito_minimo_"
                    "positivo"
                ),
            ),

            models.CheckConstraint(
                condition=models.Q(
                    dias_maximos__gte=1
                ),
                name=(
                    "transito_maximo_"
                    "positivo"
                ),
            ),

            models.CheckConstraint(
                condition=models.Q(
                    dias_maximos__gte=models.F(
                        "dias_minimos"
                    )
                ),
                name=(
                    "transito_maximo_"
                    "mayor_igual_minimo"
                ),
            ),
        ]

    def clean(self):
        super().clean()

        errores = {}

        if (
            self.dias_minimos is not None
            and self.dias_minimos < 1
        ):
            errores["dias_minimos"] = (
                "El tránsito mínimo "
                "debe ser mayor que cero."
            )

        if (
            self.dias_maximos is not None
            and self.dias_maximos < 1
        ):
            errores["dias_maximos"] = (
                "El tránsito máximo "
                "debe ser mayor que cero."
            )

        if (
            self.dias_minimos is not None
            and self.dias_maximos is not None
            and self.dias_maximos
            < self.dias_minimos
        ):
            errores["dias_maximos"] = (
                "El tránsito máximo no "
                "puede ser menor que "
                "el tránsito mínimo."
            )

        if errores:
            raise ValidationError(
                errores
            )

    def __str__(self):
        return (
            f"{self.ruta} - "
            f"{self.dias_minimos} a "
            f"{self.dias_maximos} días"
        )


class TipoCambio(models.Model):
    moneda_origen = models.CharField(
        max_length=3,
        default="USD",
    )

    moneda_destino = models.CharField(
        max_length=3,
        default="CLP",
    )

    valor = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[
            MinValueValidator(
                Decimal("0.0001")
            )
        ],
    )

    fecha_referencia = models.DateField()

    fuente = models.CharField(
        max_length=100,
    )

    obtenido_en = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-fecha_referencia",
            "-obtenido_en",
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    valor__gt=0
                ),
                name=(
                    "tipo_cambio_"
                    "valor_positivo"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "moneda_origen",
                    "moneda_destino",
                    "fecha_referencia",
                ],
                name=(
                    "tipo_cambio_"
                    "monedas_fecha_unica"
                ),
            ),
        ]

    def clean(self):
        super().clean()

        errores = {}

        if (
            self.valor is not None
            and self.valor <= 0
        ):
            errores["valor"] = (
                "El tipo de cambio "
                "debe ser mayor que cero."
            )

        if (
            self.moneda_origen
            and self.moneda_destino
            and self.moneda_origen
            == self.moneda_destino
        ):
            errores["moneda_destino"] = (
                "Las monedas deben ser distintas."
            )

        if errores:
            raise ValidationError(
                errores
            )

    def __str__(self):
        return (
            f"{self.moneda_origen}/"
            f"{self.moneda_destino} - "
            f"{self.valor} - "
            f"{self.fecha_referencia}"
        )