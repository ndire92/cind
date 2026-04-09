
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
DEBUG = True



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
    'django.contrib.sitemaps',
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
                'shop.context_processors.partners',
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


# Clés PayDunya Live

# MODE
PAYDUNYA_MODE = os.getenv("PAYDUNYA_MODE", "test")

# --- TEST KEYS ---
PAYDUNYA_MASTER_KEY_TEST = os.getenv("PAYDUNYA_MASTER_KEY_TEST")
PAYDUNYA_PUBLIC_KEY_TEST = os.getenv("PAYDUNYA_PUBLIC_KEY_TEST")
PAYDUNYA_PRIVATE_KEY_TEST = os.getenv("PAYDUNYA_PRIVATE_KEY_TEST")
PAYDUNYA_TOKEN_TEST = os.getenv("PAYDUNYA_TOKEN_TEST")

# --- LIVE KEYS ---
PAYDUNYA_MASTER_KEY = os.getenv("PAYDUNYA_MASTER_KEY")
PAYDUNYA_PUBLIC_KEY = os.getenv("PAYDUNYA_PUBLIC_KEY")
PAYDUNYA_PRIVATE_KEY = os.getenv("PAYDUNYA_PRIVATE_KEY")
PAYDUNYA_TOKEN = os.getenv("PAYDUNYA_TOKEN")

# URL
PAYDUNYA_URL = "https://app.paydunya.com/api/v1/checkout-invoice/create"

DEXPAY_PUBLIC_KEY = os.getenv("DEXPAY_PUBLIC_KEY")
DEXPAY_SECRET_KEY = os.getenv("DEXPAY_SECRET_KEY")

# Utiliser la clé publique pour initier les paiements
DEXPAY_API_KEY = DEXPAY_PUBLIC_KEY

DEXPAY_BASE_URL = "https://api.dexpay.africa/api/v1"


ADMIN_EMAIL = "info@cinderaproduitsnaturels.com"

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USE_SSL = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

