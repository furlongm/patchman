from django.dispatch import Signal

report_processed = Signal(providing_args=["report"])
package_processed = Signal(providing_args=["package"])
repo_processed = Signal(providing_args=["repo"])

