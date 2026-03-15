from django.apps import AppConfig


class RestfullConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restfull'

    def ready(self):
        import restfull.schema  # noqa: E402