from django.db import connection
from django.http import JsonResponse
from django.contrib import admin
from django.urls import include, path




def health_check(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse(
            {"status": "error"},
            status=503,
        )

    return JsonResponse(
        {"status": "ok"}
    )


urlpatterns = [
    path(
        "health/",
        health_check,
        name="health-check",
    ),
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "api/",
        include("cotizador.urls"),
    ),
]