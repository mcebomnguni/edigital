from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core Module'

    def ready(self):
        """
        Hook that is called when the app is fully loaded.
        Good place to register signals, schedulers, or perform health checks.
        """
        try:
            # Import signals or startup modules
            import core.signals  # Ensure signal handlers are registered

            # Optional: log app startup
            logger.info("Core app is ready and signals are loaded.")

        except ImportError as e:
            logger.warning(f"Core app startup encountered import error: {e}")
        except Exception as e:
            logger.exception("Unexpected error during Core app initialization.")
