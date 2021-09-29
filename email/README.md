Configuration:
-----------------
$ mv patchman-email /usr/bin

$ mv patchman-email.conf /etc/patchman

$ chmod +x /usr/bin/patchman-email

Edit the configuration file and add more domains and recipients to fit your needs.

Make sure Postfix is up and running.

Usage:
----------------
patchman-email [-a] [-H hostname] [-T tag] [-h]

-a: E-mails all recipients with available updates

-H hostname: E-mails recipient with all available updates for given host

-T tag: E-mails recipient with all available updates for given tag

-h: Shows this help message and exits


For best effect, add a Cron job.
