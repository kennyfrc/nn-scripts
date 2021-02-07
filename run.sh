#!/bin/bash

DT=$(date '+%Y%m%d-%H%M%S');
LOG_FILE="train-$DT.log"

python3 selfplay.py --games 10000 --engine lc0 --file_type plain --mode random --book books/unbal4moves.bin --nodes 1 --min_ply 30 >> ${LOG_FILE};