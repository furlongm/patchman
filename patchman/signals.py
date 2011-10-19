from django.dispatch import Signal

progress_info = Signal(providing_args=["ptext", "plength"])
progress_update = Signal(providing_args=["index"])

