from celery import Celery

def make_celery(app_name=__name__):
    """
    Create a configured Celery instance.
    
    Args:
        app_name: Name of the application (default to current module name)
        
    Returns:
        Celery application instance
    """
    # Redis URL: redis://result_backend_password@hostname:port/db_number
    # Standard local Redis is just "redis://localhost:6379/0"
    REDIS_URL = "redis://localhost:6379/0"

    celery = Celery(
        app_name,
        backend=REDIS_URL,
        broker=REDIS_URL,
        include=['tasks']  # Tell Celery where to find your tasks!
    )

    # Optional configuration updates
    celery.conf.update(
        result_expires=3600,  # Results expire after 1 hour
    )

    return celery

# Create a default instance for easy import
celery_app = make_celery("goodreads_scraper")
