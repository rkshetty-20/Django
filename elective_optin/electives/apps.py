from django.apps import AppConfig


class ElectivesConfig(AppConfig):
    name = 'electives'

    def ready(self):
        import electives.signals  # noqa: F401 — registers post_delete signal
