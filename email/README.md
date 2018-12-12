Configuration:
-----------------
$ mv patchman-email /usr/bin

$ mv patchman-email.conf /etc/patchman

$ chmod +x /usr/bin/patchman-email

Edit the configuration file and add more domains and recipients to fit your needs.

Make sure Postfix is up and running.

Usage:
----------------
patchman-email [-h] [-a] [-H hostname]
-h: Shows this help message and exits
-a: E-mails the available updates to all recipients
-H hostname: E-mails the hostname's available updates to the recipient

For best effect, add a Cron job.
