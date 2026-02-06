# Copyright 2024 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman. If not, see <http://www.gnu.org/licenses/>

"""
Client certificate authentication middleware.

Extracts client certificate information from headers set by the web server
(nginx, Apache, Caddy, etc.) and makes it available on the request object.
"""

from django.conf import settings
from django.http import JsonResponse


class ClientCertMiddleware:
    """Extract and validate client certificate from headers."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.require_cert = settings.REQUIRE_CLIENT_CERT
        self.cn_header = settings.CLIENT_CERT_CN_HEADER
        self.verify_header = settings.CLIENT_CERT_VERIFY_HEADER
        self.strict_hostname = settings.CLIENT_CERT_STRICT_HOSTNAME
        self.protected_paths = settings.CLIENT_CERT_PROTECTED_PATHS

    def __call__(self, request):
        # Extract cert info from headers (set by web server)
        request.client_cert_cn = request.META.get(self.cn_header, '')
        verify_status = request.META.get(self.verify_header, '')
        request.client_cert_verified = verify_status in ('SUCCESS', 'NONE')

        # Check if this path requires client cert
        if self.require_cert:
            for path in self.protected_paths:
                if request.path.startswith(path):
                    if not request.client_cert_verified or not request.client_cert_cn:
                        return JsonResponse(
                            {'error': 'Valid client certificate required'},
                            status=401,
                        )
                    break

        return self.get_response(request)

    def _is_protected_path(self, path):
        """Check if path requires client certificate."""
        for protected in self.protected_paths:
            if path.startswith(protected):
                return True
        return False
