"""Django settings for the Astroum AI / BRAHMO assessment backend.

Database defaults mirror the brief: mysql, 127.0.0.1:3306, astroum_ai_db, root.
Every value can be overridden by environment variable or backend/.env.
Thresholds live in BRAHMO below so no check path hardcodes them.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
DATA_DIR = Path(os.environ.get("BRAHMO_DATA_DIR", REPO_ROOT / "data"))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-for-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "brahmo",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DB_CONNECTION = os.environ.get("DB_CONNECTION", "mysql")
if DB_CONNECTION != "mysql":
    raise RuntimeError("This project is configured for MySQL only (DB_CONNECTION=mysql).")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_DATABASE", "astroum_ai_db"),
        "USER": os.environ.get("DB_USERNAME", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "123456789"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        # utf8mb4: the pharmacy stock file contains Telugu billing strings.
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "brahmo.exceptions.handler",
    # No auth in this scaffold: read endpoints serve public/synthetic data.
    # Write endpoints (gap resolution) are unauthenticated and must be gated before any real use.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Config-driven thresholds and classification inputs.
BRAHMO = {
    "STOCK_EXPIRY_WARN_DAYS": int(os.environ.get("BRAHMO_EXPIRY_WARN_DAYS", "90")),
    # Ingredients whose CDCI strengths are expected in a unit other than mg.
    # A strength written as mg for these is logged as a UNIT_MISMATCH_SUSPECTED anomaly.
    "STRENGTH_UNIT_OVERRIDES": {"Thyroxine": "mcg"},
    "SEVERITY_VALUES": ["SEVERE", "MODERATE", "MILD"],
    "REGULATORY_ACTIONS": ["PROHIBITED", "RESTRICTED", "WITHDRAWN", "STAY_GRANTED"],
    "REGULATORY_TARGET_TYPES": ["FDC", "INGREDIENT", "PRODUCT"],
    # Rail: documented daily ceilings per ingredient, each with its citation.
    "DAILY_MAX_MG": {
        "paracetamol": {"max_mg": 3000, "source": "STW-GP-01 v2025.1: max 3 g/day adult"},
    },
    "REGULATORY_SEVERITY": {"PROHIBITED": "HIGH", "WITHDRAWN": "HIGH", "RESTRICTED": "MODERATE"},
    # Duplicate-salt severity when the aggregate stays under its ceiling (HIGH is used when it exceeds).
    "DUPLICATE_SEVERITY": "MODERATE",
    # Q&A slice: retrieval thresholds and stopwords (no LLM anywhere in this path).
    "QA_MIN_DISTINCT_TERMS": 2,
    "QA_TOP_K": 6,
    "QA_CANDIDATE_LIMIT": 400,
    # A unit must cover at least this share of the question's content (non-generic) terms.
    "QA_MIN_CONTENT_COVERAGE": 0.5,
    # Generic words carry no clinical signal; they never count toward coverage.
    "QA_GENERIC_TERMS": [
        "first-line", "adult", "adults", "child", "management", "drug", "therapy", "treatment", "initial",
        "start", "started", "workflow", "pack", "label", "sources", "source", "national", "clinic",
        "protocol", "standard", "guidance", "regimen", "dose", "basis", "duration", "course", "volume",
        "aged", "class", "suspect", "suspected", "newly", "diagnosed", "threshold", "second", "agent",
        "alternative", "accompany", "accompanies", "exactly", "states", "stated", "must", "why",
        "first",
    ],
    # Lexical bridges from a question's word to words used in the workflow text.
    "QA_SYNONYMS": {
        "analgesic": ["nsaid", "ibuprofen", "diclofenac", "aspirin"],
        "antibiotic": ["amoxicillin", "azithromycin", "cefixime", "nitrofurantoin", "ciprofloxacin", "antibiotics"],
    },
    "QA_STOPWORDS": [
        "a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from", "how", "in", "is", "it",
        "of", "on", "or", "say", "says", "the", "to", "what", "when", "which", "who", "why", "with",
        "should", "must", "per", "that", "this", "their", "there", "exactly", "after", "each", "do",
        "does", "has", "have", "any", "given", "using", "where", "whether",
    ],
}
RAIL_RULE_VERSION = "rail/1.0.0"
QA_RULE_VERSION = "qa-lexical/1.0.0"
