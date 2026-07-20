from .base import *  # noqa: F401,F403

DEBUG = True
INSTALLED_APPS += ["django_extensions"]  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
RAW_STORAGE_BACKEND = "local"
SUBMISSION_INBOX = "dev@localhost"
