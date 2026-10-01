from django.contrib import admin

from .models import (
    PerfilUsuario,
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoCambio,
    TipoContenedor,
)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "autorizado",
        "puede_gestionar_datos",
    )

    list_editable = (
        "autorizado",
        "puede_gestionar_datos",
    )

    search_fields = (
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    )

    list_filter = (
        "autorizado",
        "puede_gestionar_datos",
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

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = (
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

    search_fields = (
        "ruta__puerto_origen__nombre",
        "ruta__puerto_destino__nombre",
    )


@admin.register(TipoCambio)
class TipoCambioAdmin(admin.ModelAdmin):
    list_display = (
        "moneda_origen",
        "moneda_destino",
        "valor",
        "fecha_referencia",
        "fuente",
        "obtenido_en",
    )

    readonly_fields = (
        "obtenido_en",
    )

    list_filter = (
        "moneda_origen",
        "moneda_destino",
        "fuente",
    )

    search_fields = (
        "moneda_origen",
        "moneda_destino",
        "fuente",
    )

    ordering = (
        "-fecha_referencia",
        "-obtenido_en",
    )