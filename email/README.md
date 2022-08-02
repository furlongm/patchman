Dependencies:
-----------------
- Patchman configured with MySQL

- Postfix configured and running

- GNU coreutils and sharutils installed

- Package uuid-runtime installed on Debian-based distributions


Setup:
-----------------
- Copy the files to the destination:
```
mv email/patchman-email /usr/bin

mv etc/patchman/patchman-email.conf /etc/patchman

chmod +x /usr/bin/patchman-email
```
- Edit `/etc/patchman/patchman-email.conf´ and change the parameters to fit your needs.

- Configure crontab with `scripts/patchman-email.sh` and modify the script to automate e-mail reports.


Usage:
----------------
```
patchman-email [-a] [-H hostname] [-T tag] [-h]

-a: E-mails all recipients with available updates

-H hostname: E-mails recipient with all available updates for given host

-T tag: E-mails recipient with all available updates for given tag

-h: Shows this help message and exits
```
