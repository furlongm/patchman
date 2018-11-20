#!/bin/bash

report() {
    # Verifies if there are updates available for the host
    UPDATES="$(patchman -lh -H $1 | tail -n +3 | head -n -1 | awk 'NR==10' | awk -F ' : ' '{ print $2 }')"

    if [ $UPDATES -gt 0 ]; then
        DIR="/usr/local/patchman/email/"
        FILE=$DIR$1_`date +%Y%m%d`
        DOMAIN="$(patchman -lh -H $1 | tail -n +3 | head -n -1 | awk 'NR==3' | awk -F ' : ' '{ print $2 }')"

	# Chooses a recipient depending on the host's domain
        case $DOMAIN in
            *)
                RECIPIENT="test@test.com"
                ;;
        esac

	# Creates the report
        echo "<html>" > $FILE
        echo "<style>" >> $FILE
        echo "body { font-family: \"Calibri\"  }" >> $FILE
        echo "#details table { border-collapse: collapse; width: 20em; }" >> $FILE
        echo "#updates table { border-collapse: collapse; width: 100%; }" >> $FILE
        echo "#details th, #details tr, #details td { text-align: left; }" >> $FILE
        echo "#updates th, #updates td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }" >> $FILE
        echo "</style>" >> $FILE

        echo "<body>" >> $FILE
        echo "<p>There are new updates available for <b>$1</b>:</p><br>" >> $FILE

        echo "<div id=\"details\"><table>" >> $FILE
        patchman -lh -H $1 | tail -n +3 | head -n -1 | awk 'NR!=2 && NR!=7 && NR!=9 && NR!=11 && NR!=13 && NR!=14' | awk -F ' : ' '{ print "<tr><th>"$1":</th><td>"$2"</td></tr>" }' >> $FILE
        echo "</table></div><br>" >> $FILE

        echo "<div id=\"updates\"><table>" >> $FILE
        patchman -u -H $1 | tail -n +3 | head -n -1 | awk 'BEGIN { print "<tr><th>Current Version</th><th>New Version</th><th>Type</th></tr>" }
                                                                 { print "<tr><td>"$1"</td><td>"$3"</td><td>"$4"</td></tr>" }' >> $FILE
        echo "</table></div><br>" >> $FILE

        echo "<p>Please contact your System Administrator in order to schedule the updates.</p>" >> $FILE

        echo "</body>" >> $FILE
        echo "</html>" >> $FILE

        # E-mails the report
        mail -aContent-Type:text/html -s "[$1] Update Report" $RECIPIENT < $FILE

	echo "[$1] INFO: Report sent."
    else
        echo "[$1] INFO: There are no updates available."
    fi
}

if [ "$1" != "" ]; then
    # Checks if all hosts are to be reported or only one
    if [ "$1" = "all" ]; then
        HOSTS=()
        HOSTS+="$(patchman -lh | tail -n +3 | awk 'NR%16==1' | awk -F '[.:]' '{ print $1 }')"

        for HOST in $HOSTS; do
            report $HOST
        done
    else
        report $1
    fi
else
    echo "ERROR: Missing hostname."
fi
