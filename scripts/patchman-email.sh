#!/bin/bash

LOGDIR="/var/log/patchman"

while [[ $(pgrep 'patchman -a') ]]; do 
	echo "$(date '+%d/%m/%Y %R') [INFO] Patchman running, sleeping for 30 minutes" >> $LOGDIR/patchman-email.log 
	sleep 1800
done

echo "$(date '+%d/%m/%Y %R') [INFO] Generating reports" >> $LOGDIR/patchman-email.log 

#patchman-email -a >> $LOGDIR/patchman-email.log
patchman-email -T tag >> $LOGDIR/tag.log
patchman-email -T tag2 >> $LOGDIR/tag2.log
patchman-email -T tag3 >> $LOGDIR/tag3.log
