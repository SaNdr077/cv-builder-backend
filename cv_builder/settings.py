import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-w^+q)wit8e$5+or^q*x^^@#lz+c+cne$jr7+s5-ze$==m4e^t&')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['cvgener.com', 'www.cvgener.com', 'cv-builder-backend-production-eb89.up.railway.app', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'rest_framework',
    'corsheaders',
    'cv',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS-ის კონფიგურაცია (კითხულობს მნიშვნელობებს image_78ba99.png-დან)
cors_env = os.getenv("CORS_ALLOWED_ORIGINS")
if cors_env:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_env.split(",")]
else:
    CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "https://cvgener.com"]

# CSRF-ის კონფიგურაცია
csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS")
if csrf_env:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_env.split(",")]
else:
    # თუ ცალკე CSRF ცვლადი არ გაქვს, ავტომატურად იყენებს CORS-ის სიას
    CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
    }
}

ROOT_URLCONF = 'cv_builder.urls'
GEOIP_PATH = os.path.join(BASE_DIR, 'geoip')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'cv_builder.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'