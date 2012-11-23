# Copyright 2012 VPAC, http://www.vpac.org
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

from django.dispatch import Signal

progress_info_s = Signal(providing_args=['ptext', 'plength'])
progress_update_s = Signal(providing_args=['index'])
info_message = Signal(providing_args=['text'])
error_message = Signal(providing_args=['text'])
debug_message = Signal(providing_args=['text'])
