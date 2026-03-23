import os
from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            from app.messaging import start_consumer
            from app.consumers import BINDINGS
            start_consumer('cart-service', BINDINGS)
