#!/bin/bash

for layer in 2 3 4 5
  do
  for layer_sz in 512 1024 2048 
    do
    for bl in $(seq 1 $layer)
      do
      qsub -v blayer=$bl,lay=$layer,lay_sz=$layer_sz -l nodes=1,walltime=24:00:00 ./trainlinearsvmrl.sh
    done
  done
done
