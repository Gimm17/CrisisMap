from celery import Celery

celery_app = Celery("crisismap")
celery_app.conf.broker_url = "redis://redis:6379/0"
celery_app.conf.result_backend = "redis://redis:6379/1"
