#!/bin/bash

cd ..
./manage.py graph_models -g -o patchman.png hosts operatingsystems packages arch repos domains reports
