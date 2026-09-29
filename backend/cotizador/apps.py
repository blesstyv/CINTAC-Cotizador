from django.apps import AppConfig


class CotizadorConfig(AppConfig):
    default_auto_field = (
        "django.db.models.BigAutoField"
    )

    name = "cotizador"

    def ready(self):
        import cotizador.signals