from django.utils.datastructures import MultiValueDictKeyError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from datetime import datetime, date, time

from patchman.reports.models import Report

@csrf_exempt
def upload(request):

# TODO fix http://patchman.vpac.org/reports/upload/ to redirect or do something else
# TODO redirect 302 to report view if report is requested

    if request.method == 'POST':
        
        data = request.POST.copy()
        meta = request.META.copy()
        response = HttpResponse()

        report = Report.objects.create()
        report.parse(data, meta)

        if 'report' in data and data['report'] == '1':
            packages = []
            if 'pkgs' in data:
                for p in data['pkgs'].splitlines():
                    packages.append(p.replace('\'','').split(' '))
            return render_to_response('reports/report.txt', {'data':data, 'packages':packages}, context_instance=RequestContext(request), mimetype='text/plain')

        response.status=302
        return response
