#!/bin/bash

report() {
    # Verifica se existem updates disponíveis. Se não existir nenhum, não será preciso executar o resto do script
    UPDATES="$(patchman -lh -H $1 | tail -n +3 | head -n -1 | awk 'NR==10' | awk -F ' : ' '{ print $2 }')"

    if [ $UPDATES -gt 0 ]; then
        # Define o nome do ficheiro
	DIR="/usr/local/patchman/email/"
        FILE=$DIR$1_$(date +%Y%m%d)

        #´Obtém o domínio da máquina que está registado na DB do Patchman
        DOMAIN="$(patchman -lh -H $1 | tail -n +3 | head -n -1 | awk 'NR==3' | awk -F ' : ' '{ print $2 }')"

        # Define o recipient do e-mail dependendo do domínio
        case $DOMAIN in
            #unknown)
            #    RECIPIENT="ricardomiguel.jeronimo@altran.com"
            #    ;;
            *)
                RECIPIENT="ricardomiguel.jeronimo@altran.com"
                ;;
        esac

        # Cria o relatório
        echo "<html>" > $FILE
        echo "<style>" >> $FILE
        echo "body { font-family: \"Calibri\"  }" >> $FILE
        echo "#details table { border-collapse: collapse; width: 20em; }" >> $FILE
        echo "#updates table { border-collapse: collapse; width: 100%; }" >> $FILE
        echo "#details th, #details tr, #details td { text-align: left; }" >> $FILE
        echo "#updates th, #updates td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }" >> $FILE
        echo "</style>" >> $FILE

        echo "<body>" >> $FILE
        echo "<p>Existem atualizações diponíveis para a máquina <b>$1</b>:</p><br>" >> $FILE

        echo "<div id=\"details\"><table>" >> $FILE
        patchman -lh -H $1 | tail -n +3 | head -n -1 | awk 'NR!=2 && NR!=7 && NR!=9 && NR!=11 && NR!=13 && NR!=14' | awk -F ' : ' '{ print "<tr><th>"$1":</th><td>"$2"</td></tr>" }' >> $FILE
        echo "</table></div><br>" >> $FILE

        echo "<div id=\"updates\"><table>" >> $FILE
        patchman -u -H $1 | tail -n +3 | head -n -1 | awk 'BEGIN { print "<tr><th>Versão Atual</th><th>Nova Versão</th><th>Tipo</th></tr>" }
                                                                 { print "<tr><td>"$1"</td><td>"$3"</td><td>"$4"</td></tr>" }' >> $FILE
        echo "</table></div><br>" >> $FILE

        echo "<p>Por favor, entre em contacto com a equipa de SysUnix a fim de agendar as atualizações necessárias para o momento mais oportuno.</p>" >> $FILE

        echo "</body>" >> $FILE
        echo "</html>" >> $FILE

        # Envia o relatório por e-mail
        mail -aContent-Type:text/html -s "[$1] Relatório Semanal de Atualizações" $RECIPIENT < $FILE

	echo "[$1] INFO: Relatório enviado."
    else
        echo "[$1] INFO: Não existem updates disponíveis."
    fi
}

if [ "$1" != "" ]; then
    # Verifica se é para reportar todos ou apenas um host
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
    echo "ERRO: Hostname da máquina em falta."
fi
