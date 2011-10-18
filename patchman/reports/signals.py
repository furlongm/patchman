from django.dispatch import Signal

report_processed = Signal(providing_args=["report"])
numpackages = Signal(providing_args=["host", "numpackages"])
numrepos = Signal(providing_args=["host", "numrepos"])
package_processed = Signal(providing_args=["index"])
repo_processed = Signal(providing_args=["index"])

