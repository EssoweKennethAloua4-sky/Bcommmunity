import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Chargement automatique du fichier .env s'il existe
for _env_fichier in (BASE_DIR.parent / ".env", BASE_DIR / ".env"):
    if _env_fichier.is_file():
        try:
            with open(_env_fichier, "r", encoding="utf-8") as _f:
                for _ligne in _f:
                    _ligne = _ligne.strip()
                    if _ligne and not _ligne.startswith("#") and "=" in _ligne:
                        _cle, _, _val = _ligne.partition("=")
                        _cle, _val = _cle.strip(), _val.strip().strip("'\"")
                        if _cle and _cle not in os.environ:
                            os.environ[_cle] = _val
            break
        except OSError:
            pass


def env(nom, defaut=None, requis=False):
    valeur = os.environ.get(nom, defaut)
    if requis and valeur in (None, ""):
        raise RuntimeError(f"Variable d'environnement manquante : {nom}")
    return valeur


DEBUG = env("DJANGO_DEBUG", "0") == "1"
DEV_OTP_CODE = "123456" if DEBUG else None
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key" if DEBUG else None, requis=True)
ALLOWED_HOSTS = [h for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
ADMIN_URL = env("ADMIN_URL", "admin/")
TRUSTED_PROXY_IPS = [
    ip.strip() for ip in env("TRUSTED_PROXY_IPS", "").split(",") if ip.strip()
]

INSTALLED_APPS = [
    # Daphne doit etre en premiere position pour les WebSockets ASGI
    "daphne",
    "unfold",
    "cloudinary_storage",
    "cloudinary",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "channels",
    "comptes",
    "profils",
    "scolarite",
    "amis",
    "publications",
    "discussions",
    "notifications",
    "signalements",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [__import__("pathlib").Path(__file__).resolve().parent.parent / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

# --- Base de donnees (Neon PostgreSQL en production, SQLite en dev) ---
DATABASES = {"default": dj_database_url.parse(
    env("DATABASE_URL", "sqlite:///db.sqlite3" if DEBUG else None, requis=not DEBUG),
    conn_max_age=60, conn_health_checks=True)}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# Obligatoire avec le pooler PgBouncer de Neon (mode transaction)
if "postgresql" in DATABASES["default"].get("ENGINE", ""):
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 15
elif "sqlite" in DATABASES["default"].get("ENGINE", ""):
    DATABASES["default"].setdefault("OPTIONS", {})["timeout"] = 30


# --- Configuration SQLite WAL pour éviter les blocages concurrents ---
from django.db.backends.signals import connection_created  # noqa: E402
from django.dispatch import receiver  # noqa: E402


@receiver(connection_created)
def _configurer_sqlite_wal(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")

# --- Django Channels + Redis ---
REDIS_URL = env("REDIS_URL", "").strip()
if "pytest" in sys.modules or not REDIS_URL:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
else:
    CHANNEL_LAYERS = {"default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": 1500,
            "expiry": 10,
        },
    }}

CACHES = {"default": {
    "BACKEND": "django_redis.cache.RedisCache" if REDIS_URL else "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": REDIS_URL if REDIS_URL else "bakhita-cache",
    "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"} if REDIS_URL else {},
    "KEY_PREFIX": "bakhita",
}}

AUTH_USER_MODEL = "comptes.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
SITE_URL = env("SITE_URL", "http://localhost:5173")

# --- Stockage des media : Cloudinary si configure, disque local sinon ---
CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET", "")

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
}

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    import cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/"
    MEDIA_ROOT = BASE_DIR / "media"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# Securite
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 26_214_400
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
if not DEBUG:
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT", "1") == "1"
    SECURE_REDIRECT_EXEMPT = [r"^api/vivant/$", r"^api/sante/$"]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

CORS_ALLOWED_ORIGINS = [o for o in env("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [o for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
REFRESH_COOKIE_SAMESITE = env("REFRESH_COOKIE_SAMESITE", "Lax")

# Google & Email
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", "")
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173")
PASSWORD_RESET_TIMEOUT = 3600

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend" if DEBUG
                    else "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Bakhita Community <no-reply@bakhita.example>")
ADMIN_EMAIL = env("ADMIN_EMAIL", "")  # adresse historique, conservée pour compatibilité
ADMIN_EMAILS = [
    adresse.strip() for adresse in env("ADMIN_EMAILS", ADMIN_EMAIL).split(",") if adresse.strip()
]
SEUIL_ALERTES_ADMIN = int(env("SEUIL_ALERTES_ADMIN", "10"))
if SEUIL_ALERTES_ADMIN < 1:
    raise RuntimeError("SEUIL_ALERTES_ADMIN doit être supérieur ou égal à 1.")
SEUIL_MASQUAGE_AUTO = int(env("SEUIL_MASQUAGE_AUTO", "3"))

# --- Brevo SMTP (actif uniquement si BREVO_SMTP_LOGIN est défini) ---
BREVO_SMTP_LOGIN = env("BREVO_SMTP_LOGIN", "")
BREVO_SMTP_PASSWORD = env("BREVO_SMTP_PASSWORD", "")
BREVO_API_KEY = env("BREVO_API_KEY", "")
if BREVO_SMTP_LOGIN:
    EMAIL_HOST = "smtp-relay.brevo.com"
    EMAIL_PORT = 587
    EMAIL_HOST_USER = BREVO_SMTP_LOGIN
    EMAIL_HOST_PASSWORD = BREVO_SMTP_PASSWORD
    EMAIL_USE_TLS = True
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["comptes.auth.ReseauJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "comptes.permissions.PasLectureSeule",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min", "user": "240/min",
        "inscription": "5/hour", "connexion": "60/min", "rafraichir": "180/min",
        "reset": "5/hour", "google": "20/min", "demande_ami": "30/hour",
        "publier": "20/hour", "commenter": "60/hour", "like": "120/min", "photo": "10/hour",
        "invitation": "20/hour", "message": "120/min",
        "push": "20/hour",
        "push_reply": "20/min",
        "signalement": "10/hour",
        "otp_envoyer": "3/hour",
        "otp_verifier": "10/hour",
        "link_preview": "30/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

if "sqlite" in DATABASES["default"].get("ENGINE", ""):
    # SQLite's single-writer locking makes concurrent refresh-token rotation unreliable.
    SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] = False
    SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] = False

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ---- Celery ----
from celery.schedules import crontab  # noqa: E402

CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_TASK_ALWAYS_EAGER = env("CELERY_EAGER", "0") == "1" or "pytest" in sys.modules
CELERY_TASK_SOFT_TIME_LIMIT = 120
CELERY_TASK_TIME_LIMIT = 150
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULE = {
    "publications-programmees": {
        "task": "publications.taches.publier_programmees",
        "schedule": crontab(minute="*"),
    },
    "resume-quotidien": {
        "task": "notifications.taches.resume_quotidien",
        "schedule": crontab(hour=int(env("RESUME_HEURE_UTC", "17")), minute=0),
    },
    "nettoyage": {
        "task": "notifications.taches.nettoyer",
        "schedule": crontab(hour=3, minute=30),
    },
    "suspensions": {
        "task": "comptes.taches.lever_suspensions_expirees",
        "schedule": crontab(minute="*/5"),
    },
    "rapport-hebdomadaire": {
        "task": "comptes.taches.envoyer_rapport_hebdomadaire",
        "schedule": crontab(day_of_week="monday", hour=8, minute=0),
    },
}

# ---- Push (VAPID + FCM) ----
VAPID_PUBLIC_KEY    = env("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY   = env("VAPID_PRIVATE_KEY", "")
VAPID_ADMIN_EMAIL   = env("VAPID_ADMIN_EMAIL", "admin@bakhita.example")
FCM_SERVICE_ACCOUNT_JSON = env("FCM_SERVICE_ACCOUNT_JSON", "")
ONESIGNAL_APP_ID = env("ONESIGNAL_APP_ID", "")
ONESIGNAL_REST_API_KEY = env("ONESIGNAL_REST_API_KEY", "")

# ---- Google & CORS (M7 Natif & PWA) ----
from corsheaders.defaults import default_headers  # noqa: E402

GOOGLE_CLIENT_IDS = [c for c in env("GOOGLE_CLIENT_IDS", env("GOOGLE_CLIENT_ID", "")).split(",") if c]
CORS_ALLOW_HEADERS = (*default_headers, "x-client")
CORS_ALLOWED_ORIGINS = [
    o for o in env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://localhost,capacitor://localhost"
    ).split(",") if o
]
CORS_ALLOW_CREDENTIALS = True


# --- Interface d'administration (Unfold) ---
from django.urls import reverse_lazy  # noqa: E402


def _lien(nom):
    return reverse_lazy(f"admin:{nom}_changelist")


def _permission(code):
    app, codename = code.split(".", 1)
    modification = f"{app}.change_{codename[5:]}" if codename.startswith("view_") else None
    return lambda request: request.user.has_perm(code) or (
        modification is not None and request.user.has_perm(modification)
    )


UNFOLD = {
    "SITE_TITLE": "Bakhita Community",
    "SITE_HEADER": "Bakhita Community",
    "SITE_SYMBOL": "school",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "href": f"{STATIC_URL}comptes/admin/favicon.svg",
            "type": "image/svg+xml",
        },
    ],
    "DASHBOARD_CALLBACK": "comptes.tableau_de_bord.contexte",
    "COLORS": {
        "primary": {
            "50": "oklch(98% 0.016 73.684)",
            "100": "oklch(95.4% 0.038 75.164)",
            "200": "oklch(90.1% 0.076 70.697)",
            "300": "oklch(83.7% 0.128 66.29)",
            "400": "oklch(75% 0.183 55.934)",
            "500": "oklch(70.5% 0.213 47.604)",
            "600": "oklch(64.6% 0.222 41.116)",
            "700": "oklch(55.3% 0.195 38.402)",
            "800": "oklch(47% 0.157 37.304)",
            "900": "oklch(40.8% 0.123 38.172)",
            "950": "oklch(26.6% 0.079 36.259)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Membres",
                "separator": True,
                "items": [
                    {"title": "Comptes", "icon": "group", "link": _lien("comptes_user"),
                     "permission": _permission("comptes.view_user")},
                    {"title": "Profils", "icon": "badge", "link": _lien("profils_profil"),
                     "permission": _permission("profils.view_profil")},
                    {"title": "Bons d'anniversaire", "icon": "redeem",
                     "link": _lien("profils_cadeauanniversaire"),
                     "permission": _permission("profils.view_cadeauanniversaire")},
                    {"title": "Groupes", "icon": "groups", "link": _lien("auth_group"),
                     "permission": _permission("auth.view_group")},
                ],
            },
            {
                "title": "Modération",
                "separator": True,
                "items": [
                    {"title": "Signalements", "icon": "flag", "link": _lien("signalements_signalement"),
                     "permission": _permission("signalements.view_signalement")},
                    {"title": "Bouton de support", "icon": "support_agent",
                     "link": _lien("signalements_configurationsupport"),
                     "permission": _permission("signalements.view_configurationsupport")},
                    {"title": "Suspensions", "icon": "gavel", "link": _lien("comptes_suspension"),
                     "permission": _permission("comptes.view_suspension")},
                    {"title": "Journal d'activité", "icon": "history", "link": _lien("comptes_activite"),
                     "permission": _permission("comptes.view_activite")},
                ],
            },
            {
                "title": "Contenu",
                "separator": True,
                "items": [
                    {"title": "Publications", "icon": "article", "link": _lien("publications_publication"),
                     "permission": _permission("publications.view_publication")},
                    {"title": "Commentaires", "icon": "chat", "link": _lien("publications_commentaire"),
                     "permission": _permission("publications.view_commentaire")},
                ],
            },
            {
                "title": "Scolarité",
                "separator": True,
                "items": [
                    {"title": "Cycles", "icon": "layers", "link": _lien("scolarite_cycle"),
                     "permission": _permission("scolarite.view_cycle")},
                    {"title": "Classes", "icon": "class", "link": _lien("scolarite_classe"),
                     "permission": _permission("scolarite.view_classe")},
                    {"title": "Parcours des membres", "icon": "history_edu", "link": _lien("scolarite_scolarite"),
                     "permission": _permission("scolarite.view_scolarite")},
                    {"title": "Domaines d'études", "icon": "science", "link": _lien("profils_domaine"),
                     "permission": _permission("profils.view_domaine")},
                ],
            },
            {
                "title": "Sécurité",
                "separator": True,
                "items": [
                    {"title": "Sessions actives", "icon": "key", "link": _lien("token_blacklist_outstandingtoken"),
                     "permission": _permission("token_blacklist.view_outstandingtoken")},
                    {"title": "Sessions révoquées", "icon": "block", "link": _lien("token_blacklist_blacklistedtoken"),
                     "permission": _permission("token_blacklist.view_blacklistedtoken")},
                ],
            },
        ],
    },
}
