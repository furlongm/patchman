from django.conf import settings

if settings.USE_ASYNC_PROCESSING:
    from celery.decorators import task

    @task()
    def process_report(report):
        report.process()
