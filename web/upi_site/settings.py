"""
Settings for the UPI Scam & Mule Detection website.

No database is needed: the current dataset and threshold choices live in a
signed cookie, uploaded CSVs are saved in web/uploads/, and results are cached
in memory.
"""

import os
import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent.parent          # .../Pbl.2/web
PROJECT_ROOT = WEB_DIR.parent                              # .../Pbl.2
APP_CODE_DIR = PROJECT_ROOT / "fraud_detection_app"        # model + scoring code
sys.path.insert(0, str(APP_CODE_DIR))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-dev-only-key-change-me-for-any-deployment")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", ".onrender.com"]
# Extra hosts (e.g. a custom domain) can be added with DJANGO_ALLOWED_HOSTS="a.com,b.com"
ALLOWED_HOSTS += [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"] + [
    f"https://{h.strip()}" for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

if not DEBUG:
    # Running online: refuse to start with the development key, and use HTTPS-only cookies.
    if SECRET_KEY.startswith("local-dev-only"):
        raise RuntimeError("Set DJANGO_SECRET_KEY before running with DJANGO_DEBUG=0")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

INSTALLED_APPS = [
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "upi_site.urls"
WSGI_APPLICATION = "upi_site.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.messages.context_processors.messages",
        "dashboard.context.current_dataset",
    ]},
}]

DATABASES = {}
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True

UPLOAD_DIR = WEB_DIR / "uploads"
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

STATIC_URL = "static/"
USE_TZ = False
LANGUAGE_CODE = "en-in"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Charts produced by train_and_evaluate.py are served from /static/results/...
STATICFILES_DIRS = [("results", PROJECT_ROOT / "results")]

# No database is used; silence checks for the unused default auto field.
SILENCED_SYSTEM_CHECKS = ["models.W042"]
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

# Static files are served by WhiteNoise (works locally and online, no extra server needed).
STATIC_ROOT = WEB_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
