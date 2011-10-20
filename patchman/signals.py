from django.dispatch import Signal

progress_info = Signal(providing_args=["ptext", "plength"])
progress_update = Signal(providing_args=["index"])
cli_message = Signal(providing_args=["text"])

