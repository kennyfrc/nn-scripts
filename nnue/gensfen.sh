#!/bin/bash

NNUE=sf-trainer

options="uci
setoption name SkipLoadingEval value true
setoption name Hash value 1024
setoption name Threads value 4
isready
gensfen depth 8 loop 10000000 random_move_maxply 30 random_move_count 10 output_file_name gensfen_d8_10m.bin
quit
"

printf "$options" | $NNUE
