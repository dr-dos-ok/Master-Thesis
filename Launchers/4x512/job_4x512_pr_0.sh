#!/bin/bash

cd $ZDISK/~ngal/MT/PythonCode
./train.py -l 512,512,512,512 -v 2 -grbme 0 -rbme 0 -prfreq 25 -ftfreq 25 -maxbatch 140
