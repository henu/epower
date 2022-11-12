SECRET_KEY = '{{ django_secret_key }}'

DEBUG = False

ALLOWED_HOSTS = [
    '*',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'epower',
        'USER': 'epower',
        'PASSWORD': '{{ mysql_password }}',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

STATIC_ROOT = '/home/epower/epower/static_cached'
STATIC_URL = '/static/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'errors': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/home/epower/epower/logs/errors.log',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['errors'],
            'level': 'WARNING',
            'propagate': True,
        },
        'epower': {
            'handlers': ['errors'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}