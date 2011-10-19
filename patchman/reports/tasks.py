try:
    from celery.decorators import task

    @task()
    def process_report(report):
        report.process()
except ImportError:
    def process_report(report):
        pass
