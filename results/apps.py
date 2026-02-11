from django.apps import AppConfig


class ResultsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'results'
    verbose_name = 'Results Management'
    
    def ready(self):
        # Import signals
        import results.signals