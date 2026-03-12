
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-g8b&8g*t+#d0^rd6(yet4h@6_(=23k$m@leu-yqsl_8tsdf!cw'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "187.124.39.24",
    "cinderaproduitsnaturels.com",
    "www.cinderaproduitsnaturels.com",
    "localhost",
    "127.0.0.1"
]

CSRF_TRUSTED_ORIGINS = [
    "https://cinderaproduitsnaturels.com",
    "https://www.cinderaproduitsnaturels.com",
    "http://187.124.39.24"
]



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'shop',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
          # ... garde le reste tel quel ...
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        # ...
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.cart_item_count',
                'shop.context_processors.categories_context',
                'shop.context_processors.site_settings',# Ajoutez votre context processor ici
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

##DATABASES = {
 #   'default': {
 #       'ENGINE': 'django.db.backends.sqlite3',
  #      'NAME': BASE_DIR / 'db.sqlite3',
   # }
#}

import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cind_db',
        'USER': 'cind_user',
        'PASSWORD': 'cindera',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# 2. Configuration des Fichiers Statiques et Médias


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = "shop.User"
# Redirection après connexion (vers la boutique)
LOGIN_REDIRECT_URL = 'products:shop'

# Redirection après déconnexion
LOGOUT_REDIRECT_URL = 'products:shop'
# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

PAYDUNYA_MASTER_KEY = "IZ1pSWiK-ccuu-AlCs-OlZq-tGbJQCUfvZ4T"
PAYDUNYA_PUBLIC_KEY = "test_public_0nfRyIYUuyGhqp6pBpZHWV21rvd"
PAYDUNYA_PRIVATE_KEY = "test_private_eDBH4wr1vOhAJxh2jwiCr4GPDY8"
PAYDUNYA_TOKEN = "9CK96TxtYtKQSIf1mZoY"

#PAYDUNYA_MASTER_KEY = "IZ1pSWiK-ccuu-AlCs-OlZq-tGbJQCUfvZ4T"
#PAYDUNYA_PUBLIC_KEY = "live_public_lWc6uqOS1dVvJfTa21caESs0PM5"
#PAYDUNYA_PRIVATE_KEY = "live_private_2AQffmGv0EGsK2LPe9s5v7yj68U"
#PAYDUNYA_TOKEN = "78E9iiMRJ6D5G1Jwz54t"


# Mode de fonctionnement
DEXPAY_MODE = "TEST"  # ou "LIVE" en production

# Clés API Dexpay
DEXPAY_TEST_API_KEY = "pk_test_59f57230291f2a5da0c47edf960c3480"
DEXPAY_LIVE_API_KEY = "pk_live_353f413e1c51857667b8ba7190d7c5c8"

# URLs API
DEXPAY_TEST_BASE_URL = "https://api-sandbox.dexpay.africa"
DEXPAY_LIVE_BASE_URL = "https://api.dexpay.africa"

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USE_SSL = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

