#!/bin/bash

echo "[INFO] Setting \"Check DNS\" flag as True on all hosts"

for i in $(patchman -lh | tail -n +3 | awk -F ' : ' 'NR%16==1 { print $1 }' | sed -e "s/://g"); do 
	patchman -sdns -H $i; 
done

echo "[INFO] Processing Reverse DNS"
patchman -n
