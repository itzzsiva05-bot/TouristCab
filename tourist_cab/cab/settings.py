"""
Django settings for cab project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────
#  SECURITY
# ─────────────────────────────────────────────
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY is not set. Add it to your .env file.")

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['touristcab.onrender.com', '127.0.0.1', 'localhost']

# Django's SecurityMiddleware sends "Cross-Origin-Opener-Policy: same-origin"
# by default, which breaks Google Sign-In's popup flow (window.opener becomes
# null, so it can't postMessage the result back). "same-origin-allow-popups"
# keeps the isolation benefit but still lets popups you open talk back to you.
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"




# ─────────────────────────────────────────────
#  APPLICATIONS
# ─────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'bookings',
    'drivers',
    'driverpanel',
    'adminpanel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cab.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cab.wsgi.application'


# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ─────────────────────────────────────────────
#  PASSWORD VALIDATION
# ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─────────────────────────────────────────────
#  INTERNATIONALISATION
# ─────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# ─────────────────────────────────────────────
#  STATIC & MEDIA FILES
# ─────────────────────────────────────────────
STATIC_URL  = 'static/'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

# ─────────────────────────────────────────────
#  GOOGLE MAPS
# ─────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
if not GOOGLE_MAPS_API_KEY:
    import warnings
    warnings.warn("GOOGLE_MAPS_API_KEY is not set. Maps will not work.")


# ─────────────────────────────────────────────
#  GOOGLE SIGN-IN (customer login)
# ─────────────────────────────────────────────
# Get this from https://console.cloud.google.com/apis/credentials
# (OAuth 2.0 Client ID -> Web application -> add http://127.0.0.1:8000 as an
# authorized JavaScript origin). Paste the Client ID into .env as GOOGLE_CLIENT_ID.
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')


# ─────────────────────────────────────────────
#  WHATSAPP - Meta Cloud API
# ─────────────────────────────────────────────
META_WHATSAPP_TOKEN  = os.environ.get('META_WHATSAPP_TOKEN', '')
META_PHONE_NUMBER_ID = os.environ.get('META_PHONE_NUMBER_ID', '')
META_WABA_VERSION    = os.environ.get('META_WABA_VERSION', 'v20.0')

if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
    import warnings
    warnings.warn("META_WHATSAPP_TOKEN or META_PHONE_NUMBER_ID is not set. WhatsApp will not work.")

# WhatsApp Message Template Names
META_TEMPLATE_OTP                = os.environ.get('META_TEMPLATE_OTP',                'otp_verification')
META_TEMPLATE_DRIVER_REQUEST     = os.environ.get('META_TEMPLATE_DRIVER_REQUEST',     'driver_request')
META_TEMPLATE_CUSTOMER_CONFIRMED = os.environ.get('META_TEMPLATE_CUSTOMER_CONFIRMED', 'customer_confirmed')
META_TEMPLATE_DRIVER_WELCOME     = os.environ.get('META_TEMPLATE_DRIVER_WELCOME',     'driver_welcome')


# ─────────────────────────────────────────────
#  EMAIL (SMTP) — used for customer OTP verification
# ─────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT          = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = f"TouristCab <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else None
# Without this, a slow/unreachable SMTP server can hang the whole request
# (and the "Send OTP" button) indefinitely instead of failing with an error.
EMAIL_TIMEOUT       = 15

if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    warnings.warn("EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is not set. Email OTP will not work.")


# ─────────────────────────────────────────────
#  SITE CONFIG
# ─────────────────────────────────────────────
SITE_URL       = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')
ADMIN_WHATSAPP = os.environ.get('ADMIN_WHATSAPP', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = 'static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'
