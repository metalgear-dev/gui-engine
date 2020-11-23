"""
Django settings for gui project.

Generated by 'django-admin startproject' using Django 3.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import os
import datetime
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read env file
ENV = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
# Reading .env file
environ.Env.read_env(".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ENV('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ENV('DEBUG')

ALLOWED_HOSTS = [
    '*'
]


# Application definition

INSTALLED_APPS = [
    'environ',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'rest_framework',
    'django_rest_passwordreset',
    'corsheaders',
    'channels',
    'chat',
    'basics',
    'accounts',
    'calls',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gui.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gui.wsgi.application'
ASGI_APPLICATION = 'gui.asgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': ENV.db()
}


# Specify User Model
AUTH_USER_MODEL = 'accounts.Member'


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'ja-jp'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'

# Static files
if DEBUG:
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, "static"),
    ]
else:
    STATIC_ROOT = os.path.join(BASE_DIR, "static")


# REST framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
    ),
}


# CORS Policy Setting
CORS_ORIGIN_ALLOW_ALL = True


# JWT Authentication
JWT_AUTH = {
    'JWT_SECRET_KEY': SECRET_KEY,
    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=1),
    'JWT_ALLOW_REFRESH': True,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),
    'JWT_AUTH_HEADER_PREFIX': 'Bearer',
    'JWT_RESPONSE_PAYLOAD_HANDLER': 'accounts.payload.jwt_response_payload_handler',
}


# Django websocket redis channel
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(ENV('REDIS_HOST'), 6379)],
        },
    },
}


# Django resized
DJANGORESIZED_DEFAULT_QUALITY = 75
DJANGORESIZED_DEFAULT_KEEP_META = True
DJANGORESIZED_DEFAULT_FORCE_FORMAT = 'JPEG'
DJANGORESIZED_DEFAULT_FORMAT_EXTENSIONS = {'JPEG': ".jpg"}
DJANGORESIZED_DEFAULT_NORMALIZE_ROTATION = True


# Base URLs
SITE_URL = ENV('SITE_URL')
CLIENT_URL = ENV('CLIENT_URL')

# Email Settings
EMAIL_HOST = ENV('EMAIL_HOST')
EMAIL_PORT = ENV('EMAIL_PORT')
EMAIL_HOST_USER = ENV('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = ENV('EMAIL_HOST_PASSWORD')
EMAIL_FROM_USER = ENV('EMAIL_FROM_USER')
EMAIL_BACKEND = ENV('EMAIL_BACKEND')
EMAIL_USE_TLS = ENV('EMAIL_USE_TLS')

# LINE Settings
LINE_CLIENT_ID = ENV('LINE_CLIENT_ID')
LINE_CLIENT_SECRET = ENV('LINE_CLIENT_SECRET')
LINE_CHANNEL_SECRET = ENV('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = ENV('LINE_CHANNEL_ACCESS_TOKEN')

# Django reset password
DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME = 24
DJANGO_REST_MULTITOKENAUTH_REQUIRE_USABLE_PASSWORD = False

# Amazon setting
AWS_ACCESS_KEY_ID = ENV('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = ENV('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = ENV('AWS_STORAGE_BUCKET_NAME')
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
