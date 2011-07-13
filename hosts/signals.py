from django.dispatch import Signal

host_update_found = Signal(providing_args=["update"])

