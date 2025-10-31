# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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


from datetime import datetime

from patchman.signals import (
    debug_message_s, error_message_s, info_message_s, warning_message_s,
)


def info_message(text):
    ts = datetime.now()
    info_message_s.send(sender=None, text=text, ts=ts)


def warning_message(text):
    ts = datetime.now()
    warning_message_s.send(sender=None, text=text, ts=ts)


def debug_message(text):
    ts = datetime.now()
    debug_message_s.send(sender=None, text=text, ts=ts)


def error_message(text):
    ts = datetime.now()
    error_message_s.send(sender=None, text=text, ts=ts)
