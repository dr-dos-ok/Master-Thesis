#!/bin/bash

cd $ZDISK/~ngal/MT/PythonCode
./train.py -l 2048,2048,2048,2048,2048 -v 2 -grbme 225 -rbme 75 -prfreq 25 -ftfreq 25 -maxbatch 140 -ftonly DBN_RBM_pr_225_ft_25.save 
