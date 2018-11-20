
Configuration:
-----------------
Copy the script to the desired location (e.g. /usr/local/bin)

$ chmod +x updatereport.sh

$ mkdir /usr/local/patchman/ /usr/local/patchman/email/

Edit the script and change the e-mail recipient located at line 15. Add more constants to the CASE block if you need different recipients for different domains

Make sure Postfix is up and running.

Usage:
----------------
$ ./updatereport.sh all
or
$ ./updatereport.sh hostname


For best effect, add a Cron job. This script doesn't process reports sent to the server, it only e-mails a list of available updates for each host.
