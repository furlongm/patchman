from django.contrib.admin.models import LogEntry

logs = LogEntry.objects.all()

for log in logs:
    log.delete()
