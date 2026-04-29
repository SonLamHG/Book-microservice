import os
from pathlib import Path

# PyMySQL acts as a drop-in MySQLdb replacement so we don't need to
# install mysqlclient (which requires native libs in the slim image).
import pymysql
pymysql.version_info = (1, 4, 0, "final", 0)  # satisfy Django's MySQLdb version check
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'dev-secret-key-auth-service'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'app',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'auth_service.urls'
WSGI_APPLICATION = 'auth_service.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'auth_db'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'bookstore-mysql'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

JWT_SECRET = 'bookstore-jwt-secret-key-2026'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
