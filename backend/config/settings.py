import os
from pathlib import Path

import dj_database_url

from dotenv import load_dotenv


# ==========================================
# RUTAS DEL PROYECTO
# ==========================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

PROJECT_ROOT = (
    BASE_DIR.parent
)


# ==========================================
# VARIABLES DE ENTORNO LOCALES
# ==========================================

load_dotenv(
    PROJECT_ROOT
    / ".env"
)


# ==========================================
# SEGURIDAD GENERAL
# ==========================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY"
)

if not SECRET_KEY:
    raise RuntimeError(
        (
            "No se encontró "
            "DJANGO_SECRET_KEY "
            "en las variables "
            "de entorno."
        )
    )


DEBUG = (
    os.getenv(
        "DJANGO_DEBUG",
        "False",
    )
    .strip()
    .lower()
    == "true"
)


# ==========================================
# HOSTS PERMITIDOS
# ==========================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        (
            "127.0.0.1,"
            "localhost"
        ),
    ).split(",")
    if host.strip()
]


# Render entrega automáticamente esta
# variable al servicio publicado.
RENDER_EXTERNAL_HOSTNAME = (
    os.getenv(
        "RENDER_EXTERNAL_HOSTNAME",
        "",
    ).strip()
)


if (
    RENDER_EXTERNAL_HOSTNAME
    and
    RENDER_EXTERNAL_HOSTNAME
    not in ALLOWED_HOSTS
):
    ALLOWED_HOSTS.append(
        RENDER_EXTERNAL_HOSTNAME
    )


# ==========================================
# APLICACIONES
# ==========================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # EXTERNAS
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",

    # PROYECTO
    "cotizador.apps.CotizadorConfig",
]


# ==========================================
# MIDDLEWARE
# ==========================================

MIDDLEWARE = [
    (
        "django.middleware."
        "security.SecurityMiddleware"
    ),

    (
        "whitenoise.middleware."
        "WhiteNoiseMiddleware"
    ),

    (
        "corsheaders.middleware."
        "CorsMiddleware"
    ),

    (
        "django.contrib.sessions."
        "middleware.SessionMiddleware"
    ),

    (
        "django.middleware."
        "common.CommonMiddleware"
    ),

    (
        "django.middleware.csrf."
        "CsrfViewMiddleware"
    ),

    (
        "django.contrib.auth."
        "middleware."
        "AuthenticationMiddleware"
    ),

    (
        "django.contrib.messages."
        "middleware."
        "MessageMiddleware"
    ),

    (
        "django.middleware."
        "clickjacking."
        "XFrameOptionsMiddleware"
    ),
]


ROOT_URLCONF = (
    "config.urls"
)


# ==========================================
# TEMPLATES
# ==========================================

TEMPLATES = [
    {
        "BACKEND":
            (
                "django.template."
                "backends.django."
                "DjangoTemplates"
            ),

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                (
                    "django.template."
                    "context_processors."
                    "request"
                ),

                (
                    "django.contrib.auth."
                    "context_processors."
                    "auth"
                ),

                (
                    "django.contrib.messages."
                    "context_processors."
                    "messages"
                ),
            ],
        },
    },
]


WSGI_APPLICATION = (
    "config.wsgi.application"
)


# ==========================================
# BASE DE DATOS
# ==========================================
#
# DESARROLLO LOCAL:
# Si DATABASE_URL está vacío o no existe,
# utilizamos SQLite.
#
# DESPLIEGUE WEB:
# Si DATABASE_URL existe,
# utilizamos PostgreSQL.
# ==========================================

DATABASE_URL = (
    os.getenv(
        "DATABASE_URL",
        "",
    ).strip()
)


if DATABASE_URL:
    DATABASES = {
        "default":
            dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=60,
                conn_health_checks=True,
            )
    }

else:
    DATABASES = {
        "default": {
            "ENGINE":
                (
                    "django.db."
                    "backends.sqlite3"
                ),

            "NAME":
                (
                    BASE_DIR
                    / "db.sqlite3"
                ),
        }
    }


# ==========================================
# VALIDACIÓN DE CONTRASEÑAS
# ==========================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME":
            (
                "django.contrib.auth."
                "password_validation."
                "UserAttributeSimilarityValidator"
            ),
    },

    {
        "NAME":
            (
                "django.contrib.auth."
                "password_validation."
                "MinimumLengthValidator"
            ),
    },

    {
        "NAME":
            (
                "django.contrib.auth."
                "password_validation."
                "CommonPasswordValidator"
            ),
    },

    {
        "NAME":
            (
                "django.contrib.auth."
                "password_validation."
                "NumericPasswordValidator"
            ),
    },
]


# ==========================================
# REGIONALIZACIÓN
# ==========================================

LANGUAGE_CODE = (
    "es-cl"
)

TIME_ZONE = (
    "America/Santiago"
)

USE_I18N = True

USE_TZ = True


# ==========================================
# ARCHIVOS ESTÁTICOS
# ==========================================

STATIC_URL = (
    "/static/"
)

STATIC_ROOT = (
    BASE_DIR
    / "staticfiles"
)


STORAGES = {
    "default": {
        "BACKEND":
            (
                "django.core.files."
                "storage."
                "FileSystemStorage"
            ),
    },

    "staticfiles": {
        "BACKEND":
            (
                "whitenoise.storage."
                "CompressedManifest"
                "StaticFilesStorage"
            ),
    },
}


# ==========================================
# CORREO
# ==========================================

EMAIL_BACKEND = (
    "django.core.mail."
    "backends.console."
    "EmailBackend"
)


# ==========================================
# CORS
# ==========================================

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        (
            "http://localhost:5173,"
            "http://127.0.0.1:5173"
        ),
    ).split(",")
    if origin.strip()
]


# ==========================================
# CSRF
# ==========================================

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "",
    ).split(",")
    if origin.strip()
]


if RENDER_EXTERNAL_HOSTNAME:
    render_origin = (
        "https://"
        + RENDER_EXTERNAL_HOSTNAME
    )

    if (
        render_origin
        not in CSRF_TRUSTED_ORIGINS
    ):
        CSRF_TRUSTED_ORIGINS.append(
            render_origin
        )


# ==========================================
# TOKEN DE AUTENTICACIÓN
# ==========================================

TOKEN_EXPIRATION_HOURS = int(
    os.getenv(
        "TOKEN_EXPIRATION_HOURS",
        "8",
    )
)


# ==========================================
# DJANGO REST FRAMEWORK
# ==========================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        (
            "cotizador.authentication."
            "ExpiringTokenAuthentication"
        ),
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        (
            "cotizador.permissions."
            "EsUsuarioAutorizado"
        ),
    ],

    "DEFAULT_THROTTLE_RATES": {
        "login":
            "5/minute",
    },
}


# ==========================================
# SEGURIDAD HTTP
# ==========================================

X_FRAME_OPTIONS = (
    "DENY"
)

SECURE_CONTENT_TYPE_NOSNIFF = (
    True
)

SESSION_COOKIE_HTTPONLY = (
    True
)

CSRF_COOKIE_HTTPONLY = (
    True
)


# ==========================================
# CONFIGURACIÓN DE PRODUCCIÓN
# ==========================================

if not DEBUG:
    # Render funciona detrás de un proxy
    # HTTPS. Esto permite que Django
    # reconozca correctamente la conexión.
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = (
        True
    )

    SESSION_COOKIE_SECURE = (
        True
    )

    CSRF_COOKIE_SECURE = (
        True
    )

    SECURE_HSTS_SECONDS = (
        31536000
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        True
    )

    SECURE_HSTS_PRELOAD = (
        True
    )