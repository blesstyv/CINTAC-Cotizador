"""Incorpora rutas oficiales hacia Callao para la evaluación del 17/11/2026.

Se ejecuta en cada build de Render y es idempotente: crea únicamente
registros ausentes. Nunca sobrescribe modificaciones posteriores de COMEX.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cotizador.models import Puerto, Ruta, Tarifa, TiempoTransito


DATOS = (
    ("San Antonio", "Chile"),
    ("Valparaiso", "Chile"),
)
DESTINO = ("Callao", "Perú")
TARIFAS = (("20", Decimal("900.00")), ("40", Decimal("970.00")))
DIAS_MIN = 3
DIAS_MAX = 5
FUENTE = "Product Owner - evaluación 17-11-2026"


class Command(BaseCommand):
    help = (
        "Crea las rutas oficiales San Antonio y Valparaiso hacia Callao "
        "(Perú), con tarifas de US$900/970 y tránsito entre 3 y 5 días, "
        "sin sobrescribir datos existentes."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        origenes = []

        # Resolver ambos orígenes ANTES de escribir: falla sin dejar
        # un Callao huérfano si falta algún puerto base.
        for nombre, pais in DATOS:
            puerto = Puerto.objects.filter(
                nombre__iexact=nombre,
                pais__iexact=pais,
            ).first()
            if puerto is None:
                raise CommandError(
                    f"Falta el puerto de origen {nombre}, {pais}. "
                    "Ejecute primero bootstrap_production."
                )
            origenes.append(puerto)

        destino, creado_puerto = Puerto.objects.get_or_create(
            nombre=DESTINO[0],
            pais=DESTINO[1],
        )

        nuevas = 0
        for origen in origenes:
            ruta, creada = Ruta.objects.get_or_create(
                puerto_origen=origen,
                puerto_destino=destino,
                defaults={"tipo_ruta": "Directo"},
            )

            if ruta.tipo_ruta != "Directo":
                raise CommandError(
                    f"La ruta {origen.nombre} → Callao ya existe, "
                    "pero no es Directo. Revisarla desde Administración."
                )

            nuevas += int(creada)

            TiempoTransito.objects.get_or_create(
                ruta=ruta,
                defaults={
                    "dias_minimos": DIAS_MIN,
                    "dias_maximos": DIAS_MAX,
                },
            )

            for codigo, monto in TARIFAS:
                Tarifa.objects.get_or_create(
                    ruta=ruta,
                    tipo_contenedor=codigo,
                    defaults={
                        "valor_minimo": monto,
                        "valor_maximo": monto,
                        "fuente": FUENTE,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Callao Perú: "
                f"{int(creado_puerto)} puerto nuevo, "
                f"{nuevas} rutas nuevas. "
                "Tránsito inicial: 3–5 días. "
                "Los registros existentes se conservaron."
            )
        )
