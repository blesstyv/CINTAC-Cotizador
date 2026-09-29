from django.contrib import admin

from .models import (
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)


@admin.register(Puerto)
class PuertoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "pais",
    )

    search_fields = (
        "nombre",
        "pais",
    )


@admin.register(TipoContenedor)
class TipoContenedorAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "capacidad_tn",
        "activo",
    )

    list_editable = (
        "capacidad_tn",
        "activo",
    )


@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display = (
        "puerto_origen",
        "puerto_destino",
        "tipo_ruta",
    )

    list_filter = (
        "tipo_ruta",
    )

    search_fields = (
        "puerto_origen__nombre",
        "puerto_destino__nombre",
    )


@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = (
        "ruta",
        "tipo_contenedor",
        "valor_minimo",
        "valor_maximo",
        "fuente",
    )

    list_filter = (
        "tipo_contenedor",
    )

    search_fields = (
        "ruta__puerto_origen__nombre",
        "ruta__puerto_destino__nombre",
        "fuente",
    )


@admin.register(TiempoTransito)
class TiempoTransitoAdmin(admin.ModelAdmin):
    list_display = (
        "ruta",
        "dias_minimos",
        "dias_maximos",
    )