"""
Production settings for the travel portal.

Extends the development settings with environment-driven
configuration. Nothing is activated implicitly: production
behaviour is controlled exclusively by environment variables
so that the development setup keeps working untouched.

Required in production:

    DJANGO_SETTINGS_MODULE=config.settings_production
    DJANGO_SECRET_KEY=<50+ random characters>
    DJANGO_ALLOWED_HOSTS=portal.example.com

Optional:

    DJANGO_DEBUG=1                # only for troubleshooting
    DJANGO_CORS_ALLOWED_ORIGINS=https://portal.example.com
    DJANGO_SQLITE_PATH=/var/lib/travel-portal/db.sqlite3
"""

import os

from .settings import *  # noqa: F401,F403

# ----------------------------------------------------------
# Security
# ----------------------------------------------------------

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-CHANGE-ME-production-secret-key",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "") == "1"

_ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "",
)

ALLOWED_HOSTS = [
    host.strip()
    for host in _ALLOWED_HOSTS.split(",")
    if host.strip()
]

if not ALLOWED_HOSTS:
    raise RuntimeError(
        "DJANGO_ALLOWED_HOSTS must be set in production "
        "(comma-separated host names)."
    )

# ----------------------------------------------------------
# HTTPS / transport security (enabled unless DJANGO_DEBUG=1)
# ----------------------------------------------------------

if not DEBUG:

    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

# ----------------------------------------------------------
# CORS (frontend origin(s))
# ----------------------------------------------------------

_CORS_ORIGINS = os.environ.get(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "",
)

if _CORS_ORIGINS:

    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in _CORS_ORIGINS.split(",")
        if origin.strip()
    ]

# ----------------------------------------------------------
# Database
#
# SQLite is kept by design (master specification: do not
# switch to PostgreSQL automatically). The file path is
# configurable so the database can live on persistent
# storage and be included in backups.
# ----------------------------------------------------------

_SQLITE_PATH = os.environ.get(
    "DJANGO_SQLITE_PATH",
    str(BASE_DIR / "db.sqlite3"),
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _SQLITE_PATH,
    }
}

# ----------------------------------------------------------
# Static & media files
# ----------------------------------------------------------

STATIC_ROOT = os.environ.get(
    "DJANGO_STATIC_ROOT",
    str(BASE_DIR / "staticfiles"),
)

MEDIA_ROOT = os.environ.get(
    "DJANGO_MEDIA_ROOT",
    str(BASE_DIR / "media"),
)

# ----------------------------------------------------------
# Logging
#
# Console logging at INFO keeps deployment log aggregation
# simple; errors additionally go to a dedicated file.
# ----------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": (
                "{levelname} {asctime} {name} "
                "{message}"
            ),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.environ.get(
                "DJANGO_ERROR_LOG_PATH",
                str(BASE_DIR / "django-error.log"),
            ),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "standard",
            "delay": True,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get(
            "DJANGO_LOG_LEVEL", "INFO"
        ),
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
