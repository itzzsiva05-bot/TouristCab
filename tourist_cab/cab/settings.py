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

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')




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
#  SITE CONFIG
# ─────────────────────────────────────────────
SITE_URL       = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')
ADMIN_WHATSAPP = os.environ.get('ADMIN_WHATSAPP', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'