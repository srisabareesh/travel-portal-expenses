from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        ##Register the legacy-role synchronization signals.
        from . import signals  # noqa: F401
