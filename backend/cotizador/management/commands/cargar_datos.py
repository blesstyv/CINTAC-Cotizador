from django.core.management.base import BaseCommand

from cotizador.models import Puerto, Ruta, Tarifa, TiempoTransito


DATOS = [
    {
        "origen": "Shanghai",
        "pais": "China",
        "destino": "San Antonio",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1600,
        "tarifa20_max": 2800,
        "tarifa40_min": 2300,
        "tarifa40_max": 3800,
        "transito_min": 25,
        "transito_max": 32,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Shanghai",
        "pais": "China",
        "destino": "Valparaiso",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1650,
        "tarifa20_max": 2850,
        "tarifa40_min": 2350,
        "tarifa40_max": 3850,
        "transito_min": 26,
        "transito_max": 34,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Ningbo",
        "pais": "China",
        "destino": "San Antonio",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1600,
        "tarifa20_max": 2800,
        "tarifa40_min": 2300,
        "tarifa40_max": 3800,
        "transito_min": 26,
        "transito_max": 32,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Ningbo",
        "pais": "China",
        "destino": "Valparaiso",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1650,
        "tarifa20_max": 2850,
        "tarifa40_min": 2350,
        "tarifa40_max": 3850,
        "transito_min": 27,
        "transito_max": 34,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Qingdao",
        "pais": "China",
        "destino": "San Antonio",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1700,
        "tarifa20_max": 2900,
        "tarifa40_min": 2400,
        "tarifa40_max": 3900,
        "transito_min": 28,
        "transito_max": 34,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Qingdao",
        "pais": "China",
        "destino": "Valparaiso",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1750,
        "tarifa20_max": 2950,
        "tarifa40_min": 2450,
        "tarifa40_max": 3950,
        "transito_min": 29,
        "transito_max": 36,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Shenzhen / Yantian",
        "pais": "China",
        "destino": "San Antonio",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1650,
        "tarifa20_max": 2850,
        "tarifa40_min": 2350,
        "tarifa40_max": 3850,
        "transito_min": 27,
        "transito_max": 33,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Shenzhen / Yantian",
        "pais": "China",
        "destino": "Valparaiso",
        "tipo_ruta": "Directo / Transbordo",
        "tarifa20_min": 1700,
        "tarifa20_max": 2900,
        "tarifa40_min": 2400,
        "tarifa40_max": 3900,
        "transito_min": 28,
        "transito_max": 35,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Tianjin",
        "pais": "China",
        "destino": "San Antonio",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1800,
        "tarifa20_max": 3000,
        "tarifa40_min": 2500,
        "tarifa40_max": 4000,
        "transito_min": 30,
        "transito_max": 36,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Tianjin",
        "pais": "China",
        "destino": "Valparaiso",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1850,
        "tarifa20_max": 3050,
        "tarifa40_min": 2550,
        "tarifa40_max": 4050,
        "transito_min": 31,
        "transito_max": 38,
        "fuente": "Segucargo / Delpa Group 2026",
    },
    {
        "origen": "Busan",
        "pais": "Corea del Sur",
        "destino": "San Antonio",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1700,
        "tarifa20_max": 2900,
        "tarifa40_min": 2400,
        "tarifa40_max": 3900,
        "transito_min": 30,
        "transito_max": 38,
        "fuente": "MundoMaritimo / Delpa Group 2026",
    },
    {
        "origen": "Busan",
        "pais": "Corea del Sur",
        "destino": "Valparaiso",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1750,
        "tarifa20_max": 2950,
        "tarifa40_min": 2450,
        "tarifa40_max": 3950,
        "transito_min": 31,
        "transito_max": 40,
        "fuente": "MundoMaritimo / Delpa Group 2026",
    },
    {
        "origen": "Tokio / Yokohama",
        "pais": "Japon",
        "destino": "San Antonio",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1900,
        "tarifa20_max": 3100,
        "tarifa40_min": 2600,
        "tarifa40_max": 4100,
        "transito_min": 32,
        "transito_max": 40,
        "fuente": "Estimado referencial 2026",
    },
    {
        "origen": "Tokio / Yokohama",
        "pais": "Japon",
        "destino": "Valparaiso",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1950,
        "tarifa20_max": 3150,
        "tarifa40_min": 2650,
        "tarifa40_max": 4150,
        "transito_min": 33,
        "transito_max": 42,
        "fuente": "Estimado referencial 2026",
    },
    {
        "origen": "Ho Chi Minh",
        "pais": "Vietnam",
        "destino": "San Antonio",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1900,
        "tarifa20_max": 3200,
        "tarifa40_min": 2700,
        "tarifa40_max": 4300,
        "transito_min": 35,
        "transito_max": 42,
        "fuente": "Estimado referencial 2026",
    },
    {
        "origen": "Ho Chi Minh",
        "pais": "Vietnam",
        "destino": "Valparaiso",
        "tipo_ruta": "Transbordo",
        "tarifa20_min": 1950,
        "tarifa20_max": 3250,
        "tarifa40_min": 2750,
        "tarifa40_max": 4350,
        "transito_min": 36,
        "transito_max": 44,
        "fuente": "Estimado referencial 2026",
    },
]


class Command(BaseCommand):
    help = "Carga los datos iniciales utilizados por el cotizador CINTAC"

    def handle(self, *args, **options):
        for dato in DATOS:
            origen, _ = Puerto.objects.get_or_create(
                nombre=dato["origen"],
                pais=dato["pais"],
            )

            destino, _ = Puerto.objects.get_or_create(
                nombre=dato["destino"],
                pais="Chile",
            )

            ruta, _ = Ruta.objects.update_or_create(
                puerto_origen=origen,
                puerto_destino=destino,
                defaults={
                    "tipo_ruta": dato["tipo_ruta"],
                },
            )

            Tarifa.objects.update_or_create(
                ruta=ruta,
                tipo_contenedor="20",
                defaults={
                    "valor_minimo": dato["tarifa20_min"],
                    "valor_maximo": dato["tarifa20_max"],
                    "fuente": dato["fuente"],
                },
            )

            Tarifa.objects.update_or_create(
                ruta=ruta,
                tipo_contenedor="40",
                defaults={
                    "valor_minimo": dato["tarifa40_min"],
                    "valor_maximo": dato["tarifa40_max"],
                    "fuente": dato["fuente"],
                },
            )

            TiempoTransito.objects.update_or_create(
                ruta=ruta,
                defaults={
                    "dias_minimos": dato["transito_min"],
                    "dias_maximos": dato["transito_max"],
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Datos iniciales cargados correctamente."
            )
        )