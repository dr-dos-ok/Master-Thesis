#!/bin/bash

cd $PCODE
./train.py -l 1024,1024,1024,1024 -v 2 -grbme 225 -rbme 75 -prfreq 25 -ftfreq 25 -maxbatch 140  
