from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _seed_after_migrate(sender, **kwargs):
    from .services import ensure_seed_data
    ensure_seed_data(reset=False)


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'EmpowerED OBE Analytics v2.0'

    def ready(self):
        post_migrate.connect(_seed_after_migrate, sender=self)

