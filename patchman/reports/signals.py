from django.dispatch import Signal

report_processed = Signal(providing_args=["report"])

