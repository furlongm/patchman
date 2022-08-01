Usage:
----------------
patchman-email [-a] [-H hostname] [-T tag] [-h]

-a: E-mails all recipients with available updates

-H hostname: E-mails recipient with all available updates for given host

-T tag: E-mails recipient with all available updates for given tag

-h: Shows this help message and exits


Setup:
-----------------
$ mv email/patchman-email /usr/bin

$ mv etc/patchman/patchman-email.conf /etc/patchman

$ chmod +x /usr/bin/patchman-email

Open the configuration file and edit the parameters to fit your needs.


Dependencies:
-----------------
- Patchman configured with MySQL

- Postfix configured and running

- GNU coreutils and sharutils installed

- Package uuid-runtime installed on Debian-based distributions
